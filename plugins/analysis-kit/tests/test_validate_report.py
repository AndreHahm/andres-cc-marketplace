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
