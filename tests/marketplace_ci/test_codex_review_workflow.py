"""Wiring of the `codex-review` job in marketplace-ci.yml (issue #572).

The behaviour of the derive step is tested by running its script
(test_merge_ref_delta.py); the wiring below can only be checked in the
workflow text: which step feeds which, and what the publish step says per
status.
"""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "marketplace-ci.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")

DERIVE_NAME = "Derive the delta base from the merge commit"
REFUSE_NAME = "Refuse automated Codex dispatch when this PR modifies review-dispatch-critical code"
DISPATCH_NAME = "Dispatch reviewers directly, validate output, aggregate findings"
PUBLISH_NAME = "Determine final policy result"


def _job(job_id: str) -> str:
    pattern = rf"^  {re.escape(job_id)}:\n(?P<body>.*?)(?=^  [a-z][\w-]*:\n|\Z)"
    match = re.search(pattern, TEXT, re.M | re.S)
    assert match, job_id
    return match.group("body")


def _step(job_body: str, name_fragment: str) -> str:
    steps = re.split(r"^      - ", job_body, flags=re.M)
    matches = [s for s in steps if re.match(rf"name: .*{re.escape(name_fragment)}", s)]
    assert len(matches) == 1, (name_fragment, len(matches))
    return matches[0]


def test_the_derive_step_has_an_id_and_runs_before_the_refusal_and_dispatch_steps():
    job = _job("codex-review")
    derive = _step(job, DERIVE_NAME)
    assert re.search(r"^\s+id: delta_base$", derive, re.M)
    assert job.index(DERIVE_NAME) < job.index(REFUSE_NAME) < job.index(DISPATCH_NAME)


def test_the_derive_step_reads_the_event_base_only_as_a_guard_input():
    derive = _step(_job("codex-review"), DERIVE_NAME)
    assert "EVENT_BASE_SHA: ${{ github.event.pull_request.base.sha }}" in derive
    assert "$GITHUB_OUTPUT" in derive


def test_the_refusal_and_dispatch_steps_take_their_base_from_the_derived_output():
    job = _job("codex-review")
    for name in (REFUSE_NAME, DISPATCH_NAME):
        step = _step(job, name)
        assert "BASE_SHA: ${{ steps.delta_base.outputs.sha }}" in step, name
        assert "github.event.pull_request.base.sha" not in step, name


def test_no_step_after_the_derive_step_diffs_the_merge_ref_against_the_event_base():
    """The defect: `$BASE_SHA...HEAD` with BASE_SHA taken from the event, run on the merge ref."""
    job = _job("codex-review")
    after = job[job.index(DERIVE_NAME) :]
    steps = re.split(r"^      - ", after, flags=re.M)
    diffing = [step for step in steps if re.search(r'"\$BASE_SHA"\.\.\.?HEAD', step)]
    assert diffing  # the Tier-1 refusal step, at least
    for step in diffing:
        assert "BASE_SHA: ${{ steps.delta_base.outputs.sha }}" in step, step[:80]


def test_the_codex_review_job_publishes_the_result_status_as_an_output():
    job = _job("codex-review")
    assert re.search(r"^    outputs:\n(?:      .*\n)*?      review_status: ", job, re.M)
    assert "codex-review-result.json" in job and "status" in job


def test_the_publish_step_names_each_status_in_its_own_message():
    step = _step(_job("publish"), PUBLISH_NAME)
    assert "needs.codex-review.outputs.review_status" in _job("publish")
    for status in ("findings", "clean", "could_not_run"):
        assert re.search(rf'REVIEW_STATUS" = "{status}"', step), status
    messages = set()
    for status in ("findings", "clean", "could_not_run"):
        found = re.search(rf'REVIEW_STATUS" = "{status}"[^\n]*\n\s*echo "([^"]+)"', step)
        assert found, status
        messages.add(found.group(1))
    assert len(messages) == 3  # three different messages


def test_the_timeout_comes_from_the_repository_variable_with_a_fallback():
    step = _step(_job("codex-review"), DISPATCH_NAME)
    assert (
        "CODEX_KIT_REVIEW_TIMEOUT_MS: ${{ vars.CODEX_KIT_REVIEW_TIMEOUT_MS || '600000' }}" in step
    )


def test_the_findings_message_does_not_claim_every_blocker_is_on_a_changed_line():
    """Structural findings, and Critical/Major findings when the changed lines could not be
    computed, also fail the job with status `findings`."""
    step = _step(_job("publish"), PUBLISH_NAME)
    found = re.search(r'REVIEW_STATUS" = "findings"[^\n]*\n\s*echo "([^"]+)"', step)
    assert found
    message = found.group(1)
    assert "changed line" not in message
    assert "codex-review-result" in message  # points at the artifact instead
