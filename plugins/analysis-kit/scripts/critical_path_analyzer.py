#!/usr/bin/env python3
"""Deterministic critical-path/timing aggregation for analysis-kit's
analyzing-session-operations skill.

Scope note: this script aggregates timestamped spans the calling skill has
already compiled from a session transcript or subagent-dispatch records --
it does not itself measure wall-clock time. A span missing `start` or `end`
contributes to `unknown_spans` only; it is never defaulted to zero duration
or silently dropped from the count, per AKR-NFR-004.

Input (--events <path>): a JSON array of span objects:
  {
    "session_id": "<groups spans that can be compared for overlap -- spans "
                  "from different session_ids are never merged or compared>",
    "label": "<what the span covers, e.g. a tool/skill/subagent name>",
    "start": "<ISO-8601>" | null,
    "end": "<ISO-8601>" | null
  }

Output, per session_id:
  - elapsed_seconds: latest known end minus earliest known start, or null
    if no span in this session has both a start and an end.
  - active_seconds: the union (not sum) of every known [start, end)
    interval's duration -- overlapping spans are counted once, not twice.
  - overlapping_seconds: total wall-clock time covered by 2+ concurrent
    known spans (a direct measure of realized parallelism).
  - waiting_seconds: elapsed_seconds minus active_seconds -- idle time
    within the session's own elapsed window; null whenever elapsed itself
    is null.
  - known_spans / unknown_spans: counts, not folded into any duration.
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


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Union of possibly-overlapping [start, end) intervals, sorted and merged."""
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda iv: iv[0])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _overlap_seconds(intervals: list[tuple[datetime, datetime]]) -> float:
    """Total time covered by 2+ concurrent intervals, via a sweep over start/end events."""
    if len(intervals) < 2:
        return 0.0
    events = []
    for start, end in intervals:
        events.append((start, 1))
        events.append((end, -1))
    events.sort(key=lambda e: (e[0], -e[1]))  # process starts before ends at the same instant

    overlap = 0.0
    active = 0
    prev_ts = None
    for ts, delta in events:
        if prev_ts is not None and active >= 2:
            overlap += (ts - prev_ts).total_seconds()
        active += delta
        prev_ts = ts
    return overlap


def analyze(spans: list[dict]) -> dict:
    # Keyed by str | None -- a span missing session_id groups under the None key rather
    # than being dropped or raising, though the calling skill's own input contract
    # documents session_id as required.
    by_session: dict[str | None, list[dict]] = defaultdict(list)
    for span in spans:
        by_session[span.get("session_id")].append(span)

    sessions: dict[str | None, dict] = {}
    for session_id, session_spans in by_session.items():
        known_intervals: list[tuple[datetime, datetime]] = []
        unknown_count = 0

        for span in session_spans:
            start = _parse_ts(span.get("start"))
            end = _parse_ts(span.get("end"))
            if start and end and end >= start:
                known_intervals.append((start, end))
            else:
                # A missing timestamp, or an end before its own start (clock skew, a
                # mispaired start/end field upstream) -- both are unknown, never fed
                # into the interval arithmetic where they'd silently produce a
                # negative elapsed/active duration.
                unknown_count += 1

        if known_intervals:
            earliest = min(iv[0] for iv in known_intervals)
            latest = max(iv[1] for iv in known_intervals)
            elapsed_seconds = (latest - earliest).total_seconds()
            merged = _merge_intervals(known_intervals)
            active_seconds = sum((end - start).total_seconds() for start, end in merged)
            overlapping_seconds = _overlap_seconds(known_intervals)
            waiting_seconds = elapsed_seconds - active_seconds
        else:
            elapsed_seconds = None
            active_seconds = None
            overlapping_seconds = 0.0
            waiting_seconds = None

        sessions[session_id] = {
            "elapsed_seconds": elapsed_seconds,
            "active_seconds": active_seconds,
            "overlapping_seconds": overlapping_seconds,
            "waiting_seconds": waiting_seconds,
            "known_spans": len(known_intervals),
            "unknown_spans": unknown_count,
        }

    return {"sessions": sessions}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events",
        required=True,
        help="Path to a JSON file: an array of {session_id, label, start, end} span objects",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit structured JSON (the only output mode)"
    )
    args = parser.parse_args()

    events_path = Path(args.events).resolve()
    try:
        with events_path.open(encoding="utf-8") as f:
            spans = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"Error: could not read {events_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(spans, list) or not all(isinstance(s, dict) for s in spans):
        print("Error: --events must be a JSON array of objects", file=sys.stderr)
        return 1

    result = analyze(spans)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
