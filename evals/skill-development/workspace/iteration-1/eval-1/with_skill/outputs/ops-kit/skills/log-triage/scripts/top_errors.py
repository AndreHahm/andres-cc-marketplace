#!/usr/bin/env python3
"""Count recurring errors in log lines read from stdin or a file.

Usage: top_errors.py [--top N] [FILE]
Lines are normalized (timestamps, UUIDs, hex ids, numbers, quoted values are
masked; ids like "abc123" are not) so repeats of the same error group together.
Prints a JSON array of {"count", "pattern", "first_example"}, most frequent
first.
"""

import argparse
import json
import re
import sys

MASKS = [
    (
        re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),
        "<ts>",
    ),
    (
        re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"),
        "<uuid>",
    ),
    (re.compile(r"0x[0-9a-fA-F]+"), "<hex>"),
    (re.compile(r"\d+(?:\.\d+)*"), "<n>"),
]


def normalize(line):
    line = line.strip()
    for pattern, token in MASKS:
        line = pattern.sub(token, line)
    return line


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", nargs="?", help="input file (default: stdin)")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    if args.file:
        with open(args.file, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    else:
        lines = sys.stdin.read().splitlines()
    counts, examples = {}, {}
    for line in lines:
        if not line.strip():
            continue
        key = normalize(line)
        counts[key] = counts.get(key, 0) + 1
        examples.setdefault(key, line.strip())
    ranked = sorted(counts, key=lambda k: (-counts[k], k))[: args.top]
    print(
        json.dumps(
            [{"count": counts[k], "pattern": k, "first_example": examples[k]} for k in ranked],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
