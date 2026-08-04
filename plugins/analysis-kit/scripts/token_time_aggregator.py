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
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def aggregate(entries: list[dict]) -> dict:
    total_tokens = 0
    total_duration_ms = 0
    by_label: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "duration_ms": 0, "count": 0})

    for entry in entries:
        tokens = entry.get("tokens", 0) or 0
        duration_ms = entry.get("duration_ms", 0) or 0
        label = entry.get("label", "unlabeled")
        total_tokens += tokens
        total_duration_ms += duration_ms
        by_label[label]["tokens"] += tokens
        by_label[label]["duration_ms"] += duration_ms
        by_label[label]["count"] += 1

    hotspots = sorted(by_label.items(), key=lambda kv: kv[1]["tokens"], reverse=True)

    return {
        "entries_aggregated": len(entries),
        "total_tokens": total_tokens,
        "total_duration_ms": total_duration_ms,
        "by_label": dict(by_label),
        "top_hotspots_by_tokens": [{"label": label, **stats} for label, stats in hotspots[:5]],
        "scope_note": (
            "Totals cover only entries supplied by the calling skill (typically subagent-dispatch "
            "usage figures) -- not whole-session usage, which no skill can measure directly."
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

    result = aggregate(entries)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
