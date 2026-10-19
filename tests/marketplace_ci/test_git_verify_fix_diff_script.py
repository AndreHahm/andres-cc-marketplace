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
UPSTREAM = "acme/demo"  # the repository the fixtures' origin remote names


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
    # The target branch the verifiers are trusted from: origin/HEAD at the scripts commit.
    _git(root, "remote", "add", "origin", f"https://github.com/{UPSTREAM}.git")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return root


def _run(repo, *args, extra_env=None):
    if "--upstream" not in args and "--help" not in args:
        args = (*args, "--upstream", UPSTREAM)
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
    assert M.main(["--base", base, "--upstream", UPSTREAM]) == 2


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


def test_worktree_mode_writes_no_snapshot_object_into_the_repository(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _write(repo, SKILL, GOOD + "\nMore text.\n")
    _write(repo, "untracked-secret.txt", "api-key-for-the-test-only\n")
    changed_blob = _git(repo, "hash-object", SKILL)
    untracked_blob = _git(repo, "hash-object", "untracked-secret.txt")
    result = _run(repo, "--worktree", "--base", base)
    assert result.returncode == 0, result.stdout + result.stderr
    for blob in (changed_blob, untracked_blob):
        probe = subprocess.run(["git", "cat-file", "-e", blob], cwd=repo, capture_output=True)
        assert probe.returncode != 0, f"{blob} was written into the repository's object store"


def test_worktree_mode_from_a_linked_worktree_writes_nothing_into_the_common_store(repo, tmp_path):
    _commit(repo, SKILL, GOOD, "add skill")
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", "-q", "-b", "linked-branch", str(linked))
    base = _git(linked, "rev-parse", "HEAD")
    _write(linked, SKILL, GOOD + "\nMore text.\n")
    _write(linked, "untracked-secret.txt", "linked-worktree-secret\n")
    blobs = [_git(linked, "hash-object", p) for p in (SKILL, "untracked-secret.txt")]
    result = _run(linked, "--worktree", "--base", base)
    assert result.returncode == 0, result.stdout + result.stderr
    for blob in blobs:
        probe = subprocess.run(["git", "cat-file", "-e", blob], cwd=repo, capture_output=True)
        assert probe.returncode != 0, f"{blob} reached the common object store"


def test_worktree_mode_works_in_a_repository_path_containing_a_colon(repo, tmp_path):
    base = _commit(repo, SKILL, GOOD, "add skill")
    moved = tmp_path / "re:po"
    repo.rename(moved)
    _write(moved, SKILL, GOOD + "\nMore text.\n")
    result = _run(moved, "--worktree", "--base", base)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("mode", [["--worktree"], []])
def test_no_temporary_directory_is_left_behind(repo, tmp_path, mode):
    base = _commit(repo, SKILL, GOOD, "add skill")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    if mode:
        _write(repo, SKILL, GOOD + "\nMore text.\n")
    else:
        _commit(repo, SKILL, GOOD + "\nMore text.\n", "fix")
    result = _run(repo, *mode, "--base", base, extra_env={"TMPDIR": str(scratch)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(scratch.iterdir()) == []


def test_worktree_mode_refuses_a_sparse_checkout_but_committed_mode_does_not(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _git(repo, "config", "core.sparseCheckout", "true")
    _write(repo, SKILL, GOOD + "\nMore text.\n")
    refused = _run(repo, "--worktree", "--base", base)
    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert "sparse" in (refused.stdout + refused.stderr)
    _git(repo, "add", "--", SKILL)
    _git(repo, "commit", "-q", "-m", "fix")
    assert _run(repo, "--base", base).returncode == 0


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


def test_git_failure_in_a_subdirectory_is_not_nothing_to_check(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    (repo / ".git" / "config").write_text("[broken\n", encoding="utf-8")
    result = _run(repo / "scripts", "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "nothing to check" not in result.stdout


def test_verifiers_present_at_base_but_missing_now_is_not_nothing_to_check(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _git(repo, "rm", "-q", "-r", "scripts/marketplace_ci")
    _git(repo, "commit", "-q", "-m", "remove verifiers")
    assert _run(repo, "--base", base).returncode == 2


def test_verifiers_come_from_the_target_branch_not_from_a_weakened_earlier_pr_commit(repo):
    # The PR's own earlier commit stubs the grader out; --base is the commit after it, so the
    # fix diff itself never touches scripts/marketplace_ci/. Loading the verifiers from --base
    # would import that stub and pass the bad fix.
    stub = "def run_verifiers(*_a, **_k):\n    return ()\n"
    _commit(repo, "scripts/marketplace_ci/review_verifiers.py", stub, "weaken the grader")
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, "---\nname: demo\ndescription: [unclosed\n---\n", "bad fix")
    result = _run(repo, "--base", base)
    assert result.returncode == 1, result.stdout + result.stderr
    assert {f["path"] for f in json.loads(result.stdout)["blocking"]} == {SKILL}


def _repo_with_verifiers_only_on_target(tmp_path):
    """main gains the verifiers after `feat` forked from it, so `feat`'s own tree lacks them."""
    root = tmp_path / "late"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _commit(root, "README.md", "x\n", "root")
    _git(root, "branch", "feat")
    shutil.copytree(
        REPO / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    _git(root, "add", "--", "scripts")
    _git(root, "commit", "-q", "-m", "add verifiers")
    _git(root, "remote", "add", "origin", f"https://github.com/{UPSTREAM}.git")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    _git(root, "checkout", "-q", "feat")
    return root


def test_branch_forked_before_the_verifiers_existed_is_not_nothing_to_check(tmp_path):
    root = _repo_with_verifiers_only_on_target(tmp_path)
    base = _commit(root, SKILL, GOOD, "add skill")
    _commit(root, SKILL, GOOD + "\nMore text.\n", "fix")
    result = _run(root, "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "nothing to check" not in result.stdout


def test_unrelated_history_is_not_nothing_to_check(repo):
    _git(repo, "checkout", "-q", "--orphan", "other")
    _git(repo, "rm", "-q", "-r", "-f", "scripts")
    base = _commit(repo, "other.txt", "o\n", "unrelated root")
    _commit(repo, "other.txt", "o2\n", "unrelated change")
    result = _run(repo, "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "nothing to check" not in result.stdout


def test_a_module_next_to_the_driver_cannot_shadow_the_standard_library(repo, tmp_path):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, GOOD + "\nMore text.\n", "fix")
    driver_dir = tmp_path / "driver"
    driver_dir.mkdir()
    marker = tmp_path / "shadow-ran"
    shutil.copy(SCRIPT, driver_dir / SCRIPT.name)
    (driver_dir / "argparse.py").write_text(
        f"open({str(marker)!r}, 'w').close()\nraise ImportError('shadow')\n", encoding="utf-8"
    )
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, str(driver_dir / SCRIPT.name), "--base", base, "--upstream", UPSTREAM],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert not marker.exists(), "a PR-controlled sibling module was imported"
    assert result.returncode == 0, result.stdout + result.stderr


def _fix_pair(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, GOOD + "\nMore text.\n", "fix")
    return base


def test_origin_that_is_a_contributors_fork_is_refused(repo):
    base = _fix_pair(repo)
    _git(repo, "remote", "set-url", "origin", "https://github.com/mallory/demo.git")
    result = _run(repo, "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "mallory/demo" in result.stdout + result.stderr


def test_origin_that_is_not_a_github_url_is_refused(repo):
    base = _fix_pair(repo)
    _git(repo, "remote", "set-url", "origin", "/srv/git/demo.git")
    result = _run(repo, "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "not a GitHub URL" in result.stdout + result.stderr


def test_a_repository_with_no_origin_remote_is_refused(repo):
    base = _fix_pair(repo)
    _git(repo, "remote", "remove", "origin")
    # removing the remote also deletes refs/remotes/origin/*, so origin/HEAD is gone as well
    result = _run(repo, "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:acme/demo.git",
        "ssh://git@github.com/acme/demo.git",
        "https://github.com/acme/demo",
        "https://github.com/ACME/Demo.git",
    ],
)
def test_the_usual_github_url_forms_of_the_upstream_are_accepted(repo, url):
    base = _fix_pair(repo)
    _git(repo, "remote", "set-url", "origin", url)
    result = _run(repo, "--base", base)
    assert result.returncode == 0, result.stdout + result.stderr


def test_upstream_is_required_and_must_look_like_owner_repo(repo):
    base = _fix_pair(repo)
    missing = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", base], cwd=repo, capture_output=True, text=True
    )
    assert missing.returncode == 2
    for bad in ("acme", "acme/demo/extra", "acme/de mo", "--evil"):
        assert _run(repo, "--base", base, "--upstream", bad).returncode == 2, bad


def test_no_target_branch_ref_means_no_trusted_verifiers(repo):
    base = _commit(repo, SKILL, GOOD, "add skill")
    _commit(repo, SKILL, GOOD + "\nMore text.\n", "fix")
    _git(repo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    result = _run(repo, "--base", base)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "origin/HEAD" in result.stdout + result.stderr


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
    assert M.main(["--base", base, "--upstream", UPSTREAM]) == 1


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


# --- commands planted in git's own configuration (#588) ------------------------------------------
# `git diff`/`git add` on a dirty tree can run a configured fsmonitor command and the
# post-index-change hook, append to a GIT_TRACE file and honor GIT_CONFIG_* variables; a clone's
# template hooks and the global configuration reach `git checkout`. Each route writes its own marker
# file so a failure names the route; the control tests prove each planted command really fires.


def _marker_script(path, marker):
    path.write_text(f'#!/bin/sh\necho ran >> "{marker}"\n', encoding="utf-8")
    path.chmod(0o755)
    return path


def _plant_hostile_git(repo, tmp_path):
    """Plant one command per route outside the repository; return (markers, extra_env)."""
    plant = tmp_path / "plant"
    plant.mkdir()
    names = ("local_fsmonitor", "post_index_change", "config_env", "template")
    markers = {name: plant / f"{name}.marker" for name in names}
    markers["trace"] = plant / "trace.out"  # git appends here when GIT_TRACE names it

    _git(
        repo,
        "config",
        "core.fsmonitor",
        str(_marker_script(plant / "a.sh", markers["local_fsmonitor"])),
    )
    hook = repo / ".git" / "hooks" / "post-index-change"
    _marker_script(hook, markers["post_index_change"])

    home = plant / "home"
    template = plant / "template"
    (template / "hooks").mkdir(parents=True)
    _marker_script(template / "hooks" / "post-checkout", markers["template"])
    home.mkdir()
    # The global configuration reaches the clone's `git checkout` through its template hooks.
    (home / ".gitconfig").write_text(f"[init]\n\ttemplateDir = {template}\n", encoding="utf-8")
    injected = _marker_script(plant / "c.sh", markers["config_env"])
    env = {
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "GIT_TRACE": str(markers["trace"]),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": str(injected),
    }
    return markers, env


def _fix_in_repo(repo, *, committed):
    """A base commit and a fix on top of it; the fix is left uncommitted unless `committed`."""
    base = _commit(repo, SKILL, GOOD, "add skill")
    if committed:
        _commit(repo, SKILL, GOOD + "\nMore text.\n", "fix")
    else:
        _write(repo, SKILL, GOOD + "\nMore text.\n")
    return base


def _ran(markers):
    return sorted(name for name, path in markers.items() if path.exists())


def test_control_plain_git_runs_every_planted_command(repo, tmp_path):
    """Without the script's hardening each route fires, so the tests below are not vacuous."""
    _fix_in_repo(repo, committed=False)
    markers, extra = _plant_hostile_git(
        repo, tmp_path
    )  # after the setup: its git calls must not fire them
    assert _ran(markers) == []
    # GIT_CONFIG_* outranks the repository's own core.fsmonitor, so each is exercised on its own.
    # An in-process main() call elsewhere in this file pins GIT_* in os.environ; start without them.
    inherited = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    without_injection = {k: v for k, v in extra.items() if not k.startswith("GIT_CONFIG_")}
    for planted in (without_injection, extra):
        env = {**inherited, **planted}
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, env=env, capture_output=True, check=True
        )
    env = {**inherited, **extra}
    clone = tmp_path / "control-clone"
    for args, cwd in (
        (["clone", "--shared", "--no-checkout", "-q", str(repo), str(clone)], repo),
        (["checkout", "-q", "--detach", "HEAD"], clone),
    ):
        subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, check=True)
    assert _ran(markers) == sorted(markers)


@pytest.mark.parametrize("worktree", [True, False])
def test_planted_commands_never_run(repo, tmp_path, worktree):
    base = _fix_in_repo(repo, committed=not worktree)
    markers, extra = _plant_hostile_git(repo, tmp_path)
    assert _ran(markers) == []
    result = _run(repo, "--base", base, *(["--worktree"] if worktree else []), extra_env=extra)
    assert result.returncode in (0, 1), result.stdout + result.stderr
    assert _ran(markers) == []


def test_a_git_earlier_on_path_inside_the_repository_is_never_run(repo, tmp_path):
    marker = tmp_path / "fake-git.marker"
    fake = repo / "fakebin" / "git"
    fake.parent.mkdir()
    _marker_script(fake, marker)
    base = _commit(repo, SKILL, GOOD, "add skill")
    result = _run(
        repo, "--base", base, extra_env={"PATH": f"{fake.parent}{os.pathsep}{os.environ['PATH']}"}
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert not marker.exists()


# --- the "git is not inside the repository" guard (security review of PR #610) ---------------


def _make_repo(path):
    path.mkdir(parents=True)
    commit = ["-c", "user.email=t@example.com", "-c", "user.name=t"]
    for args in (
        ["init", "-q", "-b", "main"],
        [*commit, "commit", "-q", "--allow-empty", "-m", "x"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    return path


def _stub_git(directory):
    directory.mkdir(parents=True, exist_ok=True)
    stub = directory / "git"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _find_git_from(monkeypatch, cwd, *path_dirs):
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("PATH", os.pathsep.join([*map(str, path_dirs), "/usr/bin", "/bin"]))
    return M._find_git()


def test_the_guard_still_accepts_a_git_outside_the_repository(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo")
    tools = _stub_git(tmp_path / "tools").parent
    assert _find_git_from(monkeypatch, repo, tools) == str(tools / "git")
    assert _find_git_from(monkeypatch, repo) is not None  # the system git


def test_a_git_planted_in_the_repository_is_refused_from_any_subdirectory(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo")
    plant = _stub_git(repo / "bin").parent
    deeper = repo / "sub" / "deeper"
    deeper.mkdir(parents=True)
    for start in (repo, repo / "sub", deeper):
        assert _find_git_from(monkeypatch, start, plant) is None, start


def test_a_link_outside_the_repository_that_points_into_it_is_refused(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo")
    target = _stub_git(repo / "bin")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "git").symlink_to(target)
    assert _find_git_from(monkeypatch, repo, outside) is None


def test_a_git_in_the_main_checkout_is_refused_from_a_linked_worktree(tmp_path, monkeypatch):
    main = _make_repo(tmp_path / "main")
    linked = tmp_path / "linked"
    subprocess.run(
        ["git", "worktree", "add", "-q", "--detach", str(linked)],
        cwd=main,
        check=True,
        capture_output=True,
    )
    plant = _stub_git(main / "bin").parent
    assert _find_git_from(monkeypatch, linked, plant) is None
    assert _find_git_from(monkeypatch, linked / ".." / "linked", plant) is None


def test_a_git_in_an_outer_repository_is_refused_from_a_nested_one(tmp_path, monkeypatch):
    outer = _make_repo(tmp_path / "outer")
    inner = _make_repo(outer / "vendor" / "inner")
    plant = _stub_git(outer / "bin").parent
    assert _find_git_from(monkeypatch, inner, plant) is None


def test_a_git_entry_that_cannot_be_read_is_not_trusted(tmp_path, monkeypatch):
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / ".git").write_text("not a pointer\n", encoding="utf-8")
    tools = _stub_git(tmp_path / "tools").parent
    assert _find_git_from(monkeypatch, broken, tools) is None


def _file_system_ignores_case(directory):
    probe = directory / "CaseProbe"
    probe.mkdir()
    return (directory / "caseprobe").exists()


def test_a_path_spelled_with_other_letter_case_is_still_inside_the_repository(
    tmp_path, monkeypatch
):
    if not _file_system_ignores_case(tmp_path):
        pytest.skip("needs a case-insensitive file system (the default on macOS)")
    repo = _make_repo(tmp_path / "Repo")
    plant = _stub_git(repo / "bin").parent
    respelled = tmp_path / "repo" / "bin"
    assert _find_git_from(monkeypatch, repo, respelled) is None
    assert plant.exists()
