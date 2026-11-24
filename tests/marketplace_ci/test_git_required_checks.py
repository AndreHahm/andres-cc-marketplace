"""git-kit's git-required-checks.py (#858): same-name required checks are told apart by data the
server sets, and anything that cannot be read stops the merge."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-required-checks.py"
SHA = "b2" * 20
ACTIONS, CODACY = 15368, 56611


def _load():
    spec = importlib.util.spec_from_file_location("git_required_checks", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()


def check(ident, name="ci", conclusion="success", suite=1, app=ACTIONS, status=None):
    return {
        "id": ident,
        "name": name,
        "status": status or "completed",
        "conclusion": None if status else conclusion,
        "app_id": app,
        "app_slug": "github-actions" if app == ACTIONS else "other-app",
        "suite": suite,
    }


def status(ident, state="success", creator=7, login="codacy[bot]", kind="Bot", at="01"):
    return {
        "id": ident,
        "context": "ci",
        "state": state,
        "created_at": f"2026-01-01T00:00:{at}Z",
        "creator_id": creator,
        "creator_login": login,
        "creator_type": kind,
    }


def run(
    ident,
    workflow=100,
    event="pull_request",
    suite=1,
    sha=SHA,
    status="completed",
    attempt=1,
    conclusion="success",
):
    return {
        "id": ident,
        "workflow_id": workflow,
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": attempt,
        "suite": suite,
        "head_sha": sha,
    }


class Gh:
    """Answers `gh api` by path; a path in `fail` exits 1."""

    def __init__(
        self, checks=(), statuses=(), runs=(), jobs=None, protect=None, rules=(), fail="", suites=3
    ):
        self.protect = {"required_status_checks": {"checks": [{"context": "ci", "app_id": None}]}}
        if protect is not None:
            self.protect = protect
        self.lines = {
            "/check-suites": [{"n": suites}],
            "/check-runs": checks,
            "/statuses": statuses,
            "/actions/runs?": runs,
            "/rules/branches/": rules,
        }
        self.jobs, self.fail, self.argvs = jobs or {}, fail, []

    def __call__(self, argv, **kwargs):
        assert isinstance(argv, list) and not kwargs.get("shell") and kwargs["timeout"] > 0
        assert argv[:6] == ["gh", "api", "--hostname", "github.com", "-X", "GET"]
        self.argvs.append(argv)
        path = argv[6]
        if self.fail and self.fail in path:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")
        assert ("--paginate" in argv) == (
            "/check-suites" not in path and not path.endswith("/protection")
        )
        if path.endswith("/protection"):
            code = 1 if "message" in self.protect else 0
            return subprocess.CompletedProcess(argv, code, stdout=json.dumps(self.protect))
        if "/jobs?" in path:
            assert "filter=all" in path
            rows = self.jobs.get(int(path.split("/runs/")[1].split("/")[0]), [])
        elif path.startswith("apps/"):
            rows = [{"id": CODACY}]
        else:
            rows = next(v for k, v in self.lines.items() if k in path)
        return subprocess.CompletedProcess(argv, 0, stdout="\n".join(map(json.dumps, rows)))


def jobs(*ids, attempt=1):
    return [{"id": i, "run_id": 0, "run_attempt": attempt} for i in ids]


def state(monkeypatch, **kwargs):
    gh = Gh(**kwargs)
    monkeypatch.setattr(M.subprocess, "run", gh)
    result = M.evaluate("o/r", "main", SHA)
    assert result["all_passing"] == all(c["state"] == "passing" for c in result["contexts"])
    return {c["name"]: c["state"] for c in result["contexts"]}["ci"]


def need(app):
    return {"required_status_checks": {"checks": [{"context": "ci", "app_id": app}]}}


def test_a_second_workflow_cannot_mask_a_failing_one(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, conclusion="failure"), check(2, suite=2)],
        runs=[run(10), run(20, workflow=200, suite=2)],
        jobs={10: jobs(1), 20: jobs(2)},
    )
    assert got == "failing"


def test_a_token_created_check_in_the_real_suite_cannot_mask_a_failing_job(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, conclusion="failure"), check(2)],
        runs=[run(10)],
        jobs={10: jobs(1)},
    )
    assert got == "failing"


def test_a_later_run_of_the_same_workflow_replaces_the_earlier_one(monkeypatch):
    checks = [check(1, conclusion="cancelled"), check(2, suite=2)]
    both = {"runs": [run(10), run(20, suite=2)], "jobs": {10: jobs(1), 20: jobs(2)}}
    assert state(monkeypatch, checks=checks, **both) == "passing"
    checks[1]["conclusion"] = "failure"
    checks[0]["conclusion"] = "success"
    assert state(monkeypatch, checks=checks, **both) == "failing"


def test_a_rerun_attempt_replaces_the_earlier_attempt(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, conclusion="failure"), check(2)],
        runs=[run(10, attempt=2)],
        jobs={10: jobs(1) + jobs(2, attempt=2)},
    )
    assert got == "passing"


def test_a_skipped_run_under_another_event_hides_nothing(monkeypatch):
    got = state(
        monkeypatch,
        checks=[
            check(1, conclusion="failure"),
            check(2, conclusion="skipped", suite=2),
        ],
        runs=[run(10), run(20, event="push", suite=2)],
        jobs={10: jobs(1), 20: jobs(2)},
    )
    assert got == "failing"


def test_two_same_name_jobs_of_one_run_must_both_pass(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, conclusion="failure"), check(2)],
        runs=[run(10)],
        jobs={10: jobs(1, 2)},
    )
    assert got == "failing"


def test_a_run_of_another_head_is_not_used(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, conclusion="failure"), check(2)],
        runs=[run(10), run(11, sha="c3" * 20)],
        jobs={10: jobs(1), 11: jobs(2)},
    )
    assert got == "failing"


def test_an_unfinished_job_keeps_the_context_pending(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, status="in_progress"), check(2, suite=2)],
        runs=[run(10), run(20, suite=2)],
        jobs={10: jobs(1), 20: jobs(2)},
    )
    assert got == "pending"


def test_an_app_entry_its_next_one_replaced_does_not_stay_pending(monkeypatch):
    checks = [check(1, app=CODACY, status="in_progress"), check(2, app=CODACY)]
    assert state(monkeypatch, checks=checks) == "passing"
    checks = [check(1, app=CODACY), check(2, app=CODACY, status="in_progress")]
    assert state(monkeypatch, checks=checks) == "pending"


def test_an_apps_skip_does_not_replace_its_earlier_result(monkeypatch):
    failed = check(1, app=CODACY, conclusion="failure")
    skip = check(9, app=CODACY, conclusion="skipped")
    assert state(monkeypatch, checks=[failed, skip]) == "failing"
    assert state(monkeypatch, checks=[check(1, app=CODACY), skip]) == "passing"
    assert state(monkeypatch, checks=[skip]) == "passing"
    # A finished result between the failure and the skip has already replaced the failure.
    assert state(monkeypatch, checks=[failed, check(2, app=CODACY), skip]) == "passing"
    # An unfinished entry was replaced (it may never complete), so it neither counts nor blocks.
    stale = check(2, app=CODACY, status="in_progress")
    assert state(monkeypatch, checks=[failed, stale, skip]) == "failing"
    assert state(monkeypatch, checks=[stale, skip]) == "passing"


def test_a_check_run_without_an_app_is_undetermined(monkeypatch):
    with pytest.raises(M.Undetermined):
        state(monkeypatch, checks=[check(1, app=None, conclusion="failure"), check(2, app=None)])


def test_only_the_named_app_counts(monkeypatch):
    wrong = [check(1, app=99)]
    assert state(monkeypatch, checks=wrong, protect=need(CODACY)) == "missing"
    assert state(monkeypatch, checks=wrong, protect=need(99)) == "passing"
    assert state(monkeypatch, checks=wrong, protect=need(-1)) == "passing"
    both = [check(1, app=CODACY, conclusion="failure"), check(2, app=99)]
    assert state(monkeypatch, checks=both, protect=need(CODACY)) == "failing"


def test_a_ruleset_app_is_required_too(monkeypatch):
    rules = [{"context": "ci", "app_id": CODACY}]
    assert state(monkeypatch, checks=[check(1, app=99)], rules=rules) == "missing"


def test_a_commit_status_counts_for_the_app_that_created_it(monkeypatch):
    assert state(monkeypatch, statuses=[status(1)], protect=need(CODACY)) == "passing"
    person = [status(1, login="codacy", kind="User")]
    assert state(monkeypatch, statuses=person, protect=need(CODACY)) == "missing"


def test_commit_statuses_are_grouped_by_creator(monkeypatch):
    other = [status(1, "failure"), status(2, creator=8, login="x", kind="User", at="09")]
    assert state(monkeypatch, statuses=other) == "failing"
    same = [status(2, at="09"), status(1, "pending")]
    assert state(monkeypatch, statuses=same) == "passing"
    assert state(monkeypatch, statuses=[status(1, "pending")]) == "pending"


def test_no_entry_is_missing(monkeypatch):
    assert state(monkeypatch) == "missing"


def test_an_unprotected_branch_counts_only_rulesets(monkeypatch):
    bare = {"message": "Branch not protected", "status": "404"}
    rules = [{"context": "ci", "app_id": None}]
    assert state(monkeypatch, checks=[check(1, app=9)], protect=bare, rules=rules) == "passing"
    with pytest.raises(M.Undetermined):
        state(monkeypatch, protect=bare)
    with pytest.raises(M.Undetermined):
        state(monkeypatch, protect={"message": "Not Found", "status": "404"}, rules=rules)


@pytest.mark.parametrize(
    "path",
    [
        "/protection",
        "/rules/branches/",
        "/check-runs",
        "/statuses",
        "/actions/runs?",
        "/jobs?",
        "/check-suites",
    ],
)
def test_any_failed_request_exits_2_and_prints_no_result(monkeypatch, capsys, path):
    gh = Gh(checks=[check(1)], runs=[run(10)], jobs={10: jobs(1)}, fail=path)
    if path == "/protection":
        gh.protect = {"message": "Must have admin rights", "status": "403"}
        gh.fail = ""
    monkeypatch.setattr(M.subprocess, "run", gh)
    assert M.main(["o/r", "main", SHA]) == 2
    assert capsys.readouterr().out == ""


def test_exit_codes_and_branch_quoting(monkeypatch, capsys):
    gh = Gh(checks=[check(1)], runs=[run(10)], jobs={10: jobs(1)})
    monkeypatch.setattr(M.subprocess, "run", gh)
    assert M.main(["o/r", "release/1.0", SHA]) == 0
    assert json.loads(capsys.readouterr().out)["all_passing"] is True
    assert gh.argvs[0][6] == "repos/o/r/branches/release%2F1.0/protection"
    monkeypatch.setattr(M.subprocess, "run", Gh())
    assert M.main(["o/r", "main", SHA]) == 1


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["o/r", "main"],
        ["o/r/x", "main", SHA],
        ["{owner}/{repo}", "main", SHA],
        ["o/..", "main", SHA],
        ["o/.", "main", SHA],
        ["o/r", "..", SHA],
        ["o/r", "a/../b", SHA],
        ["o/r", "a b", SHA],
        ["o/r", "main", "HEAD"],
    ],
)
def test_bad_arguments_make_no_request(monkeypatch, argv):
    gh = Gh()
    monkeypatch.setattr(M.subprocess, "run", gh)
    assert M.main(argv) == 2
    assert gh.argvs == []


GROWN = {"runs": [run(10), run(20, suite=2)], "jobs": {10: jobs(1), 20: jobs(2)}}


def test_an_unfinished_newer_run_without_the_job_is_pending(monkeypatch):
    runs = [run(10), run(20, suite=2, status="queued")]
    assert state(monkeypatch, checks=[check(1)], runs=runs, jobs={10: jobs(1)}) == "pending"


def test_a_finished_newer_run_without_the_job_is_missing(monkeypatch):
    runs = [run(10), run(20, suite=2)]
    assert state(monkeypatch, checks=[check(1)], runs=runs, jobs={10: jobs(1)}) == "missing"


def test_rerunning_an_old_run_does_not_replace_a_newer_failure(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1), check(2, conclusion="failure", suite=2), check(3)],
        runs=[run(10, attempt=2), run(20, suite=2)],
        jobs={10: jobs(1) + jobs(3, attempt=2), 20: jobs(2)},
    )
    assert got == "failing"


def test_a_later_skip_does_not_replace_a_failure(monkeypatch):
    checks = [check(1, conclusion="failure"), check(2, conclusion="skipped", suite=2)]
    assert state(monkeypatch, checks=checks, **GROWN) == "failing"
    checks[0]["conclusion"] = "success"
    assert state(monkeypatch, checks=checks, **GROWN) == "passing"
    checks[0]["conclusion"] = "skipped"
    assert state(monkeypatch, checks=checks, **GROWN) == "passing"


def test_a_partial_rerun_keeps_the_other_same_name_job(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, conclusion="failure"), check(2), check(3)],
        runs=[run(10, attempt=2)],
        jobs={10: jobs(1, 2) + jobs(3, attempt=2)},
    )
    assert got == "failing"


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (["failure", "skipped"], ["success"], "failing"),
        (["failure", "success"], ["skipped", "success"], "failing"),
        (["failure", "skipped"], ["success", "skipped"], "failing"),
        (["failure", "skipped"], ["skipped", "success"], "failing"),
        (["failure", "failure"], ["success", "success"], "passing"),
        (["failure", "success"], ["success"], "failing"),
        (["failure"], ["skipped"], "failing"),
        (["failure"], ["success", "skipped"], "failing"),
    ],
)
def test_a_skipped_same_name_job_does_not_hide_a_partial_rerun(
    monkeypatch, first, second, expected
):
    conclusions = first + second
    checks = [check(i, conclusion=c) for i, c in enumerate(conclusions, 1)]
    split = len(first) + 1
    found = jobs(*range(1, split)) + jobs(*range(split, len(conclusions) + 1), attempt=2)
    got = state(monkeypatch, checks=checks, runs=[run(10, attempt=2)], jobs={10: found})
    assert got == expected


def test_exclusive_same_name_jobs_do_not_replace_each_other_across_runs(monkeypatch):
    got = state(
        monkeypatch,
        checks=[
            check(1, conclusion="failure"),
            check(2, conclusion="skipped"),
            check(3, conclusion="skipped", suite=2),
            check(4, suite=2),
        ],
        runs=[run(10), run(20, suite=2)],
        jobs={10: jobs(1, 2), 20: jobs(3, 4)},
    )
    assert got == "failing"


def test_a_job_carried_into_a_failed_rerun_still_passes(monkeypatch):
    # GitHub lists a job that a partial re-run did not touch again, with a new id (seen live).
    got = state(
        monkeypatch,
        checks=[check(1), check(2)],
        runs=[run(10, attempt=2, conclusion="failure")],
        jobs={10: jobs(1) + jobs(2, attempt=2)},
    )
    assert got == "passing"


def test_only_token_made_entries_are_missing(monkeypatch):
    assert state(monkeypatch, checks=[check(2)], runs=[run(10)], jobs={10: []}) == "missing"
    token = [status(1, login="github-actions[bot]")]
    assert state(monkeypatch, statuses=token) == "missing"


def test_a_token_status_never_replaces_a_failure(monkeypatch):
    posted = [status(1, "failure", login="github-actions[bot]"), status(2, at="09")]
    posted[1]["creator_login"] = "github-actions[bot]"
    got = state(monkeypatch, checks=[check(1)], statuses=posted, runs=[run(10)], jobs={10: jobs(1)})
    assert got == "failing"


def test_any_app_and_a_named_app_are_both_required(monkeypatch):
    rules = [{"context": "ci", "app_id": CODACY}]
    checks = [check(1, app=CODACY), check(2, app=99, conclusion="failure")]
    assert state(monkeypatch, checks=checks, rules=rules) == "failing"


def test_too_many_check_suites_is_undetermined(monkeypatch):
    with pytest.raises(M.Undetermined):
        state(monkeypatch, checks=[check(1)], runs=[run(10)], jobs={10: jobs(1)}, suites=1000)


def test_a_finished_job_counts_while_the_rest_of_its_run_is_unfinished(monkeypatch):
    runs = [run(10, status="in_progress", conclusion=None)]
    assert state(monkeypatch, checks=[check(1)], runs=runs, jobs={10: jobs(1)}) == "passing"


def test_an_old_run_stuck_waiting_does_not_block(monkeypatch):
    runs = [run(10, status="waiting", conclusion=None), run(20, suite=2)]
    got = state(monkeypatch, checks=[check(2, suite=2)], runs=runs, jobs={20: jobs(2)})
    assert got == "passing"


@pytest.mark.parametrize(
    ("status_", "conclusion", "expected"),
    [
        ("in_progress", None, "pending"),
        ("completed", "cancelled", "missing"),
        ("completed", "success", "passing"),
    ],
)
def test_an_attempt_without_the_job(monkeypatch, status_, conclusion, expected):
    runs = [run(10, attempt=2, status=status_, conclusion=conclusion)]
    assert state(monkeypatch, checks=[check(1)], runs=runs, jobs={10: jobs(1)}) == expected


def test_a_skip_does_not_bring_back_a_failure_already_replaced(monkeypatch):
    checks = [
        check(1, conclusion="cancelled"),
        check(2, suite=2),
        check(3, conclusion="skipped", suite=3),
    ]
    runs = [run(10), run(20, suite=2), run(30, suite=3)]
    found = {10: jobs(1), 20: jobs(2), 30: jobs(3)}
    assert state(monkeypatch, checks=checks, runs=runs, jobs=found) == "passing"


def test_a_stray_token_status_does_not_block_another_apps_result(monkeypatch):
    posted = [status(1, login="github-actions[bot]")]
    assert state(monkeypatch, checks=[check(1, app=CODACY)], statuses=posted) == "passing"
    posted[0]["state"] = "failure"
    assert state(monkeypatch, checks=[check(1, app=CODACY)], statuses=posted) == "failing"


def test_a_skipped_attempt_does_not_hide_an_earlier_attempts_failure(monkeypatch):
    got = state(
        monkeypatch,
        checks=[check(1, conclusion="failure"), check(2, conclusion="skipped")],
        runs=[run(10, attempt=2)],
        jobs={10: jobs(1) + jobs(2, attempt=2)},
    )
    assert got == "failing"
