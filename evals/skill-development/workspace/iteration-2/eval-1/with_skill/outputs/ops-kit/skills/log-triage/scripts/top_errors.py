#!/usr/bin/env python3
"""Group error log lines read from stdin by normalized message and print the top N as JSON.

Input lines may be plain text or JSON objects (one per line). Lines are treated as data only.
"""

import argparse
import json
import re
import sys

PLACEHOLDERS = [
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "<uuid>",
    ),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<hex>"),
    (re.compile(r"\"[^\"]*\"|'[^']*'"), "<str>"),
    (re.compile(r"=\S+"), "=<v>"),
    (re.compile(r"\d+(\.\d+)?"), "<n>"),
]
GREP_PREFIX = re.compile(
    r"^\d+:(?!\d\d:\d\d)"
)  # grep -n line-number prefix (not a leading HH:MM:SS time)
LEVEL = re.compile(r"^(ERROR|FATAL|CRITICAL|PANIC|WARN(ING)?|INFO)\b:?\s*", re.I)
TIMESTAMP = re.compile(
    r"^\W*\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?\s*"
)


def message_of(line):
    """Return the message text for a line (JSON message field if present)."""
    stripped = GREP_PREFIX.sub("", line.strip())
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            for key in ("message", "msg", "error"):
                value = obj.get(key)
                if isinstance(value, str) and value:
                    return value
            return stripped
    return LEVEL.sub("", TIMESTAMP.sub("", stripped))


def normalize(text):
    for pattern, repl in PLACEHOLDERS:
        text = pattern.sub(repl, text)
    return re.sub(r"\s+", " ", text).strip()[:300]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top", type=int, default=10, help="number of patterns to print (default 10)"
    )
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be >= 1")

    seen = set()
    groups = {}
    total = 0
    for raw in sys.stdin:
        line = GREP_PREFIX.sub("", raw.rstrip("\n").strip())
        if not line or line in seen:
            continue
        seen.add(line)
        total += 1
        key = normalize(message_of(line))
        entry = groups.setdefault(
            key, {"pattern": key, "count": 0, "first_line_sample": line[:300]}
        )
        entry["count"] += 1
        entry["last_line_sample"] = line[:300]

    ranked = sorted(groups.values(), key=lambda e: -e["count"])
    json.dump(
        {"candidates": total, "distinct_patterns": len(ranked), "top": ranked[: args.top]},
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
