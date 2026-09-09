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


def test_missing_evidence_metadata_flagged_for_each_absent_label_when_required():
    errors = validate_report.check_evidence_metadata("no metadata block here", required=True)
    assert [e["code"] for e in errors] == ["missing_evidence_metadata"] * 4


def test_partial_evidence_metadata_flags_only_the_missing_labels():
    text = "Evidence origin: direct\nConfidence: high\n"
    errors = validate_report.check_evidence_metadata(text, required=True)
    assert len(errors) == 2
    assert {e["subject"] for e in errors} == {"evidence-metadata"}
    messages = " ".join(e["message"] for e in errors)
    assert "'Coverage:'" in messages
    assert "'Source:'" in messages
    assert "'Evidence origin:'" not in messages


def test_all_four_evidence_metadata_labels_present_passes():
    text = (
        "Evidence origin: direct\nCoverage: complete\nConfidence: high\nSource: this-conversation\n"
    )
    assert validate_report.check_evidence_metadata(text, required=True) == []


def test_missing_evidence_metadata_not_flagged_when_not_required():
    assert validate_report.check_evidence_metadata("no metadata block here", required=False) == []


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
