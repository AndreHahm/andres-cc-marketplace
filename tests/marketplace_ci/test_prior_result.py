"""Carrying a job's earlier result on a PR-description-only edit (issue #706).

`decide` is tested with a fake `gh`; the wiring in marketplace-ci.yml (which jobs carry, the step's
copies, the gating of every later step) can only be checked in the workflow text.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.marketplace_ci import prior_result

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "marketplace_ci" / "prior_result.py"
WORKFLOW = ROOT / ".github" / "workflows" / "marketplace-ci.yml"
JOBS = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]

REPO = "o/r"
RUN_ID = 500
PR = 7
HEAD = "a" * 40
JOB = "Python quality (ruff, ty, pytest)"
WORKFLOW_ID = 42


def _run(run_id, created, *, status="completed", head=HEAD, pr=PR, repo=REPO, event="pull_request"):
    return {
        "id": run_id,
        "created_at": created,
        "status": status,
        "head_sha": head,
        "event": event,
        "head_repository": {"full_name": repo},
        "pull_requests": [{"number": pr}] if pr is not None else [],
    }


def _steps(*, carried=False):
    """A carrying job's steps as the jobs API lists them: numbers jump at the post steps."""
    main = "skipped" if carried else "success"
    return [
        {"number": 1, "name": "Set up job", "conclusion": "success"},
        {"number": 4, "name": prior_result.CARRY_STEP_NAME, "conclusion": "success"},
        {"number": 6, "name": "Run actions/setup-python", "conclusion": main},
        {"number": 7, "name": "Run uv run pytest", "conclusion": main},
        {"number": 24, "name": "Post Run actions/checkout", "conclusion": "success"},
        {"number": 27, "name": "Complete job", "conclusion": "success"},
    ]


def _job(conclusion="success", *, carried=False, head=HEAD, steps=None):
    return {
        "name": JOB,
        "status": "completed",
        "conclusion": conclusion,
        "head_sha": head,
        "steps": _steps(carried=carried) if steps is None else steps,
    }


class FakeGh:
    """Answers the four reads `decide` makes; a value of None makes that read fail."""

    def __init__(self, *, runs=None, jobs=None, events=None, this_run=None, total=None):
        self.this_run = this_run or {
            "created_at": "2026-11-12T06:38:00Z",
            "workflow_id": WORKFLOW_ID,
            "head_sha": HEAD,
        }
        self.runs = runs if runs is not None else [_run(400, "2026-11-12T06:00:00Z")]
        self.total = total
        self.jobs = (
            jobs
            if jobs is not None
            else {
                400: [
                    {"name": JOB, "status": "completed", "conclusion": "success", "head_sha": HEAD}
                ]
            }
        )
        self.events = events if events is not None else ""
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, path, *fields):
        self.calls.append((path, *fields))
        if path == f"repos/{REPO}/actions/runs/{RUN_ID}":
            return None if self.this_run is None else json.dumps(self.this_run)
        if path == f"repos/{REPO}/actions/workflows/{WORKFLOW_ID}/runs":
            if self.runs is None:
                return None
            total = len(self.runs) if self.total is None else self.total
            return json.dumps({"total_count": total, "workflow_runs": self.runs})
        if path == f"repos/{REPO}/issues/{PR}/events":
            return self.events
        if path.startswith(f"repos/{REPO}/actions/runs/") and path.endswith("/jobs"):
            run_id = int(path.split("/")[-2])
            listed = self.jobs.get(run_id)
            if listed is None:
                return None
            # A job given without steps really ran (the fixtures that predate m-B2).
            listed = [j if "steps" in j else {**j, "steps": _steps()} for j in listed]
            return json.dumps({"total_count": len(listed), "jobs": listed})
        raise AssertionError(path)


def _decide(gh, **overrides):
    kwargs = {
        "repo": REPO,
        "run_id": RUN_ID,
        "pr_number": PR,
        "head_sha": HEAD,
        "job_name": JOB,
        "event_action": "edited",
        "base_change": "null",
    }
    kwargs.update(overrides)
    return prior_result.decide(gh, **kwargs)


def test_carries_a_success_from_the_newest_earlier_run():
    carry, reason = _decide(FakeGh())
    assert carry, reason
    assert "400" in reason


@pytest.mark.parametrize(
    "action", ["opened", "synchronize", "reopened", "labeled", "ready_for_review", ""]
)
def test_any_other_event_runs_in_full_without_an_api_call(action):
    gh = FakeGh()
    assert _decide(gh, event_action=action)[0] is False
    assert gh.calls == []


@pytest.mark.parametrize("change", ['{"ref":{"from":"main"}}', "", "{}", "garbage"])
def test_a_base_change_or_an_unreadable_change_runs_in_full(change):
    gh = FakeGh()
    assert _decide(gh, base_change=change)[0] is False
    assert gh.calls == []


@pytest.mark.parametrize(
    "conclusion", ["failure", "cancelled", "skipped", "timed_out", None, "neutral"]
)
def test_anything_but_a_success_of_the_job_runs_in_full(conclusion):
    gh = FakeGh(
        jobs={
            400: [{"name": JOB, "status": "completed", "conclusion": conclusion, "head_sha": HEAD}]
        }
    )
    assert _decide(gh)[0] is False


def test_a_job_still_running_in_the_earlier_run_runs_in_full():
    gh = FakeGh(
        jobs={400: [{"name": JOB, "status": "in_progress", "conclusion": None, "head_sha": HEAD}]}
    )
    assert _decide(gh)[0] is False


@pytest.mark.parametrize("status", ["in_progress", "queued", "requested", "waiting", "pending"])
def test_a_newest_earlier_run_that_is_not_complete_runs_in_full_even_after_an_older_success(status):
    runs = [_run(400, "2026-11-12T06:00:00Z"), _run(450, "2026-11-12T06:30:00Z", status=status)]
    gh = FakeGh(runs=runs)
    assert _decide(gh)[0] is False


def test_an_older_success_never_outlives_a_newer_failure():
    runs = [_run(400, "2026-11-12T06:00:00Z"), _run(450, "2026-11-12T06:30:00Z")]
    jobs = {
        400: [{"name": JOB, "status": "completed", "conclusion": "success", "head_sha": HEAD}],
        450: [{"name": JOB, "status": "completed", "conclusion": "failure", "head_sha": HEAD}],
    }
    assert _decide(FakeGh(runs=runs, jobs=jobs))[0] is False


def test_a_run_created_in_the_same_second_with_a_higher_id_is_not_earlier():
    # Security review m-B5: created_at has one-second resolution, so ordering also needs the id.
    runs = [_run(400, "2026-11-12T06:00:00Z"), _run(RUN_ID + 1, "2026-11-12T06:38:00Z")]
    jobs = {
        400: [{"name": JOB, "status": "completed", "conclusion": "success", "head_sha": HEAD}],
        RUN_ID + 1: [
            {"name": JOB, "status": "completed", "conclusion": "failure", "head_sha": HEAD}
        ],
    }
    carry, reason = _decide(FakeGh(runs=runs, jobs=jobs))
    assert carry, reason
    assert "400" in reason


def test_runs_created_after_this_one_and_this_run_itself_are_not_candidates():
    runs = [
        _run(RUN_ID, "2026-11-12T06:38:00Z"),
        _run(600, "2026-11-12T06:50:00Z", status="in_progress"),
        _run(400, "2026-11-12T06:00:00Z"),
    ]
    assert _decide(FakeGh(runs=runs))[0] is True


@pytest.mark.parametrize(
    "other",
    [
        {"pr": 8},
        {"pr": None},
        {"repo": "fork/r"},
        {"head": "b" * 40},
        {"event": "push"},
    ],
)
def test_runs_of_another_pr_repository_head_or_event_are_ignored(other):
    runs = [_run(400, "2026-11-12T06:00:00Z", **other)]
    assert _decide(FakeGh(runs=runs))[0] is False


def test_no_earlier_run_runs_in_full():
    assert _decide(FakeGh(runs=[]))[0] is False


def test_an_incomplete_run_listing_runs_in_full():
    assert _decide(FakeGh(total=101))[0] is False


@pytest.mark.parametrize(
    "event", ["base_ref_changed", "automatic_base_change_succeeded", "automatic_base_change_failed"]
)
def test_a_base_change_after_the_earlier_run_started_runs_in_full(event):
    gh = FakeGh(events=f"labeled\t2026-11-12T05:00:00Z\n{event}\t2026-11-12T06:10:00Z\n")
    assert _decide(gh)[0] is False


def test_a_base_change_before_the_earlier_run_still_carries():
    gh = FakeGh(events="base_ref_changed\t2026-11-12T05:59:00Z\nlabeled\t2026-11-12T06:20:00Z\n")
    assert _decide(gh)[0] is True


def test_unreadable_events_run_in_full():
    gh = FakeGh()
    gh.events = None
    assert _decide(gh)[0] is False
    gh.events = "base_ref_changed 2026-11-12T06:10:00Z\n"  # not tab-separated
    assert _decide(gh)[0] is False


@pytest.mark.parametrize(
    "this_run",
    [
        None,
        {"created_at": "2026-11-12T06:38:00Z", "workflow_id": WORKFLOW_ID, "head_sha": "b" * 40},
        {"created_at": "", "workflow_id": WORKFLOW_ID, "head_sha": HEAD},
        {"created_at": "2026-11-12T06:38:00Z", "workflow_id": "42", "head_sha": HEAD},
        {"created_at": "2026-11-12T06:38:00Z", "head_sha": HEAD},
    ],
)
def test_an_unreadable_or_mismatched_current_run_runs_in_full(this_run):
    gh = FakeGh()
    gh.this_run = this_run
    assert _decide(gh)[0] is False


def test_failed_listing_or_jobs_reads_run_in_full():
    gh = FakeGh()
    gh.runs = None
    assert _decide(gh)[0] is False
    assert _decide(FakeGh(jobs={}))[0] is False


@pytest.mark.parametrize("names", [[], ["Other job"], [JOB, JOB]])
def test_the_job_must_match_by_display_name_exactly_once(names):
    jobs = {
        400: [
            {"name": n, "status": "completed", "conclusion": "success", "head_sha": HEAD}
            for n in names
        ]
    }
    assert _decide(FakeGh(jobs=jobs))[0] is False


def test_a_job_on_another_head_runs_in_full():
    jobs = {
        400: [{"name": JOB, "status": "completed", "conclusion": "success", "head_sha": "b" * 40}]
    }
    assert _decide(FakeGh(jobs=jobs))[0] is False


def test_malformed_run_entries_run_in_full():
    assert _decide(FakeGh(runs=[{"id": 400}]))[0] is False
    assert _decide(FakeGh(runs=["x"]))[0] is False


def test_gh_api_retries_then_gives_up(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", "HTTP 502")

    monkeypatch.setattr(prior_result.subprocess, "run", fake_run)
    monkeypatch.setattr(prior_result.time, "sleep", lambda s: None)
    assert prior_result.gh_api("repos/o/r") is None
    assert len(calls) == len(prior_result.RETRY_DELAYS) + 1
    assert calls[0][:4] == ["gh", "api", "-X", "GET"]


def test_main_prints_run_and_exits_zero_on_any_fault(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("x")

    monkeypatch.setattr(prior_result, "decide", boom)
    args = ["--repo", REPO, "--run-id", "1", "--pr-number", "2", "--head-sha", HEAD,
            "--job-name", JOB, "--event-action", "edited", "--base-change", "null"]  # fmt: skip
    assert prior_result.main(args) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "run"


def test_the_script_runs_isolated_with_no_package_import(tmp_path):
    # The workflow runs the base SHA's copy as `python -I <file>` from outside the checkout.
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--repo", REPO, "--run-id", "1",
         "--pr-number", "2", "--head-sha", HEAD, "--job-name", JOB,
         "--event-action", "opened", "--base-change", "null"],
        capture_output=True, text=True, cwd=tmp_path,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "run"
    source = SCRIPT.read_text(encoding="utf-8")
    assert "from scripts" not in source and "from ." not in source


# --- workflow wiring ---------------------------------------------------------------------------

CARRY_STEP = "Carry this job's earlier result on a description-only edit"
GATE = "steps.carry_prior.outputs.carried != 'true'"
# Jobs that depend only on the PR head and base content.
CARRIED = (
    "python-quality",
    "review-helpers-windows",
    "node-tests",
    "marketplace-parity",
    "prefix-permanence",
)
# hygiene reads the PR title and body; compute-scope reads the live body's waivers (R7);
# codex-review acts on compute-scope's carried findings and has its own no-new-commit anchor;
# publish re-evaluates the policy.
NOT_CARRIED = ("hygiene", "compute-scope", "codex-review", "publish", "fork-unsupported")


def _carry_index(job):
    names = [s.get("name") for s in JOBS[job]["steps"]]
    assert names.count(CARRY_STEP) == 1, job
    return names.index(CARRY_STEP)


@pytest.mark.parametrize("job", CARRIED)
def test_each_commit_dependent_job_has_the_carry_step_and_gates_every_later_step(job):
    steps = JOBS[job]["steps"]
    i = _carry_index(job)
    step = steps[i]
    assert step["id"] == "carry_prior"
    assert step["if"] == "github.event.action == 'edited' && github.run_attempt == 1"
    assert step["continue-on-error"] is True
    assert step["env"]["JOB_NAME"] == JOBS[job]["name"]
    assert step["env"]["BASE_CHANGE"] == "${{ toJSON(github.event.changes.base) }}"
    assert step["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    later = steps[i + 1 :]
    assert later
    for s in later:
        assert GATE in s.get("if", ""), (job, s.get("name") or s.get("run") or s.get("uses"))
    for s in steps[:i]:
        assert "carry_prior" not in s.get("if", "")
    perms = JOBS[job]["permissions"]
    assert perms == {
        "contents": "read",
        "actions": "read",
        "issues": "read",
        "pull-requests": "read",
    }


def test_every_copy_of_the_carry_step_is_identical_but_for_the_job_name():
    copies = set()
    for job in CARRIED:
        step = dict(JOBS[job]["steps"][_carry_index(job)])
        step["env"] = {k: v for k, v in step["env"].items() if k != "JOB_NAME"}
        copies.add(json.dumps(step, sort_keys=True))
    assert len(copies) == 1


def test_the_carry_step_runs_the_base_shas_copy_isolated_and_only_trusts_a_carry_line():
    run = JOBS["python-quality"]["steps"][_carry_index("python-quality")]["run"]
    assert '"repos/$REPO/contents/scripts/marketplace_ci/prior_result.py" -f ref="$BASE_SHA"' in run
    assert 'script="$RUNNER_TEMP/prior_result.py"' in run
    assert '"$py" -I "$script"' in run
    assert 'if [ "$verdict" = carry ]; then' in run
    assert "carried=false" in run.split("\n")[0]


@pytest.mark.parametrize("job", NOT_CARRIED)
def test_the_jobs_that_read_the_pr_body_or_decide_policy_never_carry(job):
    assert CARRY_STEP not in [s.get("name") for s in JOBS[job]["steps"]]
    for s in JOBS[job]["steps"]:
        assert "carry_prior" not in str(s.get("if", "")), job


def test_a_chain_of_carries_dates_the_base_check_from_the_run_that_really_ran():
    # 300 really ran; 400 carried from it; a base change between 300 and 400 must still run (m-B2).
    gh = FakeGh(
        runs=[_run(300, "2026-11-12T05:00:00Z"), _run(400, "2026-11-12T06:00:00Z")],
        jobs={300: [_job()], 400: [_job(carried=True)]},
        events="automatic_base_change_succeeded\t2026-11-12T05:30:00Z\n",
    )
    carry, reason = _decide(gh)
    assert carry is False
    assert "300" in reason


def test_a_chain_of_carries_without_a_base_change_carries_and_names_both_runs():
    gh = FakeGh(
        runs=[_run(300, "2026-11-12T05:00:00Z"), _run(400, "2026-11-12T06:00:00Z")],
        jobs={300: [_job()], 400: [_job(carried=True)]},
    )
    carry, reason = _decide(gh)
    assert carry, reason
    assert "400" in reason and "300" in reason


def test_only_carries_and_no_run_that_really_ran_runs_in_full():
    gh = FakeGh(jobs={400: [_job(carried=True)]})
    assert _decide(gh)[0] is False


def test_a_failure_behind_a_carry_runs_in_full():
    gh = FakeGh(
        runs=[_run(300, "2026-11-12T05:00:00Z"), _run(400, "2026-11-12T06:00:00Z")],
        jobs={300: [_job("failure")], 400: [_job(carried=True)]},
    )
    assert _decide(gh)[0] is False


@pytest.mark.parametrize(
    "steps",
    [
        [],
        [{"number": 1, "name": "Set up job", "conclusion": "success"}],
        [{"number": 2, "name": prior_result.CARRY_STEP_NAME, "conclusion": "success"}],
        [
            {"number": 2, "name": prior_result.CARRY_STEP_NAME, "conclusion": "success"},
            {"number": 3, "name": "x", "conclusion": "cancelled"},
        ],
        [
            {"number": "2", "name": prior_result.CARRY_STEP_NAME},
            {"number": 3, "conclusion": "success"},
        ],
        [{"name": prior_result.CARRY_STEP_NAME}],
        "not a list",
    ],
)
def test_steps_that_cannot_tell_a_carry_from_a_run_run_in_full(steps):
    gh = FakeGh(jobs={400: [_job(steps=steps)]})
    assert _decide(gh)[0] is False


def test_the_carry_step_name_matches_every_carrying_job():
    for job_id, job in JOBS.items():
        names = [s.get("name") for s in job.get("steps", [])]
        ids = [s.get("id") for s in job.get("steps", [])]
        if "carry_prior" in ids:
            step = job["steps"][ids.index("carry_prior")]
            assert step["name"] == prior_result.CARRY_STEP_NAME, job_id
            assert names.count(prior_result.CARRY_STEP_NAME) == 1, job_id


def test_a_run_whose_carry_step_was_skipped_really_ran():
    # Not an edited event: the carry step is skipped and the job's steps ran.
    steps = _steps()
    steps[1] = {**steps[1], "conclusion": "skipped"}
    assert _decide(FakeGh(jobs={400: [_job(steps=steps)]}))[0] is True


@pytest.mark.parametrize("carry_conclusion", ["skipped", "failure", None])
def test_skipped_main_steps_without_a_successful_carry_step_run_in_full(carry_conclusion):
    steps = _steps(carried=True)
    steps[1] = {**steps[1], "conclusion": carry_conclusion}
    gh = FakeGh(
        runs=[_run(300, "2026-11-12T05:00:00Z"), _run(400, "2026-11-12T06:00:00Z")],
        jobs={300: [_job()], 400: [_job(steps=steps)]},
    )
    assert _decide(gh)[0] is False


def test_a_successful_post_step_does_not_make_a_carried_job_look_run():
    # Post and Complete job steps succeed in a carried job too; the main steps decide (m2).
    gh = FakeGh(
        runs=[_run(300, "2026-11-12T05:00:00Z"), _run(400, "2026-11-12T06:00:00Z")],
        jobs={300: [_job()], 400: [_job(carried=True)]},
        events="base_ref_changed\t2026-11-12T05:30:00Z\n",
    )
    assert _decide(gh)[0] is False
