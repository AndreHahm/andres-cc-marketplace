#!/usr/bin/env python3
"""Deterministic filesystem inventory for analysis-kit skills.

Scans a project for artifacts that are discoverable from disk alone: rules
(.claude/rules/*.md), output artifacts (.claude/output/**), and local
planning documents (.draft/*.local.md, if the project uses that convention).

This script cannot and does not attempt to discover which skills,
sub-agents, commands, or workflow-skills were invoked during a session --
that evidence only exists in conversation context, not on disk.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _iso(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entries_for_glob(root: Path, pattern: str, category: str, verbose: bool) -> list[dict]:
    matches = sorted(root.glob(pattern))
    if verbose:
        print(f"  {pattern} -> {len(matches)} match(es)", file=sys.stderr)
    entries = []
    for path in matches:
        try:
            if not path.is_file():
                continue
            entries.append({
                "category": category,
                "name": path.name,
                "path": path.relative_to(root).as_posix(),
                "mtime": _iso(path.stat().st_mtime),
            })
        except OSError as exc:
            if verbose:
                print(f"  skipped {path} ({exc})", file=sys.stderr)
            continue
    return entries


def build_inventory(project_root: Path, verbose: bool = False) -> list[dict]:
    inventory: list[dict] = []

    if verbose:
        print("Scanning .claude/rules/*.md", file=sys.stderr)
    inventory += _entries_for_glob(project_root, ".claude/rules/*.md", "rule", verbose)

    if verbose:
        print("Scanning .claude/output/**/*", file=sys.stderr)
    inventory += _entries_for_glob(project_root, ".claude/output/**/*", "output_artifact", verbose)

    draft_dir = project_root / ".draft"
    if draft_dir.is_dir():
        if verbose:
            print("Scanning .draft/*.local.md", file=sys.stderr)
        inventory += _entries_for_glob(project_root, ".draft/*.local.md", "planning_document", verbose)
    elif verbose:
        print("Skipping .draft/*.local.md (.draft/ does not exist in this project)", file=sys.stderr)

    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Project root to scan (default: current directory)")
    parser.add_argument("--verbose", action="store_true", help="Print each glob pattern tried and its match count to stderr")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    inventory = build_inventory(project_root, verbose=args.verbose)
    json.dump(inventory, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
