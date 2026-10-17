"""Tests for scripts.marketplace_ci.git_output_grants -- the issue #588 check that no new
wildcard `git diff` / `git log` / `git show` grant (which also permits `--output=<path>`) lands."""

import json
from pathlib import Path

import pytest

from scripts.marketplace_ci.git_output_grants import (
    BASELINE,
    find_violations,
    find_wildcard_git_grants,
)


def _skill(repo: Path, name: str, frontmatter: str, body: str = "") -> str:
    path = repo / "plugins" / "p" / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return path.relative_to(repo).as_posix()


def _baseline(repo: Path, entries: list[str]) -> None:
    path = repo / BASELINE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries), encoding="utf-8")


@pytest.mark.parametrize(
    "tools",
    [
        "allowed-tools: Bash(git diff:*), Read",
        "allowed-tools: Read Bash(git diff *)",
        'allowed-tools: ["Bash(git show:*)"]',
        "allowed-tools:\n  - Bash(git log -1:*)",
        "allowed-tools: Bash(git log:* git show:* date:*)",
        "allowed-tools: Bash(git --no-pager diff:*)",
        "allowed-tools: Bash(git -C /tmp show:*)",
        "allowed-tools: Bash(git --git-dir=x -c core.pager=cat log:*)",
        "allowed-tools: Bash(git diff --src-prefix=a:b:*)",
        "allowed-tools: Bash(git diff-tree:*)",
        "allowed-tools: Bash(git diff-index:*)",
        "allowed-tools: Bash(git diff-files:*)",
        "allowed-tools: Bash(git whatchanged:*)",
    ],
)
def test_wildcard_grant_is_found(tmp_path: Path, tools: str) -> None:
    path = _skill(tmp_path, "s", tools)
    assert any(key.startswith(f"{path}::git ") for key in find_wildcard_git_grants(tmp_path))


@pytest.mark.parametrize(
    "tools",
    [
        "allowed-tools: Bash(git diff --cached), Read",
        "allowed-tools: Bash(git log -n 5 --oneline --:*)",
        "allowed-tools: Bash(git status:*) Bash(git difftool:*)",
        "allowed-tools: Bash(git add diff.txt:*)",
        "allowed-tools: Bash(git -C /tmp status:*)",
        "allowed-tools: Bash(git diff-tree --no-commit-id --)",
        "allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x.py:*)",
    ],
)
def test_scoped_grant_is_not_found(tmp_path: Path, tools: str) -> None:
    _skill(tmp_path, "s", tools)
    assert find_wildcard_git_grants(tmp_path) == set()


def test_log_grant_splits_into_one_entry_per_command(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: Bash(git log:* git show:* date:*)")
    assert find_wildcard_git_grants(tmp_path) == {f"{path}::git log:*", f"{path}::git show:*"}


def test_grant_quoted_in_the_body_is_ignored(tmp_path: Path) -> None:
    _skill(tmp_path, "s", "allowed-tools: Read", body="Never grant `Bash(git diff:*)`.\n")
    assert find_wildcard_git_grants(tmp_path) == set()


def test_new_grant_outside_the_baseline_fails(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: Bash(git diff:*)")
    _baseline(tmp_path, [])
    violations = find_violations(tmp_path)
    assert [v.key for v in violations] == [f"{path}::git diff:*"]
    assert "--output" in violations[0].reason


def test_baselined_grant_passes(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: Bash(git diff:*)")
    _baseline(tmp_path, [f"{path}::git diff:*"])
    assert find_violations(tmp_path) == []


def test_missing_baseline_file_means_no_known_grants(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: Bash(git diff:*)")
    assert [v.key for v in find_violations(tmp_path)] == [f"{path}::git diff:*"]
    assert find_violations(tmp_path / "empty") == []


def test_stale_baseline_entry_fails(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: Bash(git diff --cached)")
    _baseline(tmp_path, [f"{path}::git diff:*"])
    violations = find_violations(tmp_path)
    assert [v.key for v in violations] == [f"{path}::git diff:*"]
    assert "no longer present" in violations[0].reason


def test_this_repository_matches_its_baseline() -> None:
    assert find_violations(Path(__file__).resolve().parents[2]) == []
