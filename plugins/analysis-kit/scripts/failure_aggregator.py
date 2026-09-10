#!/usr/bin/env python3
"""Deterministic reliability/failure aggregation for analysis-kit's
analyzing-session-operations skill.

Scope note: this script aggregates events the calling skill has already
compiled from a session transcript (tool-use/tool-result inspection --
session_parser.py's own current output has no per-attempt success/failure
signal, so the calling skill builds this script's --events input directly
from transcript content). It never estimates a denominator or a
time-to-recovery it wasn't given timestamps to compute -- both come back
`null`/omitted rather than a guessed value, per AKR-NFR-004.

Input (--events <path>): a JSON array of event objects, one per attempt:
  {
    "subject": "<what was attempted, e.g. 'Bash(pytest)'>",
    "category": "tool" | "environment" | "flaky" | "nondeterministic"
               | "silent" | "fail-open" | "user-corrected" | null,
    "result": "success" | "failure",
    "timestamp": "<ISO-8601>" | null
  }
`category` is null only on a `success` result; a `failure` with `category`
null is counted as "uncategorized" -- disclosed as its own bucket, never
silently dropped or guessed into an existing category.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def aggregate(events: list[dict]) -> dict:
    attempts = len(events)
    failures = 0
    by_category: dict[str, int] = defaultdict(int)
    # Keyed by str | None -- an event missing subject groups under the None key rather
    # than being dropped or raising, though the calling skill's own input contract
    # documents subject as required.
    by_subject_failures: dict[str | None, list[dict]] = defaultdict(list)

    for event in events:
        result = event.get("result")
        if result != "failure":
            continue
        failures += 1
        category = event.get("category") or "uncategorized"
        by_category[category] += 1
        by_subject_failures[event.get("subject")].append(event)

    recoveries = 0
    recovery_details: list[dict] = []
    unresolved_failures: list[dict] = []
    repeated_failures: list[dict] = []

    # Track, per subject, the failures not yet matched to a later success --
    # FIFO: the oldest unresolved failure for a subject is the one the next
    # success for that subject is treated as recovering.
    pending_failures: dict[str | None, list[dict]] = defaultdict(list)
    for event in events:
        subject = event.get("subject")
        result = event.get("result")
        if result == "failure":
            pending_failures[subject].append(event)
        elif result == "success" and pending_failures.get(subject):
            failed_event = pending_failures[subject].pop(0)
            recoveries += 1
            failed_ts = _parse_ts(failed_event.get("timestamp"))
            recovered_ts = _parse_ts(event.get("timestamp"))
            # Only report a time-to-recovery when both timestamps exist AND the
            # recovery is actually after the failure -- input isn't guaranteed to
            # be strictly chronological (interleaved from multiple sources), so a
            # naive subtraction can otherwise silently yield a negative duration.
            time_to_recovery = (
                (recovered_ts - failed_ts).total_seconds()
                if failed_ts and recovered_ts and recovered_ts >= failed_ts
                else None
            )
            recovery_details.append(
                {
                    "subject": subject,
                    "category": failed_event.get("category") or "uncategorized",
                    "failed_at": failed_event.get("timestamp"),
                    "recovered_at": event.get("timestamp"),
                    "time_to_recovery_seconds": time_to_recovery,
                }
            )

    for subject, remaining in pending_failures.items():
        for failed_event in remaining:
            unresolved_failures.append(
                {"subject": subject, "category": failed_event.get("category") or "uncategorized"}
            )

    for subject, failure_list in by_subject_failures.items():
        if len(failure_list) > 1:
            repeated_failures.append({"subject": subject, "count": len(failure_list)})
    repeated_failures.sort(key=lambda item: item["subject"])

    return {
        "attempts": attempts,
        "failures": failures,
        "by_category": dict(by_category),
        "recoveries": recoveries,
        "recovery_details": recovery_details,
        "unresolved_failures": unresolved_failures,
        "repeated_failures": repeated_failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events",
        required=True,
        help="Path to a JSON file: an array of {subject, category, result, timestamp} objects",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON (default output is already JSON; this flag is accepted "
        "for CLI-shape consistency with critical_path_analyzer.py and has no additional effect)",
    )
    args = parser.parse_args()

    events_path = Path(args.events).resolve()
    try:
        with events_path.open(encoding="utf-8") as f:
            events = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"Error: could not read {events_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
        print("Error: --events must be a JSON array of objects", file=sys.stderr)
        return 1

    result = aggregate(events)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
