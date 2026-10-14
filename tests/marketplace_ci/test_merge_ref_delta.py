"""The delta `codex-review` runs on (issue #572, Phase 0 of #568).

The job checks out `refs/pull/<n>/merge` but used to diff against the event's
`base.sha`, the PR's fork point. `main` moves on after the fork, so that diff
held everything `main` gained since (128 files instead of 13 on PR #567). The
fix takes the merge commit's first parent as the base and refuses to run
unless the merge ref is shaped as expected.

The base is derived in a dedicated workflow step written in plain shell, not in
Python: the merge ref contains the PR's own `scripts/marketplace_ci`, so the
step that decides what to trust must run before any PR code. These tests
therefore execute the real step text from the workflow against fixture repos.

Fixtures build the real shape with git: fork point F, a PR commit P, an
upstream-only commit U on `main` (which also edits a Tier-1 file), and a merge
commit M = merge(U, P) checked out as HEAD.
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.marketplace_ci.review import compute_pr_delta

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "marketplace-ci.yml"
DERIVE_STEP = "Derive the delta base from the merge commit"
REFUSE_STEP = "Refuse automated Codex dispatch when this PR modifies review-dispatch-critical code"
RESULT_FILE = "codex-review-result.json"

PR_FILE = "plugins/p/pr.md"
UPSTREAM_FILE = "plugins/p/upstream.md"
TIER1_FILE = "pyproject.toml"


def _step_script(name_fragment: str) -> str:
    """The `run: |` script of the workflow step whose name contains the fragment."""
    lines = WORKFLOW.read_text(encoding="utf-8").split("\n")
    start = next(
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("- name:") and name_fragment in line
    )
    run = next(i for i in range(start, start + 12) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body: list[str] = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    return "\n".join(body)


def _run_step(name_fragment: str, root: Path, tmp_path: Path, **env: str):
    """Run a workflow step's script the way Actions does (`bash -eo pipefail`)."""
    github_output = tmp_path / "github_output"
    github_output.write_text("", encoding="utf-8")
    script = tmp_path / "step.sh"
    script.write_text(_step_script(name_fragment), encoding="utf-8")
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=root,
        env={**os.environ, "GITHUB_OUTPUT": str(github_output), **env},
        capture_output=True,
        text=True,
        check=False,
    )
    outputs = dict(
        line.split("=", 1) for line in github_output.read_text("utf-8").splitlines() if "=" in line
    )
    return result, outputs


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@dataclass(frozen=True)
class MergeRef:
    root: Path
    tmp: Path
    fork_point: str  # the event's base.sha: where the PR branched off
    upstream_tip: str  # main's tip when GitHub built the merge ref
    pr_head: str
    merge: str

    def derive(
        self,
        event_base: str | None = None,
        pr_head: str | None = None,
        base_ref: str = "main",
    ):
        return _run_step(
            DERIVE_STEP,
            self.root,
            self.tmp,
            EVENT_BASE_SHA=event_base or self.fork_point,
            EVENT_HEAD_SHA=pr_head or self.pr_head,
            BASE_REF=base_ref,
        )

    def delta_base(self) -> str:
        result, outputs = self.derive()
        assert result.returncode == 0, result.stderr
        return outputs["sha"]


@pytest.fixture
def merge_ref(git_repo, tmp_path) -> MergeRef:
    root = git_repo.root
    git_repo.write("plugins/p/a.md", "base\n")
    git_repo.write(TIER1_FILE, "[project]\nname = 'x'\n")
    fork_point = _commit(root, "fork point")
    _git(root, "branch", "-M", "main")

    _git(root, "checkout", "-q", "-b", "pr")
    git_repo.write(PR_FILE, "pr change\n")
    pr_head = _commit(root, "pr change")

    _git(root, "checkout", "-q", "main")
    git_repo.write(UPSTREAM_FILE, "someone else's change\n")
    git_repo.write(TIER1_FILE, "[project]\nname = 'x'\nversion = '2'\n")
    upstream_tip = _commit(root, "upstream-only change")

    _git(root, "checkout", "-q", "--detach", "main")
    _git(root, "merge", "-q", "--no-ff", "-m", "merge ref", "pr")
    merge = _git(root, "rev-parse", "HEAD")
    # What `actions/checkout` with fetch-depth 0 leaves behind for the base branch.
    _git(root, "update-ref", "refs/remotes/origin/main", upstream_tip)
    work = tmp_path / "work"
    work.mkdir()
    return MergeRef(root, work, fork_point, upstream_tip, pr_head, merge)


def _paths(delta) -> set[str]:
    return {p.new_path or p.old_path for p in delta}


def _refuses(merge_ref: MergeRef, base: str) -> subprocess.CompletedProcess:
    """Run the Tier-1 refusal step with `base` as its BASE_SHA."""
    work = merge_ref.tmp / "refuse"
    work.mkdir(exist_ok=True)
    result, _ = _run_step(REFUSE_STEP, merge_ref.root, work, BASE_SHA=base)
    return result


def test_the_event_base_delta_is_polluted_by_upstream_changes(merge_ref):
    """The defect, pinned: against the fork point the delta holds upstream's files too."""
    stale = _paths(compute_pr_delta(merge_ref.root, merge_ref.fork_point))
    assert {PR_FILE, UPSTREAM_FILE, TIER1_FILE} <= stale


def test_the_derived_base_is_the_merge_commits_first_parent(merge_ref):
    result, outputs = merge_ref.derive()
    assert result.returncode == 0, result.stderr
    assert outputs == {"sha": merge_ref.upstream_tip}


def test_the_delta_against_the_derived_base_holds_only_the_prs_files(merge_ref):
    assert _paths(compute_pr_delta(merge_ref.root, merge_ref.delta_base())) == {PR_FILE}


def test_tier1_refusal_fires_against_the_stale_event_base(merge_ref):
    """The defect on the refusal step: a Tier-1 file only `main` changed refuses the PR."""
    assert _refuses(merge_ref, merge_ref.fork_point).returncode == 1


def test_tier1_refusal_does_not_fire_for_upstream_only_changes(merge_ref):
    assert _refuses(merge_ref, merge_ref.delta_base()).returncode == 0


def test_tier1_refusal_still_fires_when_the_pr_itself_touches_a_tier1_file(git_repo, tmp_path):
    root = git_repo.root
    git_repo.write("plugins/p/a.md", "base\n")
    fork_point = _commit(root, "fork point")
    _git(root, "branch", "-M", "main")
    _git(root, "checkout", "-q", "-b", "pr")
    git_repo.write(TIER1_FILE, "[project]\nname = 'changed by the pr'\n")
    pr_head = _commit(root, "pr edits tier-1")
    _git(root, "checkout", "-q", "main")
    git_repo.write(UPSTREAM_FILE, "upstream\n")
    upstream = _commit(root, "upstream")
    _git(root, "checkout", "-q", "--detach", "main")
    _git(root, "merge", "-q", "--no-ff", "-m", "merge ref", "pr")
    work = tmp_path / "work"
    work.mkdir()
    _git(root, "update-ref", "refs/remotes/origin/main", upstream)
    ref = MergeRef(root, work, fork_point, upstream, pr_head, _git(root, "rev-parse", "HEAD"))
    assert _refuses(ref, ref.delta_base()).returncode == 1


def test_an_up_to_date_event_base_is_accepted(merge_ref):
    """When main has not moved, the event base is the first parent itself."""
    result, outputs = merge_ref.derive(event_base=merge_ref.upstream_tip)
    assert result.returncode == 0, result.stderr
    assert outputs == {"sha": merge_ref.upstream_tip}


def _assert_could_not_run(merge_ref: MergeRef, result, outputs, reason: str):
    assert result.returncode != 0
    assert outputs == {}  # no base is published, so no later step can use one
    assert reason in result.stderr + result.stdout
    # The artifact still says the review did not run, not that it found something.
    written = (merge_ref.root / RESULT_FILE).read_text(encoding="utf-8")
    assert '"status": "could_not_run"' in written
    assert '"blocking": true' in written


def test_a_head_with_one_parent_fails_closed(merge_ref):
    _git(merge_ref.root, "checkout", "-q", "--detach", merge_ref.pr_head)
    result, outputs = merge_ref.derive()
    _assert_could_not_run(merge_ref, result, outputs, "two parents")


def test_a_head_with_three_parents_fails_closed(merge_ref):
    root = merge_ref.root
    _git(root, "checkout", "-q", "-b", "other", merge_ref.fork_point)
    (root / "plugins/p/other.md").write_text("other\n", encoding="utf-8")
    _commit(root, "other")
    _git(root, "checkout", "-q", "--detach", merge_ref.upstream_tip)
    _git(root, "merge", "-q", "--no-ff", "-m", "octopus", "pr", "other")
    assert len(_git(root, "rev-list", "--parents", "-n1", "HEAD").split()) == 4
    result, outputs = merge_ref.derive()
    _assert_could_not_run(merge_ref, result, outputs, "two parents")


def test_an_event_base_that_is_not_an_ancestor_of_the_first_parent_fails_closed(merge_ref):
    """A merge ref built on some other base than the event claims is not this PR's delta."""
    result, outputs = merge_ref.derive(event_base=merge_ref.pr_head)
    _assert_could_not_run(merge_ref, result, outputs, "ancestor")


def test_an_unresolvable_event_base_fails_closed(merge_ref):
    result, outputs = merge_ref.derive(event_base="0" * 40)
    _assert_could_not_run(merge_ref, result, outputs, "resolve")


def test_the_second_parent_must_be_the_events_pr_head(merge_ref):
    """A merge ref that is not built from this event's PR head is not this PR's delta."""
    result, outputs = merge_ref.derive(pr_head=merge_ref.upstream_tip)
    _assert_could_not_run(merge_ref, result, outputs, "second parent")


def test_the_first_parent_must_be_on_the_base_branch(merge_ref):
    """The anchor is proven, not assumed: an author-made merge whose first parent is their
    own commit on top of base passes the parent-count and ancestor guards, but not this."""
    root = merge_ref.root
    _git(root, "checkout", "-q", "--detach", merge_ref.fork_point)
    (root / "plugins/p/evil.md").write_text(
        "controls the reviewer instructions\n", encoding="utf-8"
    )
    evil = _commit(root, "attacker commit on top of base")
    _git(root, "merge", "-q", "--no-ff", "-m", "author-made merge", merge_ref.pr_head)
    forged_head = _git(root, "rev-parse", "HEAD")
    assert _git(root, "rev-parse", "HEAD^1") == evil
    assert _git(root, "rev-parse", "HEAD^2") == merge_ref.pr_head
    assert forged_head != merge_ref.merge
    result, outputs = merge_ref.derive()
    _assert_could_not_run(merge_ref, result, outputs, "base branch")


def test_a_base_branch_that_moved_on_after_checkout_still_passes(merge_ref):
    root = merge_ref.root
    _git(root, "checkout", "-q", "main")
    (root / "plugins/p/later.md").write_text("merged after the checkout\n", encoding="utf-8")
    later = _commit(root, "main moves on")
    _git(root, "update-ref", "refs/remotes/origin/main", later)
    _git(root, "checkout", "-q", "--detach", merge_ref.merge)
    result, outputs = merge_ref.derive()
    assert result.returncode == 0, result.stderr
    assert outputs == {"sha": merge_ref.upstream_tip}


def test_a_missing_base_branch_ref_fails_closed(merge_ref):
    result, outputs = merge_ref.derive(base_ref="no-such-branch")
    _assert_could_not_run(merge_ref, result, outputs, "base branch")


def test_the_derive_step_runs_no_python_and_no_pr_code():
    """It decides what to trust, so it must not execute anything the PR can edit."""
    script = _step_script(DERIVE_STEP)
    assert not re.search(r"\b(uv|python3?|pip|node|npm)\b", script)
    assert "scripts/" not in script
