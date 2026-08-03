#!/usr/bin/env python3
"""Deterministic structural comparison for analysis-kit skills.

Provides two comparison modes, both purely structural -- neither makes any
semantic judgment about whether a difference is good, bad, or expected.
Semantic interpretation of the diff output is the calling skill's job.

Modes:
  keys     -- diff two JSON files by top-level key (or, with --path, by the
              keys of a nested object reached via dotted path). Reports keys
              only in A, only in B, and keys in both.
  sections -- diff two markdown files by "## "-level heading text. Reports
              headings only in A, only in B, and headings in both.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def diff_keys(a_path: Path, b_path: Path, dotted_path: str | None) -> dict:
    a = _load_json(a_path)
    b = _load_json(b_path)
    if dotted_path:
        for part in dotted_path.split("."):
            a = a.get(part, {}) if isinstance(a, dict) else {}
            b = b.get(part, {}) if isinstance(b, dict) else {}
    a_keys = set(a.keys()) if isinstance(a, dict) else set()
    b_keys = set(b.keys()) if isinstance(b, dict) else set()
    return {
        "mode": "keys",
        "only_in_a": sorted(a_keys - b_keys),
        "only_in_b": sorted(b_keys - a_keys),
        "shared": sorted(a_keys & b_keys),
    }


_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _headings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [m.strip() for m in _HEADING_RE.findall(text)]


def diff_sections(a_path: Path, b_path: Path) -> dict:
    a_headings = set(_headings(a_path))
    b_headings = set(_headings(b_path))
    return {
        "mode": "sections",
        "only_in_a": sorted(a_headings - b_headings),
        "only_in_b": sorted(b_headings - a_headings),
        "shared": sorted(a_headings & b_headings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=["keys", "sections"])
    parser.add_argument("--a", required=True, help="Path to the first file")
    parser.add_argument("--b", required=True, help="Path to the second file")
    parser.add_argument("--path", default=None, help="Dotted key path into both JSON files, keys mode only")
    args = parser.parse_args()

    a_path = Path(args.a).resolve()
    b_path = Path(args.b).resolve()

    if args.mode == "keys":
        result = diff_keys(a_path, b_path, args.path)
    else:
        result = diff_sections(a_path, b_path)

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
