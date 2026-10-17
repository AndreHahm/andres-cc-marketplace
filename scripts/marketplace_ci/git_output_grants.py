"""Read-only checker for wildcard `git diff` / `git log` / `git show` tool grants (issue #588).

A prefix grant such as `Bash(git diff:*)` also permits `git diff --output=<path>`, which writes
the diff to any file the user can write. The same holds for `diff-tree`, `diff-index`, `diff-files`
and `whatchanged`, and for a grant with git global options (`git --no-pager diff:*`). A component
whose `allowed-tools` carries one therefore holds a file-write grant it never declared. This check
lists every such grant in a plugin component's frontmatter and fails on any that is not in the
checked-in baseline, so no new one lands; each component scoped to an exact command or a pinned
script is removed from the baseline, and a baseline entry whose grant is gone fails too, so the
list cannot go stale.

Arguments after a literal `--` are pathspecs, so `Bash(git log -n 5 --oneline --:*)` is not
flagged. Only frontmatter is read: a grant quoted in a skill's prose is not a grant.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

BASELINE = "scripts/marketplace_ci/git_output_grants_baseline.json"

_COMPONENT_GLOBS = (
    "plugins/*/skills/*/SKILL.md",
    "plugins/*/commands/*.md",
    "plugins/*/agents/*.md",
)

# Every command below accepts `--output=<path>`, a write to any file (each wrote its file when run).
_SUBCOMMANDS = "diff|diff-tree|diff-index|diff-files|log|show|whatchanged"
# A git global option before the subcommand: `--no-pager`, `--git-dir=x`, or `-C`/`-c`/`--git-dir`
# followed by its value.
_GLOBAL_OPTION = (
    r"\s+(?:-C|-c|--git-dir|--work-tree|--namespace)\s+[^\s:*)\"']+"
    r"|\s+--?[\w-]+(?:=[^\s:*)\"']*)?"
)
# `git [global options] <subcommand>`, any literal arguments, then a wildcard (`:*` or ` *`). The
# arguments may contain a `:` that does not start `:*`, but not `*` or `)`, so one match never
# spans two grants inside a single `Bash(...)`.
_WILDCARD_GRANT = re.compile(
    rf"git(?:{_GLOBAL_OPTION})*\s+(?:{_SUBCOMMANDS})(?![\w-])"
    r"(?P<args>(?:[^:*)\n\"']|:(?!\*))*?)(?::\*|\s\*)"
)


@dataclass(frozen=True)
class GrantViolation:
    key: str
    reason: str


def _allowed_tools_text(source: str) -> str:
    """Return the raw text of the frontmatter `allowed-tools` key, including continuation lines."""
    parts = source.split("\n---", 2)
    if not source.startswith("---") or len(parts) < 2:
        return ""
    lines = parts[0].splitlines()
    collected: list[str] = []
    inside = False
    for line in lines:
        if re.match(r"allowed-tools\s*:", line):
            inside = True
            collected.append(line)
        elif inside and (line.startswith((" ", "\t", "-")) or not line.strip()):
            collected.append(line)
        elif inside:
            break
    return "\n".join(collected)


def find_wildcard_git_grants(repo: Path) -> set[str]:
    """Return `<repo-relative path>::<grant>` for each wildcard git read grant in frontmatter."""
    found: set[str] = set()
    for pattern in _COMPONENT_GLOBS:
        for path in sorted(repo.glob(pattern)):
            text = _allowed_tools_text(path.read_text(encoding="utf-8"))
            for match in _WILDCARD_GRANT.finditer(text):
                if match["args"].rstrip().endswith("--"):
                    continue
                grant = match.group(0).replace("\\", "")
                found.add(f"{path.relative_to(repo).as_posix()}::{grant}")
    return found


def find_violations(repo: Path) -> list[GrantViolation]:
    baseline_path = repo / BASELINE
    baseline = (
        set(json.loads(baseline_path.read_text(encoding="utf-8")))
        if baseline_path.exists()
        else set()
    )
    found = find_wildcard_git_grants(repo)
    violations = [
        GrantViolation(
            key,
            "wildcard git diff/log/show grant allows --output; "
            "scope it to an exact command or a pinned script",
        )
        for key in sorted(found - baseline)
    ]
    violations += [
        GrantViolation(key, f"baseline entry no longer present; remove it from {BASELINE}")
        for key in sorted(baseline - found)
    ]
    return violations
