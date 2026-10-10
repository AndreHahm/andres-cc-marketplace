#!/usr/bin/env python3
"""Deterministic usage-data aggregation for analysis-kit skills.

Scope note: this script aggregates usage data the calling skill has
already observed and compiled -- it does not, and cannot, measure the
main conversation's own token/time usage directly, since no API exposes
that to a skill. Its realistic input is subagent-dispatch usage figures
(the tokens/duration_ms values that accompany a backgrounded Agent tool
result), compiled by the calling skill into the JSON list this script
reads. Treat any total this script reports as covering only what was
actually supplied, not the whole session.

Optional `level` field (added for analyzing-session-operations' Performance
& Cost section): one of "whole_session", "skill", "subagent", "tool". When
present, entries are additionally rolled up `by_level` so a report can state
which levels actually have data -- e.g. never present a subagent-only total
as if it were a whole-session total. Entries with no `level` are treated as
"subagent" for backward compatibility with this script's original callers,
matching its own pre-existing scope note above.
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

KNOWN_LEVELS = {"whole_session", "skill", "subagent", "tool"}


def _bad_number(value: object) -> bool:
    """True for a present, non-null value that is not a usable count.

    Booleans, text, negative numbers and nan/inf are all refused.
    """
    if value is None:
        return False
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return True
    return not math.isfinite(value) or value < 0


def validate_entries(entries: list[dict]) -> str | None:
    """Return a one-line description of the first malformed entry, or None when all are usable.

    Absent or null `tokens`/`duration_ms` still mean 0, and an unknown `level` still falls back
    to "subagent" in `aggregate`; only values that would crash or corrupt the totals are refused.
    """
    for index, entry in enumerate(entries):
        for field in ("tokens", "duration_ms"):
            if _bad_number(entry.get(field)):
                got = entry.get(field)
                return f"entry {index}: {field} must be a non-negative number, got {got!r}"
        label = entry.get("label")
        if label is not None and not isinstance(label, str):
            return f"entry {index}: label must be a string, got {label!r}"
    return None


def aggregate(entries: list[dict]) -> dict:
    total_tokens: int = 0
    total_duration_ms = 0
    by_label: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "duration_ms": 0, "count": 0})
    by_level: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "duration_ms": 0, "count": 0})

    for entry in entries:
        tokens = entry.get("tokens", 0) or 0
        duration_ms = entry.get("duration_ms", 0) or 0
        label = entry.get("label") or "unlabeled"
        level = entry.get("level") or "subagent"
        if not isinstance(level, str) or level not in KNOWN_LEVELS:
            level = "subagent"
        total_tokens += tokens
        total_duration_ms += duration_ms
        by_label[label]["tokens"] += tokens
        by_label[label]["duration_ms"] += duration_ms
        by_label[label]["count"] += 1
        by_level[level]["tokens"] += tokens
        by_level[level]["duration_ms"] += duration_ms
        by_level[level]["count"] += 1

    hotspots = sorted(by_label.items(), key=lambda kv: kv[1]["tokens"], reverse=True)
    levels_present = sorted(by_level.keys())
    levels_present_str = ", ".join(levels_present) if levels_present else "none"

    return {
        "entries_aggregated": len(entries),
        "total_tokens": total_tokens,
        "total_duration_ms": total_duration_ms,
        "by_label": dict(by_label),
        "by_level": dict(by_level),
        "levels_present": levels_present,
        "top_hotspots_by_tokens": [{"label": label, **stats} for label, stats in hotspots[:10]],
        "scope_note": (
            "Totals cover only entries supplied by the calling skill (typically subagent-dispatch "
            "usage figures) -- not whole-session usage, which no skill can measure directly. "
            f"Levels actually present in this run: {levels_present_str} "
            "-- never present a total from a narrower level (e.g. subagent) as if it covered a "
            "broader one (e.g. whole_session) that isn't in this list."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSON file: an array of {label, tokens, duration_ms} objects",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    try:
        with input_path.open(encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"Error: could not read {input_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        print("Error: --input must be a JSON array of objects", file=sys.stderr)
        return 1

    problem = validate_entries(entries)
    if problem is not None:
        print(f"Error: invalid input in {input_path}: {problem}", file=sys.stderr)
        return 1

    result = aggregate(entries)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
