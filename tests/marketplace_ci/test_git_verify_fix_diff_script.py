"""git-kit's git-verify-fix-diff.py re-runs the Phase 2 verifiers on a fix's own diff (#578).

Exit codes: 0 clean or nothing to check, 1 a blocking finding on a changed file, 2 the verifiers
could not run (fail closed, never a pass). The end-to-end cases run the script against a real
temporary git repository whose `scripts/` is a copy of this repository's.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-verify-fix-diff.py"
SKILL = "plugins/demo-kit/skills/demo/SKILL.md"
GOOD = "---\nname: demo\ndescription: A demo skill.\nallowed-tools: Read\n---\n\n# Demo\n"


def _load_module():
    spec = importlib.util.spec_from_file_location("git_verify_fix_diff", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["git_verify_fix_diff"] = module
    spec.loader.exec_module(module)
    return module


M = _load_module()


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo, rel, text, message):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-f", "--", rel)
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    shutil.copytree(
        REPO / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    _git(root, "add", "--", "scripts")
    _git(root, "commit", "-q", "-m", "scripts")
    return root


def _run(repo, *args, extra_env=None):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(extra_env or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


# --- outside this repository ---------------------------------------------------------------------


def test_no_op_where_marketplace_ci_is_absent(tmp_path):
    result = _run(tmp_path, "--base", "0" * 40)
    assert result.returncode == 0
    assert "nothing to check" in result.stdout


# --- end to end, with the fix's parent commit as the base ---------------------------------------


def test_clean_fix_exits_zero(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, GOOD + "\nMore text.\n", "fix")
    result = _run(repo, "--base", base)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["blocking"] == []


def test_fix_that_breaks_a_touched_component_exits_one(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, "---\nname: demo\ndescription: [unclosed\n---\n", "bad fix")
    result = _run(repo, "--base", base)
    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["blocking"], payload
    assert {f["path"] for f in payload["blocking"]} == {SKILL}


def test_empty_change_set_is_not_a_pass(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    result = _run(repo, "--base", base)
    assert result.returncode == 2
    assert json.loads(result.stdout)["nothing_changed"] is True


# --- fail closed ---------------------------------------------------------------------------------


def test_short_base_sha_fails_closed(repo):
    _commit(repo, SKILL, GOOD, "add skill")
    result = _run(repo, "--base", "abc123")
    assert result.returncode == 2
    assert "could not run" in (result.stdout + result.stderr).lower()


def test_unknown_base_fails_closed(repo):
    _commit(repo, SKILL, GOOD, "add skill")
    result = _run(repo, "--base", "f" * 40)
    assert result.returncode == 2


def test_verifier_exception_is_not_a_pass(repo, monkeypatch):
    _commit(repo, SKILL, GOOD, "add skill")
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, SKILL, GOOD + "x\n", "fix")

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.chdir(repo)
    monkeypatch.setattr(M, "_load_verifiers", lambda _root, _base: (boom, lambda _raw: ()))
    assert M.main(["--base", base]) == 2


def test_missing_base_argument_is_a_usage_error(repo):
    assert _run(repo).returncode == 2


def test_help_is_a_successful_usage_request(repo):
    result = _run(repo, "--help")
    assert result.returncode == 0
    assert "--base" in result.stdout


# --- --worktree: verify the uncommitted fix before it is committed ------------------------------


def _write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_worktree_mode_flags_an_uncommitted_bad_fix(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _write(repo, SKILL, "---\nname: demo\ndescription: [unclosed\n---\n")
    result = _run(repo, "--worktree", "--base", base)
    assert result.returncode == 1, result.stdout + result.stderr
    assert {f["path"] for f in json.loads(result.stdout)["blocking"]} == {SKILL}


def test_worktree_mode_passes_an_uncommitted_clean_fix(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _write(repo, SKILL, GOOD + "\nMore text.\n")
    result = _run(repo, "--worktree", "--base", base)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["checked"] == [SKILL]


def test_worktree_mode_sees_a_new_untracked_file(repo):
    base = _commit(repo, "README.md", "x\n", "readme")
    _write(repo, SKILL, "---\nname: demo\ndescription: [unclosed\n---\n")
    result = _run(repo, "--worktree", "--base", base)
    assert result.returncode == 1, result.stdout + result.stderr


def test_worktree_mode_leaves_the_repository_untouched(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _write(repo, SKILL, GOOD + "\nMore text.\n")
    _write(repo, "new.txt", "n\n")
    before = (
        _git(repo, "status", "--porcelain"),
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "for-each-ref"),
        _git(repo, "stash", "list"),
    )
    index_before = (repo / ".git" / "index").read_bytes()
    _run(repo, "--worktree", "--base", base)
    after = (
        _git(repo, "status", "--porcelain"),
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "for-each-ref"),
        _git(repo, "stash", "list"),
    )
    assert after == before
    assert (repo / ".git" / "index").read_bytes() == index_before


# --- security review (#578): fail-open paths --------------------------------------------------

BAD = "---\nname: demo\ndescription: [unclosed\n---\n"


def test_component_with_a_space_in_its_path_is_judged(repo):
    path = "plugins/demo-kit/skills/my demo/SKILL.md"
    base = _commit(repo, path, GOOD, "add skill")
    _commit(repo, path, BAD, "bad fix")
    assert _run(repo, "--base", base).returncode == 1


def test_component_with_a_non_ascii_path_is_judged(repo):
    path = "plugins/demo-kit/skills/d\u00e9mo/SKILL.md"
    base = _commit(repo, path, GOOD, "add skill")
    _commit(repo, path, BAD, "bad fix")
    assert _run(repo, "--base", base).returncode == 1


def test_pure_rename_of_a_broken_component_still_blocks(repo):
    old, new = SKILL, "plugins/demo-kit/skills/demo2/SKILL.md"
    base = _commit(repo, old, BAD, "add broken skill")
    (repo / new).parent.mkdir(parents=True)
    _git(repo, "mv", old, new)
    _git(repo, "commit", "-q", "-m", "rename")
    assert _run(repo, "--base", base).returncode == 1


def test_user_diff_config_cannot_hide_the_touched_lines(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _git(repo, "config", "diff.noprefix", "true")
    _commit(repo, SKILL, BAD, "bad fix")
    assert _run(repo, "--base", base).returncode == 1


def test_runs_from_a_subdirectory_of_the_repository(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, BAD, "bad fix")
    result = _run(repo / "scripts", "--base", base)
    assert result.returncode == 1, result.stdout + result.stderr


def test_fix_cannot_weaken_the_verifier_that_judges_it(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    verifier = repo / "scripts/marketplace_ci/review_verifiers.py"
    verifier.write_text(
        verifier.read_text(encoding="utf-8") + "\nrun_verifiers = lambda *a, **k: ()\n",
        encoding="utf-8",
    )
    _write(repo, SKILL, BAD)
    result = _run(repo, "--worktree", "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "cannot judge" in (result.stdout + result.stderr)


def test_verifiers_present_at_base_but_missing_now_is_not_nothing_to_check(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _git(repo, "rm", "-q", "-r", "scripts/marketplace_ci")
    _git(repo, "commit", "-q", "-m", "remove verifiers")
    assert _run(repo, "--base", base).returncode == 2


# --- security re-review (#578): touched-file logic and untrusted-grader guards -------------------


def _fake_finding(path, line, components=()):
    from types import SimpleNamespace

    finding = SimpleNamespace(
        rule="r-x", path=path, line=line, evidence="e", remediation="r", components=components
    )
    return SimpleNamespace(name="fake", findings=(finding,), checked=(path,))


def test_every_finding_on_the_changed_set_blocks_whatever_its_line_or_path(repo, monkeypatch):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, GOOD + "\nMore.\n", "fix")
    outcome = _fake_finding("plugins/old/skills/gone/SKILL.md", None, ("a:*",))
    monkeypatch.syspath_prepend(str(REPO))
    from scripts.marketplace_ci.git_state import parse_name_status_z

    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        M, "_load_verifiers", lambda _r, _b: (lambda *a, **k: (outcome,), parse_name_status_z)
    )
    assert M.main(["--base", base]) == 1


def test_fix_touching_the_verifiers_cannot_be_judged_by_them(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, "scripts/marketplace_ci/extra.py", "x = 1\n", "touch verifiers")
    result = _run(repo, "--base", base)
    assert result.returncode == 2
    assert "cannot judge" in (result.stdout + result.stderr)


def test_fix_touching_the_sync_registry_is_not_verified(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, ".claude/marketplace-sync.json", "{}\n", "touch registry")
    assert _run(repo, "--base", base).returncode == 2


def test_fix_touching_the_driver_itself_is_not_verified(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, "plugins/git-kit/scripts/git-verify-fix-diff.py", "x = 1\n", "touch driver")
    assert _run(repo, "--base", base).returncode == 2


def test_committed_mode_judges_the_commit_not_the_disk(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, BAD, "bad fix")
    _write(repo, SKILL, GOOD)  # an uncommitted "repair" must not rescue the committed fix
    assert _run(repo, "--base", base).returncode == 1


def test_git_dir_in_the_environment_cannot_redirect_the_verifiers(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _write(repo, SKILL, BAD)
    env = {"GIT_DIR": str(repo / ".git")}
    result = _run(repo, "--worktree", "--base", base, extra_env=env)
    assert result.returncode == 1, result.stdout + result.stderr


def test_base_that_is_not_an_ancestor_is_refused(repo):
    _commit(repo, SKILL, GOOD, "add skill")
    _git(repo, "checkout", "-q", "-b", "other")
    other = _commit(repo, "other.txt", "o\n", "other branch")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, SKILL, GOOD + "\nMore.\n", "fix")
    assert _run(repo, "--base", other).returncode == 2


def test_malformed_base_inside_a_repository_is_not_nothing_to_check(repo):
    _commit(repo, SKILL, GOOD, "add skill")
    assert _run(repo, "--base", "").returncode == 2
