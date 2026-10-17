"""Tests for scripts.marketplace_ci.git_output_grants -- the issue #588 check that no new
wildcard git grant that also permits `--output=<path>` (a write to any file) lands."""

import json
import time
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
        "allowed-tools: Bash(git:*)",
        "allowed-tools: Bash(git *)",
        "allowed-tools: Bash(git -C:*)",
        "allowed-tools: Bash(git --no-pager *)",
        "allowed-tools: Bash(git diff*)",
        "allowed-tools: Bash(git d*)",
        "allowed-tools: Bash(git diff --src-prefix='safe':*)",
        'allowed-tools: Bash(git log --format="%H":*)',
        "allowed-tools: Bash(git stash:*)",
        "allowed-tools: Bash(git rev-list:*)",
        "allowed-tools: Bash(git cherry-pick:*)",
        "allowed-tools: Bash(git revert:*)",
        "allowed-tools: Bash(git shortlog:*)",
        "allowed-tools: Bash(git log --author --:*)",
        "allowed-tools: Bash(git log --format=%(trailers):*)",
        "allowed-tools: Bash(git diff --stat*)",
        "allowed-tools: Bash(git log -1*)",
        "allowed-tools: Bash(g\\it diff:*)",
        "allowed-tools: Bash(g''it diff:*)",
        "allowed-tools: Bash(GIT diff:*)",
        "allowed-tools: Bash(/usr/bin/git diff:*)",
        "allowed-tools: Bash(git difftool:*)",
        "allowed-tools: Bash(git bisect:*)",
        "allowed-tools: Bash(git bisect view:*)",
        "allowed-tools: Bash(git bisect visualize *)",
        "allowed-tools: Bash(git bisect *)",
        "allowed-tools: Bash(git bisect vis*)",
        "allowed-tools: Bash(git -C /path/to/repo:*)",
        "allowed-tools: Bash(git -c core.pager=cat:*)",
        "allowed-tools: Bash(git --git-dir .git:*)",
        "allowed-tools: Bash(git --attr-source HEAD diff:*)",
        "allowed-tools: Bash(git diff --*)",
        "allowed-tools: Bash(git log --grep 'a -- b' *)",
        "allowed-tools: Bash(git log --grep a\\ --\\ b *)",
        "allowed-tools: Bash(git diff --output --:*)",
        "allowed-tools: Bash(git log --author git HEAD *)",
        "allowed-tools: Bash(git log --grep=')' :*)",
        "allowed-tools: Bash(git log --someflag -- :*)",
        "allowed-tools: Bash(echo %(x), Bash(git diff:*)",
        "allowed-tools: Bash(*/git diff:*)",
        "allowed-tools: Bash(/usr/*/git diff:*)",
        "allowed-tools: Bash(*git diff:*)",
        "allowed-tools: Bash(g* diff:*)",
        "allowed-tools: Bash(*/git:*)",
        "allowed-tools: Bash(g*:*)",
        "allowed-tools: Bash(git -c alias.zz=diff zz:*)",
        "allowed-tools: Bash(git -c alias.zz=log zz --oneline *)",
        "allowed-tools: Bash(git --config-env=alias.zz=VAR zz:*)",
        # a word git does not know may be an alias for diff (`git config alias.innocuous diff`)
        "allowed-tools: Bash(git innocuous:*)",
        "allowed-tools: Bash(git lg *)",
        "allowed-tools: Bash(git -C /repo co:*)",
        "allowed-tools: Bash(git difftoolx:*)",
        "allowed-tools: Bash(git innocu*)",
        "allowed-tools: Bash(git innocuous --stat *)",
    ],
)
def test_wildcard_grant_is_found(tmp_path: Path, tools: str) -> None:
    path = _skill(tmp_path, "s", tools)
    found = find_wildcard_git_grants(tmp_path)
    assert found and all(key.startswith(f"{path}::") for key in found)


@pytest.mark.parametrize(
    "tools",
    [
        "allowed-tools: Bash(git diff --cached), Read",
        "allowed-tools: Bash(git log -n 5 --oneline --:*)",
        "allowed-tools: Bash(git log -- docs/ci.md:*)",
        "allowed-tools: Bash(git log -- --output=/tmp:*)",
        "allowed-tools: Bash(git status:*) Bash(git switch:*)",
        "allowed-tools: Bash(git help:*) Bash(git config notes.:*)",
        "allowed-tools: Bash(git stat*)",
        "allowed-tools: Bash(git innocuous --oneline -- :*)",
        "allowed-tools: Bash(git bisect start:*) Bash(git bisect good:*) Bash(git bisect log:*)",
        "allowed-tools: Bash(git bisect reset:*) Bash(git bisect bad:*)",
        "allowed-tools: Bash(git log -1 -- :*)",
        "allowed-tools: Bash(ls *) Bash(cat *)",
        "allowed-tools: Bash(*/git status:*)",
        "allowed-tools: Bash(*/git-kit/scripts/x.sh:*)",
        "allowed-tools: Bash(git -c user.name=x status:*)",
        "allowed-tools: Bash(*)",
        "allowed-tools: Bash(git add diff.txt:*)",
        "allowed-tools: Bash(git -C /tmp status:*)",
        "allowed-tools: Bash(git diff-tree --no-commit-id --)",
        "allowed-tools: Bash(git status *) Bash(git commit -m *)",
        "allowed-tools: Bash(git add*)",
        "allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/git-stage-selected-files.sh:*)",
        "allowed-tools: Bash(digit *)",
        "allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x.py:*)",
        "allowed-tools: Bash(git diff:\\*)",
        "allowed-tools: Bash(git log --oneline -- docs:*)",
        "allowed-tools: Bash(git branch:*) Bash(git push origin:*)",
    ],
)
def test_scoped_grant_is_not_found(tmp_path: Path, tools: str) -> None:
    _skill(tmp_path, "s", tools)
    assert find_wildcard_git_grants(tmp_path) == set()


def test_grant_split_by_a_yaml_escaped_line_break_is_found(tmp_path: Path) -> None:
    # YAML joins `Bash(git diff` and `:*)` into one grant; the raw text has no `git diff:*`.
    path = _skill(tmp_path, "s", 'allowed-tools: ["Bash(git diff\\\n    :*)"]')
    assert find_wildcard_git_grants(tmp_path) == {f"{path}::git diff:*"}


def test_unparsable_frontmatter_fails_closed(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: [Bash(git diff:*)")
    violations = find_violations(tmp_path)
    assert [v.key for v in violations] == [path]
    assert "could not be read or parsed" in violations[0].reason


@pytest.mark.parametrize("option", ["-C", "--a", "-c", "--git-dir", "x"])
def test_long_run_of_global_options_is_not_slow(tmp_path: Path, option: str) -> None:
    # A backtracking pattern took 0.2 s at 28 `-C` tokens and 80 s at 28 `--a` tokens.
    _skill(tmp_path, "s", "allowed-tools: Bash(git " + f"{option} " * 300 + "status)")
    started = time.perf_counter()
    assert find_wildcard_git_grants(tmp_path) == set()
    assert time.perf_counter() - started < 2


def test_agent_tools_key_is_read(tmp_path: Path) -> None:
    path = tmp_path / "plugins" / "p" / "agents" / "a.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: a\ntools: Read, Bash(git diff:*)\n---\n", encoding="utf-8")
    assert find_wildcard_git_grants(tmp_path) == {"plugins/p/agents/a.md::git diff:*"}


def test_nested_command_directory_is_scanned(tmp_path: Path) -> None:
    path = tmp_path / "plugins" / "p" / "commands" / "group" / "c.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nallowed-tools: Bash(git log:*)\n---\n", encoding="utf-8")
    assert find_wildcard_git_grants(tmp_path) == {"plugins/p/commands/group/c.md::git log:*"}


def test_byte_order_mark_does_not_hide_the_frontmatter(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: Bash(git diff:*)")
    full = tmp_path / path
    full.write_bytes(b"\xef\xbb\xbf" + full.read_bytes())
    assert find_wildcard_git_grants(tmp_path) == {f"{path}::git diff:*"}


def test_symlinked_component_fails_closed(tmp_path: Path) -> None:
    path = _skill(tmp_path, "real", "allowed-tools: Read")
    link = tmp_path / "plugins" / "p" / "skills" / "linked" / "SKILL.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(tmp_path / path)
    assert [v.key for v in find_violations(tmp_path)] == ["plugins/p/skills/linked/SKILL.md"]


@pytest.mark.parametrize(
    "frontmatter",
    [
        "allowed-tools: Read\nallowed-tools: Bash(git diff:*)",
        "---x: 1\nallowed-tools: Bash(git diff:*)",
        "description: |\n  text\n  ---\nallowed-tools: Bash(git diff:*)",
    ],
)
def test_ambiguous_frontmatter_fails_closed(tmp_path: Path, frontmatter: str) -> None:
    path = _skill(tmp_path, "s", frontmatter)
    assert [v.key for v in find_violations(tmp_path)] == [path]


def test_unclosed_frontmatter_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "plugins" / "p" / "skills" / "s" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: s\nallowed-tools: Bash(git diff:*)\n", encoding="utf-8")
    assert [v.key for v in find_violations(tmp_path)] == ["plugins/p/skills/s/SKILL.md"]


def test_undecodable_component_fails_closed(tmp_path: Path) -> None:
    path = _skill(tmp_path, "s", "allowed-tools: Read")
    (tmp_path / path).write_bytes(b"---\nname: \xff\xfe\n---\n")
    assert [v.key for v in find_violations(tmp_path)] == [path]


@pytest.mark.parametrize("content", ["not json", '["a", ["b"]]', '{"a": 1}', '"text"'])
def test_malformed_baseline_is_a_violation_not_a_crash(tmp_path: Path, content: str) -> None:
    (tmp_path / BASELINE).parent.mkdir(parents=True)
    (tmp_path / BASELINE).write_text(content, encoding="utf-8")
    violations = find_violations(tmp_path)
    assert [v.key for v in violations] == [BASELINE]


def test_baseline_that_is_a_directory_is_a_violation_not_a_crash(tmp_path: Path) -> None:
    (tmp_path / BASELINE).mkdir(parents=True)
    assert [v.key for v in find_violations(tmp_path)] == [BASELINE]


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
