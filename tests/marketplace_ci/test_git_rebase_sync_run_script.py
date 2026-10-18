"""git-kit's git-rebase-sync-run.sh runs the skill's rebase and push in one fixed shape each (#585).

A `Bash(git rebase origin/:*)` or `Bash(git push --force-with-lease=:*)` tool grant also admits
anything appended after the documented text (`--exec`, `--onto`, another remote, a `+` refspec).
The script is what the skill's grant names instead. These tests run it against a throwaway origin
and clone: the accepted shapes do what the skill documents, and every other argument list exits 2
without touching git.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-rebase-sync-run.sh"
SYSTEM_PATH = os.environ.get("PATH", "/usr/bin:/bin")


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _run(cwd, *args):
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
    return subprocess.run(
        ["bash", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True, env=env
    )


def _commit(repo, name, text):
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", "--", name)
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.invalid",
        "commit",
        "-m",
        f"add {name}",
    )


@pytest.fixture
def clone(tmp_path):
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", str(origin), str(work))
    _commit(work, "base.txt", "base\n")
    _git(work, "push", "origin", "main")
    _git(work, "checkout", "-b", "feature")
    _commit(work, "feature.txt", "feature\n")
    _git(work, "push", "origin", "feature")
    _git(work, "checkout", "main")
    _commit(work, "main2.txt", "main2\n")
    _git(work, "push", "origin", "main")
    _git(work, "checkout", "feature")
    _git(work, "fetch", "origin")
    return work


def test_rebase_replays_the_branch_onto_the_base(clone):
    result = _run(clone, "rebase", "main")
    assert result.returncode == 0, result.stderr
    assert _git(clone, "merge-base", "HEAD", "origin/main") == _git(
        clone, "rev-parse", "origin/main"
    )


def test_rebase_merges_mode_runs(clone):
    assert _run(clone, "rebase-merges", "main").returncode == 0


def test_push_with_the_recorded_lease_updates_the_remote_branch(clone):
    lease = _git(clone, "rev-parse", "origin/feature")
    assert _run(clone, "rebase", "main").returncode == 0
    result = _run(clone, "push", "feature", lease)
    assert result.returncode == 0, result.stderr
    assert _git(clone, "rev-parse", "origin/feature") == _git(clone, "rev-parse", "HEAD")


def test_push_refuses_when_the_remote_moved_past_the_lease(clone, tmp_path):
    lease = _git(clone, "rev-parse", "origin/feature")
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-b", "feature", str(tmp_path / "origin.git"), str(other))
    _commit(other, "other.txt", "other\n")
    _git(other, "push", "origin", "feature")
    assert _run(clone, "rebase", "main").returncode == 0
    result = _run(clone, "push", "feature", lease)
    assert result.returncode != 0
    assert _git(tmp_path / "origin.git", "log", "-1", "--format=%s", "feature") == "add other.txt"


def test_push_refuses_a_base_branch_even_with_a_matching_lease(clone):
    lease = _git(clone, "rev-parse", "origin/main")
    _git(clone, "checkout", "-q", "main")
    assert _run(clone, "push", "main", lease).returncode == 2
    assert _run(clone, "push-plain", "main").returncode == 2


def test_push_refuses_when_head_is_not_the_named_branch(clone):
    lease = _git(clone, "rev-parse", "origin/feature")
    _git(clone, "checkout", "-q", "-b", "other")
    assert _run(clone, "push", "feature", lease).returncode == 2
    _git(clone, "checkout", "-q", "--detach")
    assert _run(clone, "push", "feature", lease).returncode == 2


def test_push_refuses_while_a_rebase_is_in_progress(clone):
    _git(clone, "checkout", "-q", "main")
    _commit(clone, "base.txt", "main edit\n")
    _git(clone, "push", "origin", "main")
    _git(clone, "checkout", "-q", "feature")
    _commit(clone, "base.txt", "feature edit\n")
    lease = _git(clone, "rev-parse", "origin/feature")
    assert _run(clone, "rebase", "main").returncode != 0
    assert (clone / ".git" / "rebase-merge").exists() or (clone / ".git" / "rebase-apply").exists()
    assert _run(clone, "push", "feature", lease).returncode == 2


def test_rebase_ignores_a_tag_named_like_the_remote_tracking_ref(clone):
    _git(clone, "update-ref", "refs/tags/origin/main", "HEAD")
    assert _run(clone, "rebase", "main").returncode == 0
    assert _git(clone, "merge-base", "HEAD", "refs/remotes/origin/main") == _git(
        clone, "rev-parse", "refs/remotes/origin/main"
    )


def test_push_plain_mode_runs(clone):
    assert _run(clone, "rebase", "main").returncode == 0
    assert _run(clone, "push-plain", "feature").returncode == 0


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("rebase",),
        ("rebase", "main", "--exec", "touch PWNED"),
        ("rebase", "main", "-x", "touch PWNED"),
        ("rebase", "--onto", "main"),
        ("rebase", "-main"),
        ("rebase", "main; touch PWNED"),
        ("rebase", "$(touch PWNED)"),
        ("rebase", "a..b"),
        ("rebase", "HEAD"),
        ("rebase", "topic/"),
        ("rebase", "topic.lock"),
        ("rebase", ""),
        ("push", "feature"),
        ("push", "feature", "nothex"),
        ("push", "feature", "a" * 40, "--force"),
        ("push", "+feature", "a" * 40),
        ("push", "feature:other", "a" * 40),
        ("push-plain",),
        ("push-plain", "feature", "extra"),
        ("push-plain", "-f"),
        ("amend", "main"),
    ],
)
def test_every_other_argument_list_is_refused_without_running_git(clone, args):
    result = _run(clone, *args)
    assert result.returncode == 2, result.stderr
    assert not (clone / "PWNED").exists()
    assert _git(clone, "rev-parse", "HEAD") == _git(clone, "rev-parse", "feature")
