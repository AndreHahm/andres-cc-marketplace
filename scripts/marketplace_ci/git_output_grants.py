"""Read-only checker for tool grants that let a git command write any file (issue #588).

A prefix grant such as `Bash(git diff:*)` also permits `git diff --output=<path>`, which writes
the diff to any file the user can write; a blanket `Bash(git:*)` permits that and every other
subcommand. This check lists every such grant in a plugin component's frontmatter and fails on any
that is not in the checked-in baseline, so no new one lands; each component scoped to an exact
command or a pinned script is removed from the baseline, and a baseline entry whose grant is gone
fails too, so the list cannot go stale.

The frontmatter is decoded as YAML and each `Bash(...)` rule is read token by token, so no pattern
can backtrack on a long crafted rule. Arguments after a literal `--` are pathspecs, so
`Bash(git log -n 5 --oneline --:*)` is not flagged. Only frontmatter is read: a grant quoted in a
skill's prose is not a grant.
"""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path

import yaml

BASELINE = "scripts/marketplace_ci/git_output_grants_baseline.json"

_COMPONENT_GLOBS = (
    "plugins/*/skills/*/SKILL.md",
    "plugins/*/commands/**/*.md",
    "plugins/*/agents/**/*.md",
)
_GRANT_KEYS = ("allowed-tools", "tools")  # skills and commands use the first, agents the second

# Each of these created the file named by `--output=<path>` when run on git 2.43.0 in a scratch
# repository (119 commands tried, then `difftool` and `bisect` by hand; other interactive and
# network commands were skipped), a write or a truncate of any path. Sweep again when git changes.
_OUTPUT_COMMANDS = frozenset(
    {
        "annotate",
        "archive",
        "blame",
        "cherry-pick",
        "diff",
        "difftool",
        "diff-files",
        "diff-index",
        "diff-tree",
        "fast-export",
        "format-patch",
        "log",
        "pickaxe",
        "range-diff",
        "reflog",
        "rev-list",
        "revert",
        "shortlog",
        "show",
        "stash",
        "whatchanged",
    }
)
# `git bisect` writes the file only through these subcommands; its others (start, good, bad, log,
# reset) are not flagged.
_BISECT_OUTPUT = frozenset({"view", "visualize"})
# Where a wildcard right after the subcommand word is flagged: a prefix of one of these.
_PREFIX_COMMANDS = _OUTPUT_COMMANDS | {"bisect"}
# Git global options that take the next word as their value.
_VALUE_GLOBAL_OPTIONS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--attr-source", "--super-prefix"}
    | {"--config-env"}
)
# Options that take the next word as their value, so a `--` right after one is its value and not a
# pathspec separator.
_VALUE_OPTIONS = frozenset(
    {"-S", "-G", "-O", "-L", "-n", "--author", "--committer", "--grep", "--since", "--until"}
    | {"--max-count", "--skip"}
)
# Options known to take no value. A `--` counts as a pathspec separator only when every option
# before it is one of these, takes its value after `=`, or is in `_VALUE_OPTIONS`; an option this
# list does not know could take the `--` as its value, so such a grant stays flagged.
_FLAGS_WITHOUT_VALUE = frozenset(
    {"--oneline", "--stat", "--name-only", "--name-status", "--cached", "--staged", "-z", "-p"}
    | {"--numstat", "--shortstat", "--summary", "--patch", "--graph", "--all", "--no-merges"}
    | {"--merges", "--first-parent", "--follow", "--decorate", "--abbrev-commit", "--text"}
    | {"--no-color", "--no-ext-diff", "-q", "--quiet", "--no-patch", "-s", "--raw", "--reverse"}
    | {"--topo-order", "--date-order"}
)
_ESCAPED_STAR = "\0"  # stands for a literal `\*` while the rule is read


@dataclass(frozen=True)
class GrantViolation:
    key: str
    reason: str


def _grant_entries(source: str) -> list[str]:
    """The decoded grant entries of a frontmatter block, as the loader sees them.

    Raises ValueError (or a YAMLError) when the frontmatter cannot be read exactly, so that case
    fails closed.
    """
    lines = source.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return []
    end = 0
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            end = index
            break
        if line.strip() == "---" or line.startswith("---"):  # an indented fence, or ---x
            raise ValueError("a line inside the frontmatter looks like a fence")
    if not end:
        raise ValueError("the frontmatter is not closed")
    text = "\n".join(lines[1:end])
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    if isinstance(root, yaml.MappingNode):  # loaders resolve a repeated key differently
        keys = [key.value for key, _ in root.value if isinstance(key, yaml.ScalarNode)]
        if len(keys) != len(set(keys)):
            raise ValueError("the frontmatter repeats a key")
    frontmatter = yaml.safe_load(text)
    if not isinstance(frontmatter, dict):
        return []
    entries: list[str] = []
    for key in _GRANT_KEYS:
        value = frontmatter.get(key)
        if isinstance(value, str):
            entries.append(value)
        elif isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, str))
    return entries


def _bash_rules(entry: str) -> list[str]:
    """The text inside each `Bash(...)`.

    Parentheses are balanced and a quoted one is skipped, so `%(trailers)` and `--grep=')'` stay
    inside. The search resumes just after each `Bash(`, so a rule nested in, or swallowed by, an
    unbalanced one is read too.
    """
    rules: list[str] = []
    search = 0
    while (start := entry.find("Bash(", search)) != -1:
        body = start + len("Bash(")
        depth, quote, index = 1, "", body
        while index < len(entry) and depth:
            char = entry[index]
            if quote:
                if char == quote:
                    quote = ""
                elif char == "\\" and quote == '"':
                    index += 1
            elif char in "'\"":
                quote = char
            elif char == "\\":
                index += 1
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        rules.append(entry[body : index - (1 if depth == 0 else 0)])
        search = body
    return rules


def _tokens(rule: str) -> list[str]:
    """The words of a rule as a shell would split them: quotes and backslashes are resolved
    (`g\\it`, `g''it`), and a quoted ` -- ` stays inside its word. An escaped `\\*` stays a
    literal."""
    rule = rule.replace("\\*", _ESCAPED_STAR)
    try:
        return shlex.split(rule)
    except ValueError:  # an unbalanced quote: keep every word rather than drop the rule
        return rule.replace("\\", "").replace('"', "").replace("'", "").split()


def _is_git(token: str) -> bool:
    return os.path.basename(token.partition("*")[0].rstrip(":")).lower() in {"git", "git.exe"}


def _after_pathspec_separator(args: list[str], wildcard: str) -> bool:
    """Whether the wildcard follows a real `--`, so what it adds is a pathspec and not an option.

    Fails closed: every option before the `--` must be one this module knows takes no value, takes
    its value after `=` or as the next word; any other could take the `--` as its own value.
    """
    words = list(args)
    head = wildcard.partition("*")[0]
    if head == "--:":  # `--:*`: the prefix ends with the separator; a glued `--*` is a glob
        words.append("--")
    index = 0
    while index < len(words):
        word = words[index]
        if word == "--":
            return True
        if word in _VALUE_OPTIONS:
            index += 2  # the next word is its value, even when that word is `--`
        elif (
            word.startswith("-")
            and "=" not in word
            and word not in _FLAGS_WITHOUT_VALUE
            and not word.lstrip("-").isdigit()
        ):
            return False
        else:
            index += 1
    return False


def _read_grant(tokens: list[str], start: int) -> tuple[str | None, int]:
    """Read the git grant at `tokens[start]`: the grant text if it is a flagged wildcard, and
    the index to resume at."""
    if "*" in tokens[start]:  # `git:*`, `git*`
        return tokens[start], start + 1
    index = start + 1
    while index < len(tokens) and tokens[index].startswith("-"):  # global options
        if "*" in tokens[index]:  # `git -C:*`
            return " ".join(tokens[start : index + 1]), index + 1
        if tokens[index] in _VALUE_GLOBAL_OPTIONS and index + 1 < len(tokens):
            if "*" in tokens[index + 1]:  # `git -C /repo:*`
                return " ".join(tokens[start : index + 2]), index + 2
            index += 2
        else:
            index += 1
    if index >= len(tokens):
        return None, len(tokens)
    subcommand, star, _ = tokens[index].partition("*")
    subcommand = subcommand.rstrip(":")
    if star:  # `git *`, `git diff:*`, `git diff*`, `git d*`, `git bisect:*`
        flagged = not subcommand or any(c.startswith(subcommand) for c in _PREFIX_COMMANDS)
        return (" ".join(tokens[start : index + 1]) if flagged else None), index + 1
    scan_from = index + 1
    if subcommand == "bisect":  # only its view and visualize subcommands write the file
        if scan_from >= len(tokens):
            return None, len(tokens)
        word, star, _ = tokens[scan_from].partition("*")
        word = word.rstrip(":")
        if star:  # `git bisect *`, `git bisect view:*`, `git bisect vis*`
            flagged = not word or any(name.startswith(word) for name in _BISECT_OUTPUT)
            return (" ".join(tokens[start : scan_from + 1]) if flagged else None), scan_from + 1
        if word not in _BISECT_OUTPUT:
            return None, scan_from + 1
        scan_from += 1
    elif subcommand not in _OUTPUT_COMMANDS:
        return None, index + 1
    end = scan_from
    while end < len(tokens) and "*" not in tokens[end]:
        end += 1
    if end >= len(tokens):  # an exact grant
        return None, len(tokens)
    if _after_pathspec_separator(tokens[scan_from:end], tokens[end]):
        return None, end + 1
    return " ".join(tokens[start : end + 1]), end + 1


def _wildcard_grants(rule: str) -> list[str]:
    """The flagged git grants in one `Bash(...)` rule; the legacy form lists several in one."""
    tokens = _tokens(rule)
    grants: list[str] = []
    index = 0
    while index < len(tokens):
        if not _is_git(tokens[index]):
            index += 1
            continue
        grant, index = _read_grant(tokens, index)
        if grant is not None:
            grants.append(grant.replace(_ESCAPED_STAR, "\\*"))
    return grants


def _scan(repo: Path) -> tuple[set[str], set[str]]:
    """Return the wildcard grant keys and the paths whose frontmatter could not be read."""
    found: set[str] = set()
    unreadable: set[str] = set()
    for pattern in _COMPONENT_GLOBS:
        for path in sorted(repo.glob(pattern)):
            relative = path.relative_to(repo).as_posix()
            if path.is_symlink():  # a link could point at an endless file or outside the repository
                unreadable.add(relative)
                continue
            try:
                entries = _grant_entries(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError, yaml.YAMLError, RecursionError):
                unreadable.add(relative)  # UnicodeDecodeError is a ValueError
                continue
            for entry in entries:
                for rule in _bash_rules(entry):
                    found.update(f"{relative}::{grant}" for grant in _wildcard_grants(rule))
    return found, unreadable


def find_wildcard_git_grants(repo: Path) -> set[str]:
    """Return `<repo-relative path>::<grant>` for each wildcard git grant in frontmatter."""
    return _scan(repo)[0]


def _load_baseline(repo: Path) -> tuple[set[str], list[GrantViolation]]:
    path = repo / BASELINE
    if not path.exists():
        return set(), []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return set(), [GrantViolation(BASELINE, f"baseline cannot be read: {type(exc).__name__}")]
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        return set(), [GrantViolation(BASELINE, "baseline is not a JSON list of strings")]
    return set(data), []


def find_violations(repo: Path) -> list[GrantViolation]:
    baseline, violations = _load_baseline(repo)
    found, unreadable = _scan(repo)
    violations += [
        GrantViolation(
            path, "frontmatter could not be read or parsed, so its grants cannot be checked"
        )
        for path in sorted(unreadable)
    ]
    violations += [
        GrantViolation(
            key,
            "wildcard git grant allows --output (a write to any file); "
            "scope it to an exact command or a pinned script",
        )
        for key in sorted(found - baseline)
    ]
    violations += [
        GrantViolation(key, f"baseline entry no longer present; remove it from {BASELINE}")
        for key in sorted(baseline - found)
    ]
    return violations
