"""Fixture tests for session-handoff's file-reference lookup.

Covers validate_handoff.py and check_staleness.py.
"""

import subprocess
import sys
from pathlib import Path

import pytest

HANDOFF_SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "session-handoff" / "scripts"
if str(HANDOFF_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(HANDOFF_SCRIPTS))

import check_staleness  # noqa: E402
import validate_handoff  # noqa: E402

FILLED = """# Handoff: fixture

## Session Metadata
- Created: 2099-01-01 00:00:00
- Branch: main

## Current State Summary
The fixture handoff describes a finished piece of work with enough text to count as filled.

### Architecture Overview
Small fixture.

### Critical Files
{critical}

### Files Modified
None.

### Decisions Made
None worth noting for this fixture.

## Important Context
The fixture exists only to exercise the file reference lookup in the validator script.

### Immediate Next Steps
1. Nothing further is needed; this text only satisfies the length requirement.

### Assumptions Made
None.

### Potential Gotchas
None.
"""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "plugins" / "p" / "skills" / "plugin-rulebook").mkdir(parents=True)
    (root / "plugins" / "p" / "skills" / "plugin-rulebook" / "SKILL.md").write_text("x")
    (root / "plugins" / "p" / "scripts").mkdir(parents=True)
    (root / "plugins" / "p" / "scripts" / "deep_file.py").write_text("x")
    (root / "README.md").write_text("x")
    (root / ".claude" / "handoffs").mkdir(parents=True)
    (root / ".gitignore").write_text(".claude/handoffs/\n")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "init")
    (root / "new_untracked.py").write_text("x")  # untracked, not ignored
    return root


def _status(repo: Path, ref: str) -> str:
    files = validate_handoff.list_repo_files(str(repo))
    return validate_handoff.resolve_reference(ref, str(repo), files)


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("README.md", "verified"),  # (a) repo-relative, exists
        ("plugins/x/nope.py", "missing"),  # (b) repo-relative, absent
        ("deep_file.py", "verified"),  # (c) bare name two levels down
        ("ghost_file.py", "missing"),  # (d) bare name nowhere
        ("plugin-rulebook/SKILL.md", "verified"),  # (e) partial path
        ("rulebook/SKILL.md", "missing"),  # (f) "/" boundary: no match on plugin-rulebook/
        ("new_untracked.py", "verified"),  # (i) untracked file
        ("./README.md", "verified"),
    ],
)
def test_resolve_reference_in_repo(repo: Path, ref: str, expected: str) -> None:
    assert _status(repo, ref) == expected


def test_line_number_suffix_resolves(repo: Path) -> None:  # (g)
    content = "See `deep_file.py:123`."
    existing, missing, _ = validate_handoff.check_file_references(content, str(repo))
    assert existing == ["deep_file.py"]
    assert missing == []


def test_parent_segment_never_verified(repo: Path) -> None:  # (h)
    (repo.parent / "outside.txt").write_text("x")
    assert _status(repo, "../outside.txt") == "missing"
    assert _status(repo, "plugins/../../outside.txt") == "missing"


def test_not_a_git_repo(tmp_path: Path) -> None:  # (j)
    root = tmp_path / "plain"
    root.mkdir()
    if validate_handoff.list_repo_files(str(root)) is not None:
        pytest.skip("tmp_path is inside a git repository on this machine")
    assert validate_handoff.resolve_reference("deep_file.py", str(root), None) == "unverifiable"
    assert validate_handoff.resolve_reference("plugins/x/nope.py", str(root), None) == "missing"


def _write_handoff(repo: Path, critical: str, extra: str = "") -> Path:
    path = repo / ".claude" / "handoffs" / "2099-01-01-000000-fixture.md"
    path.write_text(FILLED.format(critical=critical) + extra, encoding="utf-8")
    return path


def test_score_with_only_resolvable_shapes_is_100(repo: Path) -> None:  # (k)
    refs = "- `deep_file.py`\n- `plugin-rulebook/SKILL.md`\n- `deep_file.py:7`"
    path = _write_handoff(repo, refs)
    result = validate_handoff.validate_handoff(str(path))
    assert result["files_missing"] == []
    assert result["score"] == 100


def test_score_with_one_truly_missing_path_is_95(repo: Path) -> None:  # (k)
    path = _write_handoff(repo, "- `deep_file.py`\n- `plugins/x/nope.py`")
    result = validate_handoff.validate_handoff(str(path))
    assert result["files_missing"] == ["plugins/x/nope.py"]
    assert result["score"] == 95


def test_sibling_handoff_name_resolves(repo: Path) -> None:
    (repo / ".claude" / "handoffs" / "2099-01-01-000001-earlier.md").write_text("x")
    path = _write_handoff(repo, "- `2099-01-01-000001-earlier.md`")
    assert validate_handoff.validate_handoff(str(path))["files_missing"] == []


def test_secret_still_blocks(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:  # (l)
    path = _write_handoff(repo, "- `deep_file.py`", extra="\nDATABASE_PASSWORD=correct-horse\n")
    result = validate_handoff.validate_handoff(str(path))
    assert result["secrets_found"]
    assert validate_handoff.print_report(result) is False
    assert "BLOCKED" in capsys.readouterr().out


def test_staleness_partial_path_in_table_not_missing(repo: Path) -> None:
    existing, missing = check_staleness.check_files_exist(
        ["plugin-rulebook/SKILL.md", "plugins/gone/deleted.py"], str(repo)
    )
    assert existing == ["plugin-rulebook/SKILL.md"]
    assert missing == ["plugins/gone/deleted.py"]


def test_staleness_parent_segment_still_contained(repo: Path) -> None:
    (repo.parent / "outside.txt").write_text("x")
    existing, missing = check_staleness.check_files_exist(["../outside.txt"], str(repo))
    assert existing == []
    assert missing == ["../outside.txt"]
