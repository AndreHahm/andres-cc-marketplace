"""Tests for scripts/validate_report.py -- common contract checks (coverage
preamble, next-step line, evidence metadata) and component/actor disposition
completeness via inventory/disposition HTML-comment markers.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import validate_report  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "reports"
CONTRACTS = validate_report.load_contracts()


def _fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_component_valid_fixture_passes():
    result = validate_report.validate(
        "analyzing-plugin-components", _fixture("component-valid.md"), CONTRACTS
    )
    assert result["valid"] is True
    assert result["errors"] == []


def test_component_fixture_with_duplicate_disposition_fails():
    result = validate_report.validate(
        "analyzing-plugin-components", _fixture("component-missing-reflection.md"), CONTRACTS
    )
    assert result["valid"] is False
    codes = {e["code"] for e in result["errors"]}
    assert "duplicate_disposition" in codes
    dup = next(e for e in result["errors"] if e["code"] == "duplicate_disposition")
    assert dup["subject"] == "component:commit"


def test_actor_fixture_with_missing_assessment_fails():
    result = validate_report.validate(
        "analyzing-actor-behavior", _fixture("actor-missing-assessment.md"), CONTRACTS
    )
    assert result["valid"] is False
    codes = {e["code"] for e in result["errors"]}
    assert "missing_disposition" in codes
    missing = next(e for e in result["errors"] if e["code"] == "missing_disposition")
    assert missing["subject"] == "actor:plugin-validator"


def test_repeated_identical_inventory_identifier_requires_matching_dispositions():
    # Two same-type sub-agent dispatches sharing one identifier: inventory has
    # it twice, disposition only once -- must fail, not silently pass via a
    # set-based dedup that collapses both inventory occurrences into one.
    text = (
        "<!-- inventory: actor:general-purpose -->\n"
        "<!-- inventory: actor:general-purpose -->\n"
        "<!-- disposition: actor:general-purpose assessed -->\n"
    )
    errors = validate_report.check_dispositions(text, "actor")
    assert errors == [
        {
            "code": "missing_disposition",
            "message": (
                "2 inventory occurrence(s) of actor:general-purpose but only 1 disposition(s) found"
            ),
            "subject": "actor:general-purpose",
        }
    ]


def test_repeated_identical_inventory_identifier_with_matching_dispositions_passes():
    text = (
        "<!-- inventory: actor:general-purpose -->\n"
        "<!-- inventory: actor:general-purpose -->\n"
        "<!-- disposition: actor:general-purpose grouped:fanout -->\n"
        "<!-- disposition: actor:general-purpose grouped:fanout -->\n"
    )
    assert validate_report.check_dispositions(text, "actor") == []


def test_orphaned_disposition_with_no_matching_inventory_marker_fails():
    text = "<!-- disposition: component:not-in-inventory assessed -->\n"
    errors = validate_report.check_dispositions(text, "component")
    assert errors == [
        {
            "code": "orphaned_disposition",
            "message": (
                "Disposition found for component:not-in-inventory but no matching "
                "inventory marker exists"
            ),
            "subject": "component:not-in-inventory",
        }
    ]


def test_common_fixture_with_missing_next_step_fails():
    result = validate_report.validate(
        "analyzing-plugin-components", _fixture("common-missing-next-step.md"), CONTRACTS
    )
    assert result["valid"] is False
    codes = {e["code"] for e in result["errors"]}
    assert codes == {"missing_next_step"}


def test_missing_coverage_preamble_fields_flagged():
    text = "# Report\n\nNo preamble here.\n\nEvidence origin: direct\n"
    errors = validate_report.check_common(text, CONTRACTS)
    codes = {e["code"] for e in errors}
    assert codes == {"missing_coverage"}
    assert len(errors) == len(CONTRACTS["common"]["coverage_fields"])


def test_blank_coverage_preamble_fields_flagged_as_missing_coverage():
    text = (
        "**Requested scope:**\n**Inspected scope:**\n**Unavailable evidence:**\n**Limitations:**\n"
    )
    errors = validate_report.check_common(text, CONTRACTS)
    assert len(errors) == len(CONTRACTS["common"]["coverage_fields"])
    assert all(e["code"] == "missing_coverage" for e in errors)
    assert all("has no value" in e["message"] for e in errors)


def test_coverage_field_mentioned_in_prose_is_not_mistaken_for_the_real_field():
    # Codex/CodeRabbit finding: an unanchored substring search would treat a
    # mid-sentence mention of the label as if it were the actual field.
    text = "This report discusses Requested scope: informally, not as the real field.\n"
    errors = validate_report.check_common(text, CONTRACTS)
    requested = [e for e in errors if e["subject"] == "Requested scope:"]
    assert requested and requested[0]["code"] == "missing_coverage"
    assert "not found" in requested[0]["message"]


def test_real_bold_markdown_preamble_still_passes():
    text = (
        "**Requested scope:** this-conversation\n**Inspected scope:** same\n"
        "**Unavailable evidence:** none\n**Limitations:** none\n"
    )
    assert validate_report.check_common(text, CONTRACTS) == []


def test_coverage_fields_quoted_later_in_the_report_do_not_satisfy_the_preamble():
    # Codex finding (PR #302): coverage fields were searched across the
    # entire document, so a report with no real preamble of its own but a
    # later section that quotes/excerpts another report's four coverage
    # lines (e.g. inside a fenced evidence block) previously passed anyway.
    text = (
        "# Report\n\nNo preamble here.\n\n"
        "## Findings\n\n"
        "Quoting the source report's own preamble as evidence:\n"
        "```\n"
        "**Requested scope:** this-conversation\n**Inspected scope:** same\n"
        "**Unavailable evidence:** none\n**Limitations:** none\n"
        "```\n"
    )
    errors = validate_report.check_common(text, CONTRACTS)
    assert len(errors) == len(CONTRACTS["common"]["coverage_fields"])
    assert all(e["code"] == "missing_coverage" for e in errors)


def test_coverage_fields_in_the_real_preamble_still_pass_when_report_has_later_sections():
    text = (
        "# Report\n\n"
        "**Requested scope:** this-conversation\n**Inspected scope:** same\n"
        "**Unavailable evidence:** none\n**Limitations:** none\n\n"
        "## Findings\n\ntext\n"
    )
    assert validate_report.check_common(text, CONTRACTS) == []


def test_blank_next_step_line_flagged():
    errors = validate_report.check_next_step("Next:\n", required=True)
    assert [e["code"] for e in errors] == ["missing_next_step"]
    assert "no content" in errors[0]["message"]


def _finding_block(
    *, evidence_origin=True, coverage=True, confidence=True, evidence_source=True
) -> str:
    lines = ["<!-- finding:start -->", "Some finding text."]
    if evidence_origin:
        lines.append("Evidence origin: direct")
    if coverage:
        lines.append("Coverage: complete")
    if confidence:
        lines.append("Confidence: high")
    if evidence_source:
        lines.append("Evidence source: this-conversation")
    lines.append("<!-- finding:end -->")
    return "\n".join(lines)


def test_no_finding_blocks_at_all_flags_missing_evidence_metadata():
    errors = validate_report.check_evidence_metadata("no finding blocks here at all", required=True)
    assert [e["code"] for e in errors] == ["missing_evidence_metadata"]
    assert "finding:start" in errors[0]["message"]


def test_unbalanced_finding_markers_flagged():
    # CodeRabbit finding: a dangling <!-- finding:start --> with no matching
    # end marker was previously invisible to FINDING_BLOCK_RE.findall().
    text = _finding_block() + "\n\n<!-- finding:start -->\nno end marker here\n"
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert [e["code"] for e in errors] == ["malformed_finding_marker"]
    assert "unclosed" in errors[0]["message"]


def test_nested_finding_markers_flagged():
    # Codex finding (PR #302, round 2): two <!-- finding:start --> markers
    # followed by two <!-- finding:end --> markers balances numerically
    # (2 == 2), but FINDING_BLOCK_RE's non-greedy match previously collapsed
    # the outer start through the FIRST end marker into one block, silently
    # losing independent validation of the inner finding -- verified live to
    # return zero errors before this fix.
    text = (
        "<!-- finding:start -->\n"
        + _finding_block()
        + "\ninner finding with no metadata at all\n"
        + "<!-- finding:end -->"
    )
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert [e["code"] for e in errors] == ["malformed_finding_marker"]
    assert "Nested" in errors[0]["message"]


def test_dangling_end_marker_with_no_start_flagged():
    text = "<!-- finding:end -->\n" + _finding_block()
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert [e["code"] for e in errors] == ["malformed_finding_marker"]
    assert "no matching" in errors[0]["message"]


def test_metadata_written_outside_any_block_flagged_as_unwrapped():
    # Codex finding: a second finding whose metadata was written but never
    # wrapped in finding:start/end markers was previously invisible.
    text = (
        _finding_block()
        + "\n\n[S02] a second finding\n"
        + "Evidence origin: inferred\nCoverage: partial\nConfidence: low\n"
        + "Evidence source: y\n"
    )
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert [e["code"] for e in errors] == ["unwrapped_evidence_metadata"]


def test_unwrapped_finding_with_no_metadata_attempt_is_a_documented_residual_gap():
    # A finding with no markers AND no metadata attempt at all cannot be
    # mechanically distinguished from ordinary prose without understanding
    # each skill's own finding format -- documented as a structural-only
    # limitation, not a bug. This test pins the current (accepted) behavior.
    text = _finding_block() + "\n\n[S02] a completely unwrapped finding with no markers at all\n"
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_finding_block_missing_some_labels_flags_only_those():
    text = _finding_block(coverage=False, evidence_source=False)
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert len(errors) == 2
    assert all(e["subject"] == "finding-1" for e in errors)
    messages = " ".join(e["message"] for e in errors)
    assert "'Coverage:'" in messages
    assert "'Evidence source:'" in messages
    assert "'Evidence origin:'" not in messages


def test_single_complete_finding_block_passes():
    assert validate_report.check_evidence_metadata(_finding_block(), required=True) == []


def test_multi_finding_report_with_one_unannotated_finding_fails():
    # The exact gap both Codex and Claude confirmed in cross-model review: a
    # report with several findings but only one carrying real metadata must
    # not pass just because *a* finding somewhere is fully annotated.
    text = (
        _finding_block()
        + "\n\n"
        + _finding_block(
            evidence_origin=False, coverage=False, confidence=False, evidence_source=False
        )
    )
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert len(errors) == 4
    assert all(e["subject"] == "finding-2" for e in errors)


def test_multi_finding_report_all_annotated_passes():
    text = _finding_block() + "\n\n" + _finding_block()
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_empty_label_value_flagged_as_invalid_not_missing():
    text = (
        "<!-- finding:start -->\nEvidence origin:\nCoverage: complete\nConfidence: high\n"
        "Evidence source: x\n<!-- finding:end -->"
    )
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert errors == [
        {
            "code": "invalid_evidence_metadata",
            "message": "Finding block 1: metadata label 'Evidence origin:' has no value",
            "subject": "finding-1",
        }
    ]


def test_invalid_enum_value_flagged():
    text = _finding_block().replace("Coverage: complete", "Coverage: invented")
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert len(errors) == 1
    assert errors[0]["code"] == "invalid_evidence_metadata"
    assert "Coverage:" in errors[0]["message"]
    assert "invented" in errors[0]["message"]


def test_enum_value_with_trailing_explanation_still_passes():
    text = _finding_block().replace(
        "Evidence origin: direct", "Evidence origin: direct (re-verified this run)"
    )
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_enum_value_check_is_case_insensitive():
    text = _finding_block().replace("Confidence: high", "Confidence: High")
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_evidence_source_has_no_enum_any_nonempty_value_passes():
    text = _finding_block().replace(
        "Evidence source: this-conversation", "Evidence source: arbitrary free text is fine"
    )
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_no_findings_marker_satisfies_requirement_with_zero_blocks():
    assert validate_report.check_evidence_metadata("<!-- no-findings -->", required=True) == []


def test_no_findings_marker_with_stray_unwrapped_metadata_is_contradictory():
    # Codex finding (PR #302): a stale <!-- no-findings --> marker alongside
    # unwrapped substantive metadata previously returned valid: true,
    # bypassing the per-finding metadata check entirely.
    text = (
        "<!-- no-findings -->\n\n"
        "Actually found something: Evidence origin: direct\nCoverage: complete\n"
        "Confidence: high\nEvidence source: this-conversation\n"
    )
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert [e["code"] for e in errors] == ["contradictory_no_findings"]


def test_no_findings_marker_with_no_stray_metadata_still_passes():
    text = "<!-- no-findings -->\n\nNothing else relevant in this report.\n"
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_marker_example_inside_fenced_block_is_not_mistaken_for_a_real_marker():
    # Codex finding (PR #302): a valid finding whose own body fenced-quotes
    # the marker convention as a documentation example previously had its
    # real, correctly-paired outer markers reported as improperly nested.
    text = (
        "<!-- finding:start -->\n"
        "This report documents the convention:\n"
        "```\n"
        "<!-- finding:start -->\n...\n<!-- finding:end -->\n"
        "```\n"
        "Evidence origin: direct\nCoverage: complete\nConfidence: high\n"
        "Evidence source: this-conversation\n"
        "<!-- finding:end -->"
    )
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_stray_label_with_blank_value_still_flagged_as_unwrapped():
    # CodeRabbit finding (PR #302): the stray-label check used a truthy test,
    # so a stray label present with a BLANK value (falsy "") was silently
    # excluded, even though the label itself unambiguously exists outside
    # any finding block.
    text = _finding_block() + "\n\nEvidence origin:\n"
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert [e["code"] for e in errors] == ["unwrapped_evidence_metadata"]
    assert "Evidence origin:" in errors[0]["message"]


def test_no_findings_marker_absent_and_no_blocks_still_fails():
    errors = validate_report.check_evidence_metadata("nothing relevant here", required=True)
    assert [e["code"] for e in errors] == ["missing_evidence_metadata"]
    assert "no-findings" in errors[0]["message"]


def test_missing_evidence_metadata_not_flagged_when_not_required():
    assert (
        validate_report.check_evidence_metadata("no finding blocks here at all", required=False)
        == []
    )


def test_missing_section_flagged_for_absent_required_heading():
    errors = validate_report.check_required_headings(
        "# Report\nno matching heading", ["## Findings"]
    )
    assert errors == [
        {
            "code": "missing_section",
            "message": "Required heading '## Findings' not found",
            "subject": "## Findings",
        }
    ]


def test_required_heading_present_is_not_flagged():
    assert (
        validate_report.check_required_headings("# Report\n## Findings\ntext", ["## Findings"])
        == []
    )


def test_unknown_skill_returns_single_error():
    result = validate_report.validate("not-a-real-skill", "irrelevant text", CONTRACTS)
    assert result["valid"] is False
    assert [e["code"] for e in result["errors"]] == ["unknown_skill"]


def test_cli_json_output(tmp_path, capsys):
    report = tmp_path / "report.md"
    report.write_text(_fixture("component-valid.md"), encoding="utf-8")

    import json

    sys.argv = [
        "validate_report.py",
        "--skill",
        "analyzing-plugin-components",
        "--report",
        str(report),
        "--json",
    ]
    rc = validate_report.main()
    captured = capsys.readouterr()

    assert rc == 0
    payload = json.loads(captured.out)
    assert payload == {"valid": True, "errors": []}


def test_cli_exits_nonzero_and_lists_errors_for_invalid_report(tmp_path, capsys):
    report = tmp_path / "report.md"
    report.write_text(_fixture("common-missing-next-step.md"), encoding="utf-8")

    sys.argv = [
        "validate_report.py",
        "--skill",
        "analyzing-plugin-components",
        "--report",
        str(report),
    ]
    rc = validate_report.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert "missing_next_step" in captured.err


def test_cli_exits_nonzero_for_unreadable_report(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.md"
    sys.argv = [
        "validate_report.py",
        "--skill",
        "analyzing-plugin-components",
        "--report",
        str(missing),
    ]
    rc = validate_report.main()
    captured = capsys.readouterr()

    assert rc == 2
    assert "could not read" in captured.err
