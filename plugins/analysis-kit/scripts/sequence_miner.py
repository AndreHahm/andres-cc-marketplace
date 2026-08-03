#!/usr/bin/env python3
"""Deterministic repeated-subsequence detection for analysis-kit skills.

Takes a JSON array of normalized action tokens (strings) -- the calling
skill is responsible for producing this list by abstracting raw actions
into tokens first (e.g. "RUN_TEST(unit,state)"), since no raw session-log
source exists for this plugin to parse independently. This script only
does the counting: which subsequences of tokens repeat, and how often.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def find_repeated_subsequences(tokens: list[str], min_length: int, min_occurrences: int) -> list[dict]:
    max_length = min(len(tokens), 10)
    found = []
    for length in range(min_length, max_length + 1):
        counts = Counter(
            tuple(tokens[i:i + length])
            for i in range(len(tokens) - length + 1)
        )
        for sequence, count in counts.items():
            if count >= min_occurrences:
                found.append({"sequence": list(sequence), "length": length, "count": count})
    # Prefer longer, more-frequent sequences first.
    found.sort(key=lambda entry: (-entry["length"], -entry["count"]))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to a JSON file containing an array of string tokens")
    parser.add_argument("--min-length", type=int, default=2, help="Minimum subsequence length to report (default: 2)")
    parser.add_argument("--min-occurrences", type=int, default=2, help="Minimum repeat count to report (default: 2)")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    with input_path.open(encoding="utf-8") as f:
        tokens = json.load(f)

    if not isinstance(tokens, list) or not all(isinstance(t, str) for t in tokens):
        print("Error: --input must be a JSON array of strings", file=sys.stderr)
        return 1

    result = {
        "token_count": len(tokens),
        "repeated_subsequences": find_repeated_subsequences(tokens, args.min_length, args.min_occurrences),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
