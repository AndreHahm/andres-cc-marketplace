"""Fixture tests for session-handoff template v2: frontmatter, Resume Card, and the fallback for
older handoffs. Covers create_handoff.py, validate_handoff.py, check_staleness.py and
list_handoffs.py.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

HANDOFF_SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "session-handoff" / "scripts"
if str(HANDOFF_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(HANDOFF_SCRIPTS))

import check_staleness  # noqa: E402
import create_handoff  # noqa: E402
import list_handoffs  # noqa: E402
import validate_handoff  # noqa: E402

V2_FILLED = """---
created: 2099-01-01T00:00:00Z
project: {project}
branch: {branch}
head: 0123456789abcdef0123456789abcdef01234567
pr: {pr}
platform: linux
continues_from: none
state: {state}
context_mode: {mode}
---

# Handoff: v2 fixture

## Resume Card

- State: implementing, the parser is half done
- Next step: finish the parser in src/app.py
- Branch and PR: some-other-branch, none
- Blockers: none
- User constraints: never push without asking

## Current State Summary

The fixture describes work in progress with enough text to count as a filled section here.

## Codebase Understanding

### Critical Files

| File | Role | Why it matters |
|------|------|----------------|
| src/app.py | Entry point | The parser lives here |

## Work Completed

### Work Not Visible in Git

- None.

### Unpushed Changes

| File | Change |
|------|--------|
| src/util.py | Helper added |

### Decisions Made

| Decision | Options Considered | Rationale | Decided by |
|----------|-------------------|-----------|------------|
| Use a flat parser | flat, PyYAML | Scripts run on bare python3 | user |

### Other Table

| File | Note |
|------|------|
| src/elsewhere.py | Not a file source in a v2 handoff |

## Pending Work

### Immediate Next Steps

1. Finish the parser in the entry point and run the fixture tests again afterwards.

## Context for Resuming Agent

### Important Context

#### User Constraints

- Never push without asking; the user reviews every push before it goes out.

#### Learnings

- None.

### Assumptions Made

- None.

### Potential Gotchas & Key Patterns

- None.
"""


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=validate_handoff.git_env(),
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "util.py").write_text("y = 2\n", encoding="utf-8")
    (root / "src" / "elsewhere.py").write_text("z = 3\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", ".")
    _git(root, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "init")
    return root


def _write_v2(repo: Path, **values: str) -> Path:
    fields = {"project": str(repo), "branch": "main", "pr": "none", "state": "implementing"}
    fields["mode"] = "none"
    fields.update(values)
    handoffs = repo / ".claude" / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    path = handoffs / "2099-01-01-000000-v2.md"
    path.write_text(V2_FILLED.format(**fields), encoding="utf-8")
    return path


# --- scaffold --------------------------------------------------------------------------------


def test_scaffold_has_frontmatter_and_card_first(repo: Path) -> None:
    path = Path(create_handoff.generate_handoff(str(repo), "demo"))
    content = path.read_text(encoding="utf-8")
    fields, malformed = validate_handoff.parse_frontmatter(content)
    assert fields is not None and malformed == []
    assert set(fields) == set(validate_handoff.FRONTMATTER_KEYS)
    assert fields["branch"] == "main"
    assert fields["head"] == _git(repo, "rev-parse", "HEAD")
    assert fields["platform"] in ("linux", "windows", "macos")
    assert fields["continues_from"] == "none"
    assert fields["created"].endswith("Z")
    assert validate_handoff.check_resume_card(content) == []


@pytest.mark.parametrize(
    "dropped",
    [
        "Session Metadata",
        "Recent Commits",
        "Handoff Chain",
        "Architecture Overview",
        "Files Modified",
        "Key Patterns Discovered",
        "Tasks Finished",
        "Environment State",
        "Session duration",
        "Context mode:",
    ],
)
def test_scaffold_drops_old_sections(repo: Path, dropped: str) -> None:
    content = Path(create_handoff.generate_handoff(str(repo), "demo")).read_text(encoding="utf-8")
    assert dropped not in content


def test_scaffold_lists_uncommitted_files(repo: Path) -> None:
    (repo / "src" / "app.py").write_text("x = 3\n", encoding="utf-8")
    content = Path(create_handoff.generate_handoff(str(repo), "demo")).read_text(encoding="utf-8")
    assert "| src/app.py |" in content


def test_scaffold_lists_untracked_files(repo: Path) -> None:
    (repo / "src" / "new.py").write_text("n = 1\n", encoding="utf-8")
    content = Path(create_handoff.generate_handoff(str(repo), "demo")).read_text(encoding="utf-8")
    assert "| src/new.py |" in content


def test_scaffold_without_upstream_does_not_claim_pushed(repo: Path) -> None:
    content = Path(create_handoff.generate_handoff(str(repo), "demo")).read_text(encoding="utf-8")
    assert "everything is committed and pushed" not in content
    assert "[TODO: the branch has no upstream" in content


def test_scaffold_change_rows_are_todos(repo: Path) -> None:
    (repo / "src" / "app.py").write_text("x = 3\n", encoding="utf-8")
    content = Path(create_handoff.generate_handoff(str(repo), "demo")).read_text(encoding="utf-8")
    assert "| src/app.py | [TODO: what changed and why] |" in content


def test_scaffold_listing_failure_does_not_claim_clean(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    real_run_cmd = create_handoff.run_cmd

    def failing_ls_files(cmd: list[str], cwd: str | None = None) -> tuple[bool, str]:
        if cmd[:2] == ["git", "ls-files"]:
            return False, ""
        return real_run_cmd(cmd, cwd=cwd)

    monkeypatch.setattr(create_handoff, "run_cmd", failing_ls_files)
    content = Path(create_handoff.generate_handoff(str(repo), "demo")).read_text(encoding="utf-8")
    assert "everything is committed and pushed" not in content
    assert "[TODO: a git listing command failed" in content


def test_scaffold_outside_git_does_not_claim_pushed(tmp_path: Path) -> None:
    project = tmp_path / "plain"
    project.mkdir()
    content = Path(create_handoff.generate_handoff(str(project), "demo")).read_text(
        encoding="utf-8"
    )
    assert "everything is committed and pushed" not in content
    assert "[TODO: not a git repository" in content


def test_scaffold_with_upstream_and_nothing_pending(repo: Path, tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    (repo / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "ignore")
    _git(repo, "push", "-q")
    content = Path(create_handoff.generate_handoff(str(repo), "demo")).read_text(encoding="utf-8")
    assert "None: everything is committed and pushed." in content
    assert "no upstream" not in content


def test_scaffold_suggested_chain_link_is_a_todo(repo: Path) -> None:
    first = Path(create_handoff.generate_handoff(str(repo), "first"))
    second = Path(create_handoff.generate_handoff(str(repo), "second"))
    fields, _ = validate_handoff.parse_frontmatter(second.read_text(encoding="utf-8"))
    assert fields is not None
    assert fields["continues_from"] == f"[TODO: {first.name} or none]"


def test_scaffold_explicit_chain_link_is_written(repo: Path) -> None:
    first = Path(create_handoff.generate_handoff(str(repo), "first"))
    second = Path(create_handoff.generate_handoff(str(repo), "second", first.name))
    fields, _ = validate_handoff.parse_frontmatter(second.read_text(encoding="utf-8"))
    assert fields is not None and fields["continues_from"] == first.name


# --- frontmatter parser ----------------------------------------------------------------------


def test_parse_frontmatter_valid() -> None:
    fields, malformed = validate_handoff.parse_frontmatter(
        "---\nstate: in-review\nproject: C:\\work: x\n---\n# T\n"
    )
    assert fields == {"state": "in-review", "project": "C:\\work: x"}
    assert malformed == []


@pytest.mark.parametrize(
    "content",
    ["# Handoff: old\n\n## Session Metadata\n", "---\nstate: done\n# never closed\n", ""],
)
def test_parse_frontmatter_missing_or_unclosed(content: str) -> None:
    assert validate_handoff.parse_frontmatter(content) == (None, [])


def test_parse_frontmatter_reports_malformed_lines() -> None:
    fields, malformed = validate_handoff.parse_frontmatter(
        "---\nstate: done\n  nested: x\nno colon here\n---\n"
    )
    assert fields == {"state": "done"}
    assert malformed == ["  nested: x", "no colon here"]


@pytest.mark.parametrize(
    ("state", "pr", "expected"),
    [
        ("implementing", "none", "none"),
        ("pr-draft", "12", "review"),
        ("in-review", "12", "review"),
        ("ready-to-merge", "12", "ship"),
        ("ready-to-publish", "none", "ship"),
        ("blocked", "12", "review"),
        ("blocked", "none", "none"),
        ("done", "12", "admin"),
        ("shipping", "12", None),
    ],
)
def test_expected_context_mode(state: str, pr: str, expected: str | None) -> None:
    assert validate_handoff.expected_context_mode(state, pr) == expected


# --- validator -------------------------------------------------------------------------------


def test_filled_v2_scores_at_least_90(repo: Path) -> None:
    result = validate_handoff.validate_handoff(str(_write_v2(repo)))
    assert result["score"] >= 90
    assert result["frontmatter_problems"] == []
    assert result["card_problems"] == []
    assert result["missing_recommended"] == []


def test_unknown_state_is_a_problem(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result = validate_handoff.validate_handoff(str(_write_v2(repo, state="shipping")))
    assert result["frontmatter_problems"] == ["unknown state: shipping"]
    assert result["score"] == 90
    assert validate_handoff.print_report(result) is False
    assert "NEEDS WORK" in capsys.readouterr().out


@pytest.mark.parametrize("key", ["state", "mode"])
def test_empty_state_or_mode_is_a_problem(repo: Path, key: str) -> None:
    result = validate_handoff.validate_handoff(str(_write_v2(repo, **{key: ""})))
    name = "state" if key == "state" else "context_mode"
    assert f"empty value: {name}" in result["frontmatter_problems"]
    assert validate_handoff.print_report(result) is False


@pytest.mark.parametrize("key", ["project", "branch", "pr"])
def test_empty_other_key_is_a_problem(repo: Path, key: str) -> None:
    result = validate_handoff.validate_handoff(str(_write_v2(repo, **{key: ""})))
    assert f"empty value: {key}" in result["frontmatter_problems"]
    assert validate_handoff.print_report(result) is False


def test_card_with_unfilled_line_is_a_problem(repo: Path) -> None:
    path = _write_v2(repo)
    content = path.read_text(encoding="utf-8").replace("- Blockers: none\n", "- Blockers:\n")
    path.write_text(content, encoding="utf-8")
    assert validate_handoff.check_resume_card(content) == [
        "Resume Card has no filled line for: Blockers"
    ]


def test_card_problem_blocks_ready(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_v2(repo)
    content = path.read_text(encoding="utf-8").replace("- Blockers: none\n", "")
    path.write_text(content, encoding="utf-8")
    result = validate_handoff.validate_handoff(str(path))
    assert result["card_problems"] == ["Resume Card has no filled line for: Blockers"]
    assert validate_handoff.print_report(result) is False
    assert "NEEDS WORK" in capsys.readouterr().out


def test_filled_card_reports_ready(repo: Path) -> None:
    assert validate_handoff.print_report(validate_handoff.validate_handoff(str(_write_v2(repo))))


def test_empty_card_is_a_problem() -> None:
    content = "---\nstate: done\n---\n# Handoff: x\n\n## Resume Card\n\n## Next\n"
    assert validate_handoff.check_resume_card(content) == [
        "Resume Card has no filled line for: State, Next step, Branch and PR, Blockers, "
        "User constraints"
    ]


def test_context_mode_override_is_a_note_only(repo: Path) -> None:
    result = validate_handoff.validate_handoff(str(_write_v2(repo, mode="admin")))
    assert result["frontmatter_problems"] == []
    assert len(result["frontmatter_notes"]) == 1
    assert result["score"] == 100


def test_missing_card_costs_points(repo: Path) -> None:
    path = _write_v2(repo)
    content = path.read_text(encoding="utf-8")
    start = content.index("## Resume Card")
    path.write_text(content[:start] + content[content.index("## Current State") :], "utf-8")
    result = validate_handoff.validate_handoff(str(path))
    assert result["card_problems"] == ["Resume Card missing"]
    assert result["score"] == 95


def test_card_longer_than_15_lines() -> None:
    card = "\n".join(f"- line {i}" for i in range(16))
    content = f"---\nstate: done\n---\n# Handoff: x\n\n## Resume Card\n\n{card}\n\n## Next\n"
    assert validate_handoff.check_resume_card(content) == ["Resume Card has 16 lines (at most 15)"]


def test_important_context_counts_its_subsections(repo: Path) -> None:
    # Important Context has no text of its own in the fixture, only User Constraints/Learnings.
    result = validate_handoff.validate_handoff(str(_write_v2(repo)))
    assert result["required_complete"] is True


# --- staleness -------------------------------------------------------------------------------


def test_staleness_reads_frontmatter(repo: Path) -> None:
    meta = check_staleness.parse_handoff_metadata(str(_write_v2(repo)))
    # The card's "Branch and PR: some-other-branch" must not be read as the branch.
    assert meta["branch"] == "main"
    assert meta["created"] is not None
    assert meta["project_path"] == str(repo)
    # Only Critical Files and Unpushed Changes are file sources.
    assert meta["modified_files"] == ["src/app.py", "src/util.py"]


def test_staleness_v2_branch_matches(repo: Path) -> None:
    result = check_staleness.check_staleness(str(_write_v2(repo)))
    assert result["branch_matches"] is True
    assert result["referenced_files_missing"] == []


def test_staleness_v2_unfilled_branch_is_unknown(repo: Path) -> None:
    meta = check_staleness.parse_handoff_metadata(
        str(_write_v2(repo, branch="[TODO: branch name]"))
    )
    assert meta["branch"] is None


PRE_V2 = """# Handoff: old

## Session Metadata
- Created: 2099-01-01 00:00:00
- Project: /somewhere/else
- Branch: `feature/x`

### Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| src/app.py | edited | reason |
| /etc/passwd | absolute | skipped |
"""


def test_staleness_pre_v2_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "old.md"
    path.write_text(PRE_V2, encoding="utf-8")
    assert check_staleness.parse_handoff_metadata(str(path)) == {
        "created": datetime(2099, 1, 1, 0, 0, 0),
        "branch": "feature/x",
        "project_path": "/somewhere/else",
        "modified_files": ["src/app.py"],
    }


def test_staleness_pre_v2_iso_created(tmp_path: Path) -> None:
    path = tmp_path / "old.md"
    path.write_text(PRE_V2.replace("2099-01-01 00:00:00", "2099-01-01T00:00:00Z"), "utf-8")
    assert check_staleness.parse_handoff_metadata(str(path))["created"] is not None


# --- list ------------------------------------------------------------------------------------


def test_list_shows_state_for_v2_only(repo: Path, tmp_path: Path) -> None:
    v2 = _write_v2(repo, state="in-review", mode="review", pr="7")
    old = tmp_path / "old.md"
    old.write_text(PRE_V2, encoding="utf-8")
    assert list_handoffs.read_state(v2) == "in-review"
    assert list_handoffs.read_state(old) is None
