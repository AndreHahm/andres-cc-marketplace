"""git-kit's git-run-trusted-fix-diff.py runs the driver as committed on the target branch (#656).

Exit codes: the driver's own, 2 when a check here fails (nothing from the target branch ran), 4 when
the trusted commit has no driver. The end-to-end cases use a real temporary git repository whose
trusted commit carries a stand-in driver that reports what it was run with.
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-run-trusted-fix-diff.py"
DRIVER = REPO / "plugins/git-kit/scripts/git-verify-fix-diff.py"
DRIVER_PATH = "plugins/git-kit/scripts/git-verify-fix-diff.py"
UPSTREAM = "acme/demo"
# Prints how it was run, then exits with the code named by the marker file next to the repository.
STAND_IN = (
    "import json, os, sys\n"
    "print(json.dumps({'argv': sys.argv[1:], 'file': __file__, 'cwd': os.getcwd()}))\n"
    "raise SystemExit(int(os.environ.get('STAND_IN_EXIT', '0')))\n"
)


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
    _commit(root, DRIVER_PATH, STAND_IN, "trusted driver")
    _git(root, "remote", "add", "origin", f"https://github.com/{UPSTREAM}.git")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return root


def _run(repo, *args, env=None):
    base = _git(repo, "rev-parse", "HEAD")
    given = args or ("--upstream", UPSTREAM, "--target-branch", "main", "--base", base)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *given],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})},
    )


def test_runs_the_driver_from_the_trusted_commit_not_the_tree(repo):
    base = _commit(repo, "x.txt", "x", "a fix commit")
    # The branch rewrites the driver in its own tree; the trusted copy must still run.
    _commit(repo, DRIVER_PATH, "raise SystemExit(9)\n", "tampered driver")
    done = _run(
        repo, "--upstream", UPSTREAM, "--target-branch", "main", "--base", base, "--worktree"
    )
    assert done.returncode == 0, done.stderr
    seen = json.loads(done.stdout)
    assert seen["argv"] == [
        "--base",
        base,
        "--upstream",
        UPSTREAM,
        "--target-branch",
        "main",
        "--worktree",
    ]
    assert Path(seen["cwd"]).resolve() == repo.resolve()


def test_the_driver_runs_from_a_private_temp_file_that_is_removed(repo):
    done = _run(repo)
    assert done.returncode == 0, done.stderr
    ran_from = Path(json.loads(done.stdout)["file"])
    assert ran_from.name == "git-verify-fix-diff.py"
    assert not ran_from.exists() and not ran_from.parent.exists()
    assert repo.resolve() not in ran_from.resolve().parents


def test_the_drivers_exit_code_is_passed_through(repo):
    assert _run(repo, env={"STAND_IN_EXIT": "1"}).returncode == 1


def test_origin_that_is_not_the_upstream_refuses_before_running_anything(repo):
    _git(repo, "remote", "set-url", "origin", "https://github.com/evil/fork.git")
    done = _run(repo)
    assert done.returncode == 2
    assert "is not acme/demo" in done.stderr
    assert done.stdout == ""


def test_origin_that_is_not_a_github_url_refuses(repo):
    _git(repo, "remote", "set-url", "origin", "https://example.com/acme/demo.git")
    done = _run(repo)
    assert done.returncode == 2 and done.stdout == ""


def test_trusted_commit_off_the_default_branch_refuses(repo):
    # A PR into a base branch the default branch has not merged: the commit supplying the driver
    # would be author-chosen code.
    _git(repo, "checkout", "-q", "-b", "side")
    _commit(repo, DRIVER_PATH, "print('attacker')\n", "side driver")
    _git(repo, "update-ref", "refs/remotes/origin/side", "HEAD")
    done = _run(
        repo,
        "--upstream",
        UPSTREAM,
        "--target-branch",
        "side",
        "--base",
        _git(repo, "rev-parse", "HEAD"),
    )
    assert done.returncode == 2
    assert "not on the default branch" in done.stderr
    assert done.stdout == ""


def test_missing_target_ref_refuses(repo):
    done = _run(
        repo,
        "--upstream",
        UPSTREAM,
        "--target-branch",
        "nope",
        "--base",
        _git(repo, "rev-parse", "HEAD"),
    )
    assert done.returncode == 2 and "no refs/remotes/origin/nope" in done.stderr


def test_a_trusted_commit_without_the_driver_exits_four(repo):
    _git(repo, "rm", "-q", "--", DRIVER_PATH)
    _git(repo, "commit", "-q", "-m", "drop the driver")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    done = _run(repo)
    assert done.returncode == 4 and done.stdout == ""


@pytest.mark.parametrize(
    "bad",
    [
        ("--upstream", "not-a-repo", "--target-branch", "main"),
        ("--upstream", UPSTREAM, "--target-branch", "-x"),
        ("--upstream", UPSTREAM, "--target-branch", "a..b"),
        ("--upstream", UPSTREAM, "--target-branch", "a;touch${IFS}x"),
    ],
)
def test_malformed_arguments_exit_two_before_any_git_call(repo, bad):
    base = _git(repo, "rev-parse", "HEAD")
    assert _run(repo, *bad, "--base", base).returncode == 2


def test_a_short_base_is_refused(repo):
    done = _run(repo, "--upstream", UPSTREAM, "--target-branch", "main", "--base", "abc123")
    assert done.returncode == 2 and "full object id" in done.stderr


def test_missing_arguments_are_a_usage_error(repo):
    assert _run(repo, "--upstream", UPSTREAM).returncode == 2


def test_help_is_not_a_pass(repo):
    # A run that printed no verdict must never read as clean.
    done = _run(repo, "--help")
    assert done.returncode == 2


def test_abbreviated_options_are_refused(repo):
    base = _git(repo, "rev-parse", "HEAD")
    done = _run(repo, "--up", UPSTREAM, "--target-branch", "main", "--base", base)
    assert done.returncode == 2 and done.stdout == ""


def test_default_branch_ref_outside_origin_is_refused(repo):
    _git(repo, "update-ref", "refs/heads/elsewhere", "HEAD")
    _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/heads/elsewhere")
    done = _run(repo)
    assert done.returncode == 2 and done.stdout == ""


def test_outside_a_repository_refuses(tmp_path):
    done = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--upstream",
            UPSTREAM,
            "--target-branch",
            "main",
            "--base",
            "0" * 40,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 2 and done.stdout == ""


def test_git_environment_variables_do_not_redirect_the_checks(repo, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q", "-b", "main")
    done = _run(repo, env={"GIT_DIR": str(other / ".git")})
    assert done.returncode == 0, done.stderr


def _functions(path, names):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: ast.dump(node)
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    }


def test_the_git_lookup_helpers_match_the_drivers_copy():
    # The launcher cannot import them (the driver's copy in the tree is the untrusted one), so the
    # two copies are compared instead: a hardening fix to one has to land in both.
    names = {"_main_working_tree", "_repository_roots", "_is_inside", "_find_git"}
    mine, theirs = _functions(SCRIPT, names), _functions(DRIVER, names)
    assert set(mine) == set(theirs) == names
    assert mine == theirs


def _constants(path, names):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        target.id: ast.dump(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id in names
    }


def test_the_shared_constants_match_the_drivers_copy():
    # The patterns that validate arguments and origin, and the environment and git hardening the
    # git calls run under: a change to one copy alone would leave the gate weaker than its twin.
    names = {
        "_OBJECT_ID",
        "_REPO",
        "_UPSTREAM",
        "_BRANCH_NAME",
        "_ORIGIN_URL",
        "_KEEP_ENV",
        "_HARDENING",
        "_PINNED_ENV",
    }
    mine, theirs = _constants(SCRIPT, names), _constants(DRIVER, names)
    assert set(mine) == set(theirs) == names
    assert mine == theirs
