#!/usr/bin/env python3
"""Derive critical/standard/opportunistic re-check priority for entries in sources.json.

Blast radius is re-derived by grepping the repo tree for each source's `id` at
computation time rather than trusting the informational `cited_by` field, so a
stale hand-maintained count can't silently skew the result.

Usage:
    python compute_priority.py [path/to/sources.json]
"""
import json
import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return start.resolve()


class GrepUnavailableError(RuntimeError):
    """Raised when grep itself cannot be run -- distinct from "grep ran, found nothing"."""


def grep_blast_radius(repo_root: Path, source_id: str) -> int:
    # Exclude this skill's own directory (and its plugin mirror) -- sources.json
    # always contains the literal id string, and migration-notes.md/classification
    # docs may mention it too, which would otherwise put a floor of 1+ under every
    # source regardless of whether anything outside the registry actually cites it.
    own_dir_markers = ("upstream-sources-registry",)
    try:
        result = subprocess.run(
            ["grep", "-rlF", "--exclude-dir=.git", source_id, str(repo_root)],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError as e:
        raise GrepUnavailableError(f"grep is not available on this system: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise GrepUnavailableError(f"grep timed out scanning {repo_root}: {e}") from e

    # grep exit codes: 0 = matches found, 1 = no matches (expected, not an error),
    # 2+ = a real error (bad pattern, unreadable path, permission denied). Codes
    # 0/1 both fall through to counting stdout; only 2+ is a genuine failure that
    # must not be silently reported as blast_radius=0.
    if result.returncode not in (0, 1):
        raise GrepUnavailableError(
            f"grep exited {result.returncode} for id '{source_id}': {result.stderr.strip()}"
        )

    if not result.stdout:
        return 0
    hits = [
        line for line in result.stdout.splitlines()
        if line.strip() and not any(marker in line for marker in own_dir_markers)
    ]
    return len(hits)


def is_cited_by_required_rule(source: dict) -> bool:
    # A source's cited_by entries name rule IDs (e.g. "R5"); this script does not
    # itself know each rule's severity -- treat any non-empty cited_by on a
    # spec-tier source as REQUIRED-adjacent, since guide-tier/backed rules are
    # the ones typically marked SUGGESTED. This is a coarse heuristic, not a
    # substitute for reading plugin-rulebook's actual severity per rule.
    return bool(source.get("cited_by"))


def derive_priority(source: dict, blast_radius: int) -> str:
    authority = source.get("authority")
    volatility = source.get("volatility")

    if volatility == "frequent":
        return "critical"
    if authority == "spec" and is_cited_by_required_rule(source):
        return "critical"
    if authority == "guide" and volatility == "evolving":
        return "standard"
    if volatility == "stable" and blast_radius <= 1:
        return "opportunistic"
    if authority == "informal":
        return "opportunistic"
    return "standard"


def main() -> int:
    sources_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "assets" / "sources.json"
    if not sources_path.exists():
        print(f"sources.json not found at {sources_path}", file=sys.stderr)
        return 1

    try:
        with open(sources_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Malformed JSON in {sources_path} at line {e.lineno}, column {e.colno}: {e.msg}", file=sys.stderr)
        return 1

    repo_root = find_repo_root(sources_path.parent)

    exit_code = 0
    for source in data.get("sources", []):
        source_id = source.get("id")
        if not source_id:
            print(f"Skipping entry with no 'id' field: {source!r}", file=sys.stderr)
            exit_code = 1
            continue

        override = source.get("manual_rank_override")
        if override:
            priority = override
            reason = "manual_rank_override"
        else:
            try:
                blast_radius = grep_blast_radius(repo_root, source_id)
            except GrepUnavailableError as e:
                print(f"{source_id}: ERROR -- {e}", file=sys.stderr)
                exit_code = 1
                continue
            priority = derive_priority(source, blast_radius)
            reason = f"derived (blast_radius={blast_radius})"
        print(f"{source_id}: {priority}  [{reason}]")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
