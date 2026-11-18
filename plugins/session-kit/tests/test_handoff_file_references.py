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
    # The same scrubbed environment the scripts use, so a run from a git hook (which exports
    # GIT_DIR or GIT_INDEX_FILE) cannot point these fixture commands at the caller's repo.
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, env=validate_handoff.git_env()
    )


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
    existing, missing = validate_handoff.check_file_references(content, str(repo))
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
    # Without a repo file list a bare name can only be tried at the root, so a miss is a miss.
    (root / "here.md").write_text("x")
    assert validate_handoff.resolve_reference("here.md", str(root), None) == "verified"
    assert validate_handoff.resolve_reference("deep_file.py", str(root), None) == "missing"
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


@pytest.mark.parametrize(
    "ident",
    ["os.geteuid", "json.loads", "timezone.utc", "code.claude.com", "base.sha", "Tests.OPTIONAL"],
)
def test_code_identifier_is_not_a_file_reference(repo: Path, ident: str) -> None:
    path = _write_handoff(repo, f"- `{ident}`\n| {ident} | x |\n- {ident}:12")
    result = validate_handoff.validate_handoff(str(path))
    assert result["files_missing"] == []
    assert result["score"] == 100


def test_bare_name_with_file_extension_still_checked(repo: Path) -> None:
    path = _write_handoff(repo, "- `ghost_file.py`\n- `GHOST.MD`\n- `README.md`")
    result = validate_handoff.validate_handoff(str(path))
    assert result["files_missing"] == ["GHOST.MD", "ghost_file.py"]


@pytest.mark.parametrize("name", ["schema.proto", "query.graphql", "App.vue", "main.tf"])
def test_bare_name_with_less_common_extension_still_checked(repo: Path, name: str) -> None:
    path = _write_handoff(repo, f"- `{name}`")
    assert validate_handoff.validate_handoff(str(path))["files_missing"] == [name]


def test_path_with_slash_and_unknown_extension_still_checked(repo: Path) -> None:
    path = _write_handoff(repo, "- `plugins/x/thing.geteuid`")
    assert validate_handoff.validate_handoff(str(path))["files_missing"] == [
        "plugins/x/thing.geteuid"
    ]


def test_unstaged_deletion_is_missing(repo: Path) -> None:
    # git ls-files --cached still lists a tracked file deleted but not yet staged.
    (repo / "plugins" / "p" / "scripts" / "deep_file.py").unlink()
    for ref in ("plugins/p/scripts/deep_file.py", "scripts/deep_file.py", "deep_file.py"):
        assert _status(repo, ref) == "missing", ref
    path = _write_handoff(repo, "- `deep_file.py`")
    assert validate_handoff.validate_handoff(str(path))["files_missing"] == ["deep_file.py"]
    existing, missing = check_staleness.check_files_exist(["scripts/deep_file.py"], str(repo))
    assert existing == []
    assert missing == ["scripts/deep_file.py"]


def test_bare_name_verified_by_surviving_copy(repo: Path) -> None:
    # One of two same-named tracked files deleted: the surviving one still verifies.
    (repo / "other").mkdir()
    (repo / "other" / "deep_file.py").write_text("x")
    (repo / "plugins" / "p" / "scripts" / "deep_file.py").unlink()
    assert _status(repo, "deep_file.py") == "verified"


def test_exact_deleted_path_not_verified_by_longer_path(repo: Path) -> None:
    # src/task.py is deleted (not staged); examples/src/task.py must not stand in for it.
    for rel in ("src/task.py", "examples/src/task.py"):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "two")
    (repo / "src" / "task.py").unlink()
    assert _status(repo, "src/task.py") == "missing"
    assert _status(repo, "examples/src/task.py") == "verified"


def test_doubled_slash_matches_like_single(repo: Path) -> None:
    assert _status(repo, "scripts//deep_file.py") == "verified"
    assert _status(repo, "scripts/./deep_file.py") == "verified"


def test_handoff_dir_fallback_only_for_bare_names(repo: Path) -> None:
    handoffs = repo / ".claude" / "handoffs"
    (handoffs / "docs").mkdir()
    (handoffs / "docs" / "design.md").write_text("x")
    (handoffs / "2099-01-01-000001-earlier.md").write_text("x")
    path = _write_handoff(repo, "- `docs/design.md`\n- `2099-01-01-000001-earlier.md`")
    assert validate_handoff.validate_handoff(str(path))["files_missing"] == ["docs/design.md"]


@pytest.mark.parametrize("name", ["main.cc", "README.mdx"])
def test_bare_cc_and_mdx_names_checked(repo: Path, name: str) -> None:
    path = _write_handoff(repo, f"- `{name}`")
    assert validate_handoff.validate_handoff(str(path))["files_missing"] == [name]


def test_local_path_starting_with_http_is_checked(repo: Path) -> None:
    path = _write_handoff(repo, "- `http/client.py`\n- `httpx_client.py`")
    result = validate_handoff.validate_handoff(str(path))
    assert result["files_missing"] == ["http/client.py", "httpx_client.py"]


def test_staleness_never_turns_absolute_path_into_relative(repo: Path) -> None:
    (repo / "etc").mkdir()
    (repo / "etc" / "passwd").write_text("x")
    existing, missing = check_staleness.check_files_exist(["/etc/passwd"], str(repo))
    assert existing == []
    assert missing == ["/etc/passwd"]
    table = "| /etc/passwd |\n| plugins/p/scripts/deep_file.py |\n"
    handoff = repo / ".claude" / "handoffs" / "t.md"
    handoff.write_text(table, encoding="utf-8")
    files = check_staleness.parse_handoff_metadata(str(handoff))["modified_files"]
    assert files == ["plugins/p/scripts/deep_file.py"]


def test_git_lookup_ignores_inherited_repo_location(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git" / "index"))
    files = validate_handoff.list_repo_files(str(repo))
    assert files is not None
    assert "plugins/p/scripts/deep_file.py" in files
