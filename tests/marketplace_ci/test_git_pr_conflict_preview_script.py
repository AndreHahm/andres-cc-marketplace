"""git-kit's git-pr-conflict-preview.sh runs the read-only previews of a remote-only PR conflict.

A `Bash(gh pr view:*)` or `Bash(git merge-tree ...:*)` tool grant also admits other repositories,
`--web`, other refs and other options. The script is what the skills' grants name instead. `gh` is
a stub that records its arguments, so these tests need no network; `merge-tree` runs against a
throwaway origin and clone.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-pr-conflict-preview.sh"
SYSTEM_PATH = os.environ.get("PATH", "/usr/bin:/bin")
FIELDS = "mergeable,mergeStateStatus,baseRefName,headRefName,headRefOid,isCrossRepository,url"


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _run(cwd, *args, extra_env=None):
    env = {
        "PATH": SYSTEM_PATH,
        "HOME": str(cwd),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True, env=env
    )


def _commit(repo, name, text):
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", "--", name)
    _git(repo, "commit", "-m", f"add {name}")


@pytest.fixture
def stub_gh(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh-args.txt"
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$@" > "$GH_ARGS_LOG"\n'
        'printf "repo=%s\\n" "${GH_REPO:-}" >> "$GH_ARGS_LOG"\n'
        'printf "host=%s\\n" "${GH_HOST:-}" >> "$GH_ARGS_LOG"\n',
        encoding="utf-8",
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return {"PATH": f"{bin_dir}:{SYSTEM_PATH}", "GH_ARGS_LOG": str(log)}, log


def test_view_runs_exactly_one_fixed_gh_pr_view(tmp_path, stub_gh):
    env, log = stub_gh
    result = _run(tmp_path, "view", "579", extra_env=env)
    assert result.returncode == 0, result.stderr
    assert log.read_text(encoding="utf-8").splitlines()[:5] == [
        "pr",
        "view",
        "579",
        "--json",
        FIELDS,
    ]


def test_view_does_not_honor_a_redirecting_environment_variable(tmp_path, stub_gh):
    env, log = stub_gh
    env["GH_REPO"] = "attacker/elsewhere"
    env["GH_HOST"] = "evil.example.invalid"
    assert _run(tmp_path, "view", "579", extra_env=env).returncode == 0
    lines = log.read_text(encoding="utf-8").splitlines()
    assert lines[-2:] == ["repo=", "host="]


def test_default_branch_runs_exactly_one_fixed_gh_repo_view(tmp_path, stub_gh):
    env, log = stub_gh
    result = _run(tmp_path, "default-branch", extra_env=env)
    assert result.returncode == 0, result.stderr
    assert log.read_text(encoding="utf-8").splitlines()[:5] == [
        "repo",
        "view",
        "--json",
        "defaultBranchRef",
        "--jq",
    ]


@pytest.fixture
def clone(tmp_path):
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", str(origin), str(work))
    _commit(work, "shared.txt", "base\n")
    _git(work, "push", "origin", "main")
    _git(work, "checkout", "-b", "feature")
    _commit(work, "shared.txt", "feature\n")
    _git(work, "checkout", "main")
    _commit(work, "shared.txt", "main\n")
    _git(work, "push", "origin", "main")
    _git(work, "checkout", "feature")
    _git(work, "fetch", "origin")
    return work


def test_merge_tree_names_the_conflicted_file_and_exits_1(clone):
    result = _run(clone, "merge-tree", "main")
    assert result.returncode == 1
    assert "shared.txt" in result.stdout


def test_merge_tree_does_not_touch_the_worktree_or_index(clone):
    before = _git(clone, "status", "--porcelain=v1")
    _run(clone, "merge-tree", "main")
    assert _git(clone, "status", "--porcelain=v1") == before == ""


def test_merge_tree_ignores_a_tag_named_like_the_remote_tracking_ref(clone):
    _git(clone, "update-ref", "refs/tags/origin/main", "HEAD")
    assert _run(clone, "merge-tree", "main").returncode == 1


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("view",),
        ("view", "579", "--web"),
        ("view", "579", "--repo", "other/repo"),
        ("view", "--web"),
        ("view", "579; touch PWNED"),
        ("view", "$(touch PWNED)"),
        ("view", "0x10"),
        ("view", ""),
        ("view", "1234567890"),
        ("merge-tree",),
        ("merge-tree", "main", "extra"),
        ("merge-tree", "-z"),
        ("merge-tree", "a..b"),
        ("merge-tree", "HEAD"),
        ("merge-tree", "main; touch PWNED"),
        ("merge-tree", "topic.lock"),
        ("show", "579"),
        ("default-branch", "x"),
        ("default-branch", "--web"),
    ],
)
def test_every_other_argument_list_is_refused_without_running_anything(tmp_path, stub_gh, args):
    env, log = stub_gh
    result = _run(tmp_path, *args, extra_env=env)
    assert result.returncode == 2, result.stderr
    assert not log.exists()
    assert not (tmp_path / "PWNED").exists()
