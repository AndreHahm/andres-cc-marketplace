"""git-kit's dirty-worktree Stop guard must not report rebase- or squash-merged work as unmerged.

Issue #707: the guard compared SHAs (`git log origin/main..HEAD`), so a branch merged with
GitHub's rebase-merge or squash-merge, whose commits land on `main` under new SHAs, blocked
Stop with a false data-loss warning. Each test builds a throwaway origin, a clone, and a
session-locked worktree like the one `starting-work` creates. `gh` is a stub, so no network
is needed.
"""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/hooks/scripts/git-guard-dirty-worktree-exit.sh"
SYSTEM_PATH = os.environ.get("PATH", "/usr/bin:/bin")
BASH = shutil.which("bash") or "bash"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("timeout") is None,
    reason="the guard needs jq, and its PR fallback needs timeout",
)


def _env(home, extra=None):
    env = {
        "PATH": SYSTEM_PATH,
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    env.update(extra or {})
    return env


def _git(cwd, *args, home):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=_env(home)
    ).stdout.strip()


def _commit(cwd, name, text, home):
    (cwd / name).write_text(text, encoding="utf-8")
    _git(cwd, "add", "--", name, home=home)
    _git(cwd, "commit", "-m", f"add {name}", home=home)


def _run_guard(cwd, home, extra_env=None):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        cwd=cwd,
        input=json.dumps({"stop_hook_active": False}),
        capture_output=True,
        text=True,
        env=_env(home, extra_env),
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def setup(tmp_path):
    """Origin with one commit on main, a clone, and a locked worktree on branch feat."""
    home = tmp_path
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin), home=home)
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", str(origin), str(clone), home=home)
    _commit(clone, "base.txt", "base\n", home)
    _git(clone, "push", "origin", "HEAD:main", home=home)
    _git(clone, "remote", "set-head", "origin", "main", home=home)
    wt = tmp_path / "wt"
    _git(clone, "worktree", "add", "-b", "feat", str(wt), home=home)
    _git(clone, "worktree", "lock", str(wt), "--reason", "claude session", home=home)
    return home, clone, wt


def _land_on_main(clone, home, *, squash):
    """Land feat's changes on origin/main under new SHAs, after an unrelated main commit."""
    _git(clone, "checkout", "-q", "main", home=home)
    _commit(clone, "other.txt", "other\n", home)
    if squash:
        _git(clone, "merge", "--squash", "feat", home=home)
        _git(clone, "commit", "-m", "squashed feat", home=home)
    else:
        _git(clone, "cherry-pick", "main..feat", home=home)
    _git(clone, "push", "origin", "HEAD:main", home=home)
    _git(clone, "fetch", "origin", home=home)


ORIGIN_URL = "https://github.com/acme/widgets.git"


def _stub_gh(tmp_path, pr):
    """A gh stub that runs the guard's own --jq expression over a PR JSON fixture."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fixture = tmp_path / "pr.json"
    fixture.write_text(json.dumps(pr), encoding="utf-8")
    log = tmp_path / "gh-env.txt"
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f'printf "GH_REPO=%s\\n" "${{GH_REPO:-}}" > "{log}"\n'
        'while [ "$#" -gt 0 ]; do [ "$1" = "--jq" ] && expr="$2"; shift; done\n'
        f'exec jq -r "$expr" "{fixture}"\n',
        encoding="utf-8",
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return {"PATH": f"{bin_dir}:{SYSTEM_PATH}"}, log


def _pr(state, head, base="main", url="https://github.com/acme/widgets/pull/7"):
    return {"state": state, "baseRefName": base, "headRefOid": head, "url": url}


def _point_origin_at_github(wt, home):
    # The guard never fetches, so origin can name a GitHub URL once refs are in place.
    _git(wt, "remote", "set-url", "origin", ORIGIN_URL, home=home)


def _squash_merged(setup):
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _commit(wt, "b.txt", "b\n", home)
    _land_on_main(clone, home, squash=True)
    _point_origin_at_github(wt, home)
    return home, wt, _git(wt, "rev-parse", "HEAD", home=home)


def test_rebase_merged_branch_does_not_block(setup):
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _commit(wt, "b.txt", "b\n", home)
    _land_on_main(clone, home, squash=False)
    assert _run_guard(wt, home) == ""


def test_genuinely_unmerged_branch_blocks(setup):
    home, _clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "fetch", "origin", home=home)
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"
    assert "commits not yet in main" in out


def test_dirty_worktree_blocks_even_when_merged(setup):
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _land_on_main(clone, home, squash=False)
    (wt / "scratch.txt").write_text("wip\n", encoding="utf-8")
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"
    assert "uncommitted changes" in out


def test_squash_merge_without_gh_keeps_warning(setup):
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _commit(wt, "b.txt", "b\n", home)
    _land_on_main(clone, home, squash=True)
    # No gh on PATH: the PR fallback cannot run, so the guard fails toward warning.
    empty_bin = home / "empty-bin"
    empty_bin.mkdir()
    for tool in ("git", "jq", "timeout", "env", "sed", "awk", "grep", "tr", "tail", "cat"):
        found = shutil.which(tool)
        if found:
            (empty_bin / tool).symlink_to(found)
    out = _run_guard(wt, home, {"PATH": str(empty_bin)})
    assert json.loads(out)["decision"] == "block"


def test_squash_merge_with_merged_pr_at_head_does_not_block(setup, tmp_path):
    home, wt, head = _squash_merged(setup)
    env, log = _stub_gh(tmp_path, _pr("MERGED", head))
    env["GH_REPO"] = "someone/else"
    assert _run_guard(wt, home, env) == ""
    assert log.read_text(encoding="utf-8").strip() == "GH_REPO="


@pytest.mark.parametrize(
    "pr",
    [
        pytest.param(_pr("MERGED", "0" * 40), id="different-head"),
        pytest.param(_pr("OPEN", "HEAD"), id="open"),
        pytest.param(_pr("MERGED", "HEAD", base="feature-a"), id="stacked-base"),
        pytest.param(
            _pr("MERGED", "HEAD", url="https://github.com/upstream/widgets/pull/7"),
            id="other-repository",
        ),
        pytest.param(_pr("MERGED", None), id="null-head"),
    ],
)
def test_squash_merge_without_a_matching_merged_pr_keeps_warning(setup, tmp_path, pr):
    home, wt, head = _squash_merged(setup)
    if pr["headRefOid"] == "HEAD":
        pr = pr | {"headRefOid": head}
    env, _log = _stub_gh(tmp_path, pr)
    out = _run_guard(wt, home, env)
    assert json.loads(out)["decision"] == "block"


def test_merge_commit_in_range_keeps_warning_without_pr(setup):
    # git cherry skips merge commits, so a merge whose resolution is the only
    # unlanded change must still be reported.
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _land_on_main(clone, home, squash=False)
    _git(wt, "merge", "--no-ff", "-m", "merge main", "origin/main", home=home)
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"


# A pushed-but-unmerged branch: its commits are safe on origin, so removing the
# worktree loses nothing. Only an upstream under refs/remotes/origin/ counts.


def test_branch_pushed_to_origin_does_not_block(setup):
    home, _clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "push", "-u", "origin", "feat", home=home)
    assert _run_guard(wt, home) == ""


def test_commit_after_push_blocks(setup):
    home, _clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "push", "-u", "origin", "feat", home=home)
    _commit(wt, "b.txt", "b\n", home)
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"
    assert "commits not yet in main" in out


def test_dirty_pushed_branch_blocks(setup):
    home, _clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "push", "-u", "origin", "feat", home=home)
    (wt / "scratch.txt").write_text("wip\n", encoding="utf-8")
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"
    assert "uncommitted changes" in out


def test_upstream_on_another_remote_blocks(setup, tmp_path):
    home, _clone, wt = setup
    fork = tmp_path / "fork.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(fork), home=home)
    _git(wt, "remote", "add", "fork", str(fork), home=home)
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "push", "-u", "fork", "feat", home=home)
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"


def test_local_branch_upstream_blocks(setup):
    home, _clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "branch", "backup", "HEAD", home=home)
    _git(wt, "branch", "--set-upstream-to=backup", home=home)
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"


def test_fork_mapped_into_origin_namespace_blocks(setup, tmp_path):
    # A fork whose fetch refspec writes into refs/remotes/origin/ must not pass as origin.
    home, _clone, wt = setup
    fork = tmp_path / "fork.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(fork), home=home)
    _git(wt, "remote", "add", "fork", str(fork), home=home)
    _git(wt, "config", "remote.fork.fetch", "+refs/heads/*:refs/remotes/origin/*", home=home)
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "push", "fork", "feat", home=home)
    _git(wt, "fetch", "fork", home=home)
    _git(wt, "config", "branch.feat.remote", "fork", home=home)
    _git(wt, "config", "branch.feat.merge", "refs/heads/feat", home=home)
    assert (
        _git(wt, "rev-parse", "--symbolic-full-name", "@{upstream}", home=home)
        == "refs/remotes/origin/feat"
    )
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"


def test_slashed_remote_name_under_origin_blocks(setup, tmp_path):
    # A remote named origin/fork lands in refs/remotes/origin/fork/* by default.
    home, _clone, wt = setup
    fork = tmp_path / "fork.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(fork), home=home)
    _git(wt, "remote", "add", "origin/fork", str(fork), home=home)
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "push", "-u", "origin/fork", "feat", home=home)
    assert (
        _git(wt, "rev-parse", "--symbolic-full-name", "@{upstream}", home=home)
        == "refs/remotes/origin/fork/feat"
    )
    out = _run_guard(wt, home)
    assert json.loads(out)["decision"] == "block"


# Every history check is bounded by one shared budget inside the hook's 10s
# limit; a check that times out, or cannot be bounded, keeps the warning.


def _bin_without_timeout(home):
    empty_bin = home / "no-timeout-bin"
    empty_bin.mkdir()
    for tool in ("git", "jq", "env", "sed", "awk", "grep", "tr", "tail", "cat"):
        found = shutil.which(tool)
        if found:
            (empty_bin / tool).symlink_to(found)
    return {"PATH": str(empty_bin)}


def _bin_with_failing_timeout_for(home, word):
    """A timeout wrapper that reports a timeout (124) when its command line contains word."""
    bin_dir = home / "timeout-bin"
    bin_dir.mkdir()
    real = shutil.which("timeout")
    stub = bin_dir / "timeout"
    stub.write_text(
        f'#!/bin/sh\ncase " $* " in *" {word} "*) exit 124 ;; esac\nexec "{real}" "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return {"PATH": f"{bin_dir}:{SYSTEM_PATH}"}


def test_timed_out_merge_scan_keeps_warning(setup):
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _land_on_main(clone, home, squash=False)
    out = _run_guard(wt, home, _bin_with_failing_timeout_for(home, "rev-list"))
    assert json.loads(out)["decision"] == "block"


def test_exhausted_budget_keeps_warning(setup):
    # git cherry succeeds but uses up the shared budget, so the merge scan is
    # refused without running and the rebase-merged branch still warns.
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _land_on_main(clone, home, squash=False)
    bin_dir = home / "slow-timeout-bin"
    bin_dir.mkdir()
    real = shutil.which("timeout")
    stub = bin_dir / "timeout"
    stub.write_text(
        f'#!/bin/sh\ncase " $* " in *" cherry "*) sleep 5 ;; esac\nexec "{real}" "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    out = _run_guard(wt, home, {"PATH": f"{bin_dir}:{SYSTEM_PATH}"})
    assert json.loads(out)["decision"] == "block"
    # The transcript parse has its own cap, so the override still works on an
    # exhausted budget.
    transcript = home / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": " Exit anyway "}})
        + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        cwd=wt,
        input=json.dumps({"stop_hook_active": False, "transcript_path": str(transcript)}),
        capture_output=True,
        text=True,
        env=_env(home, {"PATH": f"{bin_dir}:{SYSTEM_PATH}"}),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_no_timeout_falls_back_to_range_check(setup):
    # Without timeout the patch comparison cannot be bounded, so a rebase-merged
    # branch is reported by plain SHA range, as before issue #707.
    home, clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _land_on_main(clone, home, squash=False)
    out = _run_guard(wt, home, _bin_without_timeout(home))
    assert json.loads(out)["decision"] == "block"


def test_no_timeout_pushed_branch_keeps_warning(setup):
    home, _clone, wt = setup
    _commit(wt, "a.txt", "a\n", home)
    _git(wt, "push", "-u", "origin", "feat", home=home)
    out = _run_guard(wt, home, _bin_without_timeout(home))
    assert json.loads(out)["decision"] == "block"


def test_no_timeout_branch_with_nothing_new_does_not_block(setup):
    # HEAD already on origin/main: the range is empty, so there is nothing to protect.
    home, _clone, wt = setup
    _git(wt, "fetch", "origin", home=home)
    assert _run_guard(wt, home, _bin_without_timeout(home)) == ""
