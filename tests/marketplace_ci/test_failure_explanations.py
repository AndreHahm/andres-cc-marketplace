"""Plain-language explanations for a could-not-run Codex review (issue #676)."""

from __future__ import annotations

import pytest

from scripts.marketplace_ci import review
from scripts.marketplace_ci.review import (
    FAILURE_CATALOGUE,
    SANDBOX_FAILURE_CODES,
    ReviewerReport,
    classify_failure,
    render_could_not_run,
)


def _failed(name: str, error: str, *, unsandboxed: bool = False) -> ReviewerReport:
    return ReviewerReport(
        reviewer=name, status="failed", error=error, attempts=1, unsandboxed=unsandboxed
    )


def _done(name: str) -> ReviewerReport:
    return ReviewerReport(reviewer=name, status="completed", output={})


@pytest.mark.parametrize("code", sorted(FAILURE_CATALOGUE))
def test_every_catalogue_entry_has_all_three_fields(code):
    entry = FAILURE_CATALOGUE[code]
    assert entry.summary.strip() and entry.cause.strip() and entry.action.strip()


def test_the_sandbox_codes_are_catalogued():
    assert SANDBOX_FAILURE_CODES <= set(FAILURE_CATALOGUE)
    assert "unknown" in FAILURE_CATALOGUE


@pytest.mark.parametrize(
    ("error", "code"),
    [
        ("reviewer returned an inconclusive review: setup refresh had errors",
         "sandbox_setup_refresh_failed"),
        ("helper_unknown_error: setup refresh had errors", "sandbox_setup_refresh_failed"),
        ('{"ok":false,"category":"isolation_profile_unavailable"}',
         "sandbox_setup_refresh_failed"),
        ("Codex sandbox probe failed (try 1 of 3: setup refresh); no reviewer was started",
         "sandbox_probe_failed"),
        ("unsandboxed run refused: a file the fallback runs changed",
         "fallback_refused_files_changed"),
        ('{"ok":false,"category":"guardrails_disabled"}', "fallback_guardrails_disabled"),
        ("bridge could not be run: node was not found on PATH outside the checkout",
         "codex_not_found"),
        ("bridge process killed after 600s (outlived its own timeout)", "bridge_timeout"),
        ('{"ok":false,"category":"timeout","detail":"x"}', "bridge_timeout"),
        ("dispatch budget exhausted before this reviewer could start (attempts so far: 0)",
         "budget_exhausted"),
        ("reviewer returned an inconclusive review: no inspection limit given",
         "inconclusive_review"),
        ("something nobody has seen before", "unknown"),
        (None, "unknown"),
        ("", "unknown"),
    ],
)  # fmt: skip
def test_classify_failure(error, code):
    assert classify_failure(error) == code


def test_a_probe_failure_that_quotes_the_raw_sandbox_wording_is_still_a_probe_failure():
    """The probe message carries the sandbox's own text; the specific message must win."""
    error = "Codex sandbox probe failed (try 1 of 3: helper_unknown_error); no reviewer was started"
    assert classify_failure(error) == "sandbox_probe_failed"


def test_every_code_classify_failure_returns_is_catalogued():
    for text in ("setup refresh", "probe failed", "x", "bridge process killed", "node not found"):
        assert classify_failure(text) in FAILURE_CATALOGUE


def test_render_groups_by_cause_not_by_reviewer_and_says_it_is_not_a_pass():
    reports = [
        _failed("a-reviewer", "reviewer returned an inconclusive review: setup refresh had errors"),
        _failed("b-reviewer", "helper_unknown_error: setup refresh had errors"),
        _failed("c-reviewer", "bridge process killed after 600s"),
        _done("d-reviewer"),
    ]
    text = render_could_not_run(reports)
    assert text.splitlines()[0] == "PARITY RESULT: could not run (exit 2 - this is NOT a pass)"
    assert text.count("What happened:") == 2  # sandbox (a, b) and timeout (c)
    assert "(2 of 4 reviewers: a-reviewer, b-reviewer)" in text
    assert "1 of 4 reviewers completed" in text
    assert "Nothing ran unsandboxed." in text
    assert "Raw detail: reviewer returned an inconclusive review: setup refresh had errors" in text


def test_render_says_no_code_was_reviewed_when_nothing_completed():
    text = render_could_not_run([_failed("a-reviewer", "setup refresh")])
    assert "no code was reviewed" in text


def test_render_says_when_something_ran_unsandboxed():
    text = render_could_not_run(
        [_failed("a-reviewer", "bridge process killed", unsandboxed=True), _done("b-reviewer")]
    )
    assert "ran unsandboxed (danger-full-access)" in text
    assert "Nothing ran unsandboxed." not in text


def test_render_states_why_there_was_no_fallback_for_sandbox_causes_only():
    note = "refused: this branch changes .codex/config.toml, which Codex reads"
    sandbox = render_could_not_run([_failed("a", "setup refresh")], fallback_note=note)
    assert f"Why no fallback: {note}" in sandbox
    other = render_could_not_run([_failed("a", "bridge process killed")], fallback_note=note)
    assert "Why no fallback" not in other


def test_render_prints_the_raw_text_for_an_unknown_cause():
    text = render_could_not_run([_failed("a", "weird new failure")])
    assert "does not classify" in text and "Raw detail: weird new failure" in text


def test_the_sandbox_wording_has_one_definition():
    """The wrapper must not grow a second copy: classify_failure and the empty-review check use
    the same compiled pattern."""
    assert classify_failure("os error 32") == "sandbox_setup_refresh_failed"
    assert review._SANDBOX_FAILURE_RE.search("os error 32")


def test_the_probe_failed_message_names_why_no_fallback_was_used(tmp_path):
    scope = review.ReviewScope(
        mode="delta",
        structural_check="delta",
        validate=("skill-reviewer",),
        audit=(),
        paths=("a.md",),
    )

    def errors(refusal: str | None) -> str:
        reports = review.dispatch_reviewers(
            scope,
            base_sha="0" * 40,
            repo=tmp_path / "repo",
            instructions_dir=tmp_path / "ins",
            sandbox_probe=lambda: "try 1 of 3: setup refresh",
            fallback_refusal=refusal,
        )
        return reports[0].error or ""

    assert "was not requested (--allow-unsandboxed-fallback)" in errors(None)
    refused = errors("this branch changes .codex/config.toml, which Codex reads")
    assert "the unsandboxed fallback was refused: this branch changes .codex/config.toml" in refused
    assert "pass --allow-unsandboxed-fallback" not in refused
