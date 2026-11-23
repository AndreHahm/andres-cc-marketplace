"""Carry a job's earlier result on a PR-description-only edit (issue #706).

A `pull_request` `edited` event that does not retarget the base changes neither the PR head nor
its base, so a job that depends only on that content would compute the same result again. A job
skipped by `if:` counts as passing for a required check, so skipping it could turn a failure on
the same head green. Instead, each such job runs this file first and ends successfully without
running its real steps only when the same job SUCCEEDED in the newest earlier run of this
workflow for this PR and head. When that job was itself carried, the same must hold back through
the chain of carries, and the base-change check is dated from the run that really ran the job.
Anything else, including any API error or data it cannot read, prints `run` and the job runs in
full.

The workflow fetches this file from the base SHA through the Contents API and runs it as
`python -I <file>`, so it must stay a single standard-library-only file: no import from this
package, no third-party module. Its verdict is the last stdout line: `carry` or `run`. The reason
goes to stderr. The exit code is 0 for both verdicts; the caller treats anything but a `carry`
line with exit 0 as `run`.

Known limitation (docs/ci.md, "Carried results on a description edit"): a `pull_request` run
tests the merge ref, so a carried result was computed against the base as it was for the earlier
run. That matches what already happens when the base branch moves without a new PR event.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime

# The same short retry as the review-anchor lookup (review.py's _GH_RETRY_DELAYS, Codex R5).
RETRY_DELAYS = (1, 3)

# Issue events that mean the base branch changed. The failed automatic change is included too:
# it costs one full run at most and needs no reasoning about what it left behind.
BASE_CHANGE_EVENTS = frozenset(
    {"base_ref_changed", "automatic_base_change_succeeded", "automatic_base_change_failed"}
)

# The display name of the carry step in each carrying job of marketplace-ci.yml. A job whose step
# right after this one was skipped was itself carried, not run (issue #706 review, m-B2).
CARRY_STEP_NAME = "Carry this job's earlier result on a description-only edit"

Gh = Callable[..., "str | None"]


def gh_api(*args: str) -> str | None:
    """`gh api -X GET <args>`'s stdout, retried after each delay in RETRY_DELAYS; None when every
    attempt failed."""
    for delay in (*RETRY_DELAYS, None):
        try:
            result = subprocess.run(
                ["gh", "api", "-X", "GET", *args], capture_output=True, text=True, encoding="utf-8"
            )
        except OSError:
            return None
        if result.returncode == 0:
            return result.stdout
        if delay is not None:
            time.sleep(delay)
    return None


def _json(gh: Gh, path: str, *fields: str):
    out = gh(path, *fields)
    if out is None:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def _epoch(stamp: object) -> float:
    if not isinstance(stamp, str) or not stamp:
        raise ValueError(stamp)
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def decide(
    gh: Gh,
    *,
    repo: str,
    run_id: int,
    pr_number: int,
    head_sha: str,
    job_name: str,
    event_action: str,
    base_change: str,
) -> tuple[bool, str]:
    """(True, reason) when `job_name` may carry its earlier success, else (False, reason).

    `base_change` is `toJSON(github.event.changes.base)`: the literal `null` when the edit did not
    retarget the base."""
    if event_action != "edited":
        return False, f"event action {event_action!r} is not 'edited'"
    if base_change.strip() != "null":
        return False, "this edit changed the base branch"
    if not job_name:
        return False, "no job name given"

    run = _json(gh, f"repos/{repo}/actions/runs/{run_id}")
    try:
        created = _epoch(run["created_at"])  # type: ignore[index]
        workflow_id = run["workflow_id"]  # type: ignore[index]
        run_head = run["head_sha"]  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        return False, "cannot read this run"
    if not isinstance(workflow_id, int) or isinstance(workflow_id, bool):
        return False, "cannot read this run's workflow"
    if run_head != head_sha:
        return False, "this run's head is not the event's PR head"

    listing = _json(
        gh,
        f"repos/{repo}/actions/workflows/{workflow_id}/runs",
        "-f", f"head_sha={head_sha}", "-f", "event=pull_request", "-F", "per_page=100",
    )  # fmt: skip
    try:
        runs = listing["workflow_runs"]  # type: ignore[index]
        total = listing["total_count"]  # type: ignore[index]
        if not isinstance(runs, list) or not isinstance(total, int) or total > len(runs):
            return False, "the run listing is incomplete"
        candidates = []
        for r in runs:
            if r["id"] == run_id or r.get("head_sha") != head_sha:
                continue
            if r.get("event") != "pull_request":
                continue
            if (r.get("head_repository") or {}).get("full_name") != repo:
                continue
            if not any(p.get("number") == pr_number for p in r.get("pull_requests") or []):
                continue
            r_created = _epoch(r["created_at"])
            if r_created <= created and r["id"] < run_id:
                candidates.append((r_created, r["id"], r))
    except (TypeError, KeyError, ValueError, AttributeError):
        return False, "cannot read the run listing"
    if not candidates:
        return False, "no earlier run of this workflow for this PR and head"
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    prior_id = candidates[0][1]

    # Only the newest earlier run counts: an older success never outlives a newer failure,
    # cancellation, or a run still in progress. When that run's job was itself carried, walk back
    # through the carries to the run that really ran the job, and date the base-change check from
    # that run, not from the carry (m-B2).
    anchor = None
    for r_created, r_id, r in candidates:
        verdict = _job_verdict(
            gh, repo=repo, run=r, run_id=r_id, head_sha=head_sha, job_name=job_name
        )
        if verdict == "ran":
            anchor = (r_created, r_id)
            break
        if verdict != "carried":
            return False, verdict
    if anchor is None:
        return False, "no earlier run for this PR and head really ran this job"
    anchor_created, anchor_id = anchor

    events = gh(
        f"repos/{repo}/issues/{pr_number}/events", "-F", "per_page=100", "--paginate",
        "--jq", ".[] | [.event, .created_at] | @tsv",
    )  # fmt: skip
    if events is None:
        return False, "cannot read the PR's events"
    try:
        for line in events.splitlines():
            if not line.strip():
                continue
            name, stamp = line.split("\t")
            if name in BASE_CHANGE_EVENTS and _epoch(stamp) >= anchor_created:
                return False, f"the base branch changed after run {anchor_id} started"
    except ValueError:
        return False, "cannot read the PR's events"

    if anchor_id == prior_id:
        return True, f"carried from run {prior_id}, where this job succeeded on the same head"
    return True, (
        f"carried from run {prior_id}, which carried it from run {anchor_id}, where this job"
        " succeeded on the same head"
    )


def _job_verdict(gh: Gh, *, repo: str, run: dict, run_id: int, head_sha: str, job_name: str) -> str:
    """`ran` or `carried` when `job_name` succeeded on `head_sha` in this completed run; otherwise
    the reason it cannot be carried."""
    if run.get("status") != "completed":
        return f"the earlier run {run_id} is not completed"
    # The latest attempt's jobs (the endpoint's default filter).
    jobs = _json(gh, f"repos/{repo}/actions/runs/{run_id}/jobs", "-F", "per_page=100")
    try:
        listed = jobs["jobs"]  # type: ignore[index]
        if not isinstance(listed, list) or jobs["total_count"] > len(listed):  # type: ignore[index]
            return f"the job listing of run {run_id} is incomplete"
        matches = [j for j in listed if j.get("name") == job_name]
    except (TypeError, KeyError, AttributeError):
        return f"cannot read the jobs of run {run_id}"
    if len(matches) != 1:
        return f"run {run_id} has {len(matches)} jobs named {job_name!r}"
    job = matches[0]
    if job.get("head_sha") != head_sha:
        return f"the job in run {run_id} ran on another head"
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        return (
            f"the job in run {run_id} ended {job.get('status')}/{job.get('conclusion')}, not"
            " completed/success"
        )
    # Step numbers are not contiguous (post steps jump ahead), so the decision uses the order of the
    # job's own main steps after the carry step, never "carry step number + 1".
    unknown = f"cannot tell whether the job in run {run_id} was carried"
    try:
        steps = sorted(job["steps"], key=lambda s: s["number"])
        if any(not isinstance(s["number"], int) or isinstance(s["number"], bool) for s in steps):
            return unknown
        carry = [s for s in steps if s.get("name") == CARRY_STEP_NAME]
        if len(carry) != 1:
            return unknown
        later = [
            s
            for s in steps
            if s["number"] > carry[0]["number"]
            and not str(s.get("name", "")).startswith("Post ")
            and s.get("name") != "Complete job"
        ]
        carry_conclusion = carry[0].get("conclusion")
        conclusions = [s.get("conclusion") for s in later]
    except (TypeError, KeyError, AttributeError):
        return unknown
    if not later:
        return unknown
    if carry_conclusion == "success" and all(c == "skipped" for c in conclusions):
        return "carried"
    if carry_conclusion in ("success", "skipped") and conclusions[0] == "success":
        return "ran"
    return unknown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--event-action", required=True)
    parser.add_argument("--base-change", required=True)
    args = parser.parse_args(argv)
    try:
        carry, reason = decide(
            gh_api,
            repo=args.repo,
            run_id=args.run_id,
            pr_number=args.pr_number,
            head_sha=args.head_sha,
            job_name=args.job_name,
            event_action=args.event_action,
            base_change=args.base_change,
        )
    except Exception as exc:  # noqa: BLE001 - any fault runs the job in full
        carry, reason = False, f"lookup failed: {type(exc).__name__}"
    print(reason, file=sys.stderr)
    print("carry" if carry else "run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
