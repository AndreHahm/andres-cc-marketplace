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

import yaml

BASELINE = "scripts/marketplace_ci/git_output_grants_baseline.json"

_COMPONENT_GLOBS = (
    "plugins/*/skills/*/SKILL.md",
    "plugins/*/commands/*.md",
    "plugins/*/agents/*.md",
)

# Every command below accepts `--output=<path>`, a write to any file (each wrote its file when run).
_SUBCOMMANDS = "diff|diff-tree|diff-index|diff-files|log|show|whatchanged"
# A git global option before the subcommand: `--no-pager`, `--git-dir=x`, or `-C`/`-c`/`--git-dir`
# followed by its value. A value never starts with `-`, so two adjacent options can only parse one
# way; with both readings possible the repeated group backtracks exponentially on a long run.
_GLOBAL_OPTION = (
    r"\s+(?:-C|-c|--git-dir|--work-tree|--namespace)\s+[^\s:*)-][^\s:*)]*"
    r"|\s+--?[\w-]+(?:=[^\s:*)]*)?"
)
# `git [global options]`, then either a wildcard right away (a blanket `git:*`, `git *` or
# `git -C:*`) or a subcommand, any literal arguments and a wildcard (`:*` or ` *`). The arguments
# may contain a `:` that does not start `:*`, but not `*` or `)`, so one match never spans two
# grants inside a single `Bash(...)`.
_WILDCARD_GRANT = re.compile(
    rf"(?<![\w-])git(?:{_GLOBAL_OPTION})*"
    rf"(?:\s+(?:{_SUBCOMMANDS})(?![\w-])(?P<args>(?:[^:*)\n]|:(?!\*))*?))?(?::\*|\s\*)"
)
# A glob with no separator after a subcommand or a prefix of one: `git diff*`, `git d*`. Not
# verified live that Claude Code matches this as a glob; flagged anyway, since a false positive only
# costs a baseline entry.
_GLOB_PREFIX = re.compile(rf"(?<![\w-])git(?:{_GLOBAL_OPTION})*\s+(?P<word>[\w-]+)\*")


@dataclass(frozen=True)
class GrantViolation:
    key: str
    reason: str


def _allowed_tools(source: str) -> list[str]:
    """The decoded `allowed-tools` entries of a frontmatter block, as the loader sees them.

    The value is decoded with a YAML parser, not matched as raw text: an escaped line break in a
    double-quoted scalar, for one, joins `Bash(git diff` and `:*)` into a single grant. Raises
    ValueError when the frontmatter is not valid YAML, so that case fails closed.
    """
    parts = source.split("\n---", 2)
    if not source.startswith("---") or len(parts) < 2:
        return []
    try:
        frontmatter = yaml.safe_load(parts[0][3:])
    except (yaml.YAMLError, RecursionError) as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(frontmatter, dict):
        return []
    value = frontmatter.get("allowed-tools")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _scan(repo: Path) -> tuple[set[str], set[str]]:
    """Return the wildcard grant keys and the paths whose frontmatter could not be parsed."""
    found: set[str] = set()
    unparsable: set[str] = set()
    for pattern in _COMPONENT_GLOBS:
        for path in sorted(repo.glob(pattern)):
            relative = path.relative_to(repo).as_posix()
            try:
                entries = _allowed_tools(path.read_text(encoding="utf-8"))
            except ValueError:
                unparsable.add(relative)
                continue
            for entry in entries:
                for match in _WILDCARD_GRANT.finditer(entry):
                    if "--" in (match["args"] or "").split():
                        continue  # what the wildcard adds comes after `--`: a pathspec
                    grant = match.group(0).replace("\\", "")
                    found.add(f"{relative}::{grant}")
                for match in _GLOB_PREFIX.finditer(entry):
                    if any(name.startswith(match["word"]) for name in _SUBCOMMANDS.split("|")):
                        found.add(f"{relative}::{match.group(0)}")
    return found, unparsable


def find_wildcard_git_grants(repo: Path) -> set[str]:
    """Return `<repo-relative path>::<grant>` for each wildcard git read grant in frontmatter."""
    return _scan(repo)[0]


def find_violations(repo: Path) -> list[GrantViolation]:
    baseline_path = repo / BASELINE
    baseline = (
        set(json.loads(baseline_path.read_text(encoding="utf-8")))
        if baseline_path.exists()
        else set()
    )
    found, unparsable = _scan(repo)
    violations = [
        GrantViolation(path, "frontmatter is not valid YAML, so its grants cannot be checked")
        for path in sorted(unparsable)
    ]
    violations += [
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
