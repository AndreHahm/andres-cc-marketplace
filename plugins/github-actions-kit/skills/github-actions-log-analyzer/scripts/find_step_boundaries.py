#!/usr/bin/env python3
"""Detect step/skill line-range boundaries in a GitHub Actions run log.

Ported from SKILL.md's own prose+grep instructions (Step 3) into a deterministic script,
matching the sibling skills' convention (github-actions-hardening-audit,
github-actions-conclusion-audit) of bundling structured parsing logic rather than
re-deriving it from ad hoc grep commands on every invocation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass

FLUE_START_RE = re.compile(r'\[flue\] skill\("([^"]+)"\): starting')
FLUE_END_RE = re.compile(r'\[flue\] skill\("([^"]+)"\): completed')
GROUP_START_RE = re.compile(r"##\[group\](.*)$")
GROUP_END_RE = re.compile(r"##\[endgroup\]")
GENERIC_START_RE = re.compile(r"(?<![A-Za-z0-9_])START(?![A-Za-z0-9_])", re.IGNORECASE)
GENERIC_END_RE = re.compile(r"(?<![A-Za-z0-9_])END(?![A-Za-z0-9_])", re.IGNORECASE)
RESULT_START_RE = re.compile(r"RESULT_START|extractResult")
RESULT_END_RE = re.compile(r"RESULT_END")


@dataclass
class Boundary:
    name: str
    start_line: int
    end_line: int
    source: str


def read_lines(path: str) -> list[str]:
    # Match `grep -a`'s behavior: treat binary/null-byte content as text rather than erroring.
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except FileNotFoundError:
        print(f"Error: log file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: could not read log file {path}: {e}", file=sys.stderr)
        sys.exit(1)


def find_flue_boundaries(lines: list[str]) -> list[Boundary]:
    """Stack-based pairing per skill name — a repeated `starting` for the same name before its
    `completed` (a retry, or two sequential same-named invocations) pushes a new open span rather
    than silently overwriting the earlier one, matching find_group_boundaries's nearest-unmatched-
    start-first pairing instead of dropping data on a same-name repeat."""
    boundaries: list[Boundary] = []
    open_starts: dict[str, list[int]] = {}
    for i, line in enumerate(lines, start=1):
        m = FLUE_START_RE.search(line)
        if m:
            open_starts.setdefault(m.group(1), []).append(i)
            continue
        m = FLUE_END_RE.search(line)
        if m:
            name = m.group(1)
            stack = open_starts.get(name)
            if stack:
                start = stack.pop()
                boundaries.append(Boundary(name=name, start_line=start, end_line=i, source="flue"))
    return boundaries


def find_group_boundaries(lines: list[str]) -> list[Boundary]:
    boundaries: list[Boundary] = []
    stack: list[tuple[str, int]] = []
    for i, line in enumerate(lines, start=1):
        m = GROUP_START_RE.search(line)
        if m:
            stack.append((m.group(1).strip() or f"group@{i}", i))
            continue
        if GROUP_END_RE.search(line) and stack:
            name, start = stack.pop()
            boundaries.append(Boundary(name=name, start_line=start, end_line=i, source="group"))
    return boundaries


def find_generic_boundaries(lines: list[str]) -> list[Boundary]:
    """Stack-based pairing of standalone START/END delimiters, nearest-unmatched-START first.

    Excludes RESULT_START/RESULT_END lines — those are result markers (tracked separately by
    find_result_markers), not step boundaries, and would otherwise double-count the same span.
    """
    boundaries: list[Boundary] = []
    stack: list[int] = []
    for i, line in enumerate(lines, start=1):
        if RESULT_START_RE.search(line) or RESULT_END_RE.search(line):
            continue
        if GENERIC_START_RE.search(line):
            stack.append(i)
        if GENERIC_END_RE.search(line) and stack:
            start = stack.pop()
            boundaries.append(
                Boundary(name=f"custom@{start}", start_line=start, end_line=i, source="custom")
            )
    return boundaries


def find_result_markers(lines: list[str]) -> list[dict]:
    markers = []
    open_start = None
    for i, line in enumerate(lines, start=1):
        if RESULT_START_RE.search(line):
            open_start = i
            continue
        if RESULT_END_RE.search(line) and open_start is not None:
            markers.append({"start_line": open_start, "end_line": i})
            open_start = None
    return markers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path", help="Path to a GitHub Actions run log file")
    args = parser.parse_args()

    lines = read_lines(args.log_path)

    steps = (
        find_flue_boundaries(lines) + find_group_boundaries(lines) + find_generic_boundaries(lines)
    )
    steps.sort(key=lambda b: b.start_line)

    result = {
        "steps": [asdict(b) for b in steps],
        "result_markers": find_result_markers(lines),
        "total_lines": len(lines),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
