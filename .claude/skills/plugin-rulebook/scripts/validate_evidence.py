#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml"]
# ///
# Validates a document against one of the four shapes defined in
# references/evidence-schema.md: manifest, finding, report (revision), or
# bundle (evidence bundle). Used by plugin-lifecycle-downstream and any
# component that produces or consumes these shapes to check "does this
# report conform" without re-deriving the schema by hand.
#
# Usage:
#   validate_evidence.py <manifest|finding|report|bundle> <path-to-document.yaml>
#   validate_evidence.py --self-test

import sys
from pathlib import Path

import yaml

STATUS_VALUES = {"open", "fixed", "verified", "deferred", "accepted_risk", "superseded"}
CANONICAL_SEVERITY_VALUES = {"critical", "major", "minor"}
RULE_TYPE_VALUES = {"required", "advisory"}
SCOPE_MODE_VALUES = {"changed", "named", "full"}
INVOCATION_MODE_VALUES = {"full_pipeline", "external_entry"}
DEEP_TEST_VALUES = {"not_run", "scoped", "full"}
GRADING_VALUES = {"not_run", "evidence_only"}


def err(problems, message):
    problems.append(message)


def check_required(doc, fields, problems, where=""):
    for field in fields:
        if field not in doc:
            err(problems, f"{where}missing required field '{field}'")


def check_id_format(finding_id, problems, where=""):
    if not isinstance(finding_id, str) or ":" not in finding_id:
        err(problems, f"{where}id '{finding_id}' does not match '<source>:<local-id>' format")


def validate_finding(doc, problems, where=""):
    check_required(
        doc,
        ["id", "source", "scope", "severity", "status"],
        problems,
        where,
    )
    if "id" in doc:
        check_id_format(doc["id"], problems, where)
    # isinstance(..., str) checked before the `in` membership test against
    # each values-set below -- an unhashable value (e.g. a YAML list) would
    # otherwise raise TypeError from the set-membership test itself instead
    # of producing a clean validation problem.
    if "status" in doc:
        if not isinstance(doc["status"], str) or doc["status"] not in STATUS_VALUES:
            err(problems, f"{where}status '{doc['status']}' not in {sorted(STATUS_VALUES)}")
    if "severity" in doc:
        if not isinstance(doc["severity"], str) or doc["severity"] not in CANONICAL_SEVERITY_VALUES:
            err(
                problems,
                f"{where}severity '{doc['severity']}' not in {sorted(CANONICAL_SEVERITY_VALUES)}",
            )
    if "rule_type" in doc:
        if not isinstance(doc["rule_type"], str) or doc["rule_type"] not in RULE_TYPE_VALUES:
            err(
                problems, f"{where}rule_type '{doc['rule_type']}' not in {sorted(RULE_TYPE_VALUES)}"
            )


def validate_findings_list(doc, problems, where=""):
    findings = doc.get("findings", [])
    if not isinstance(findings, list):
        err(problems, f"{where}'findings' must be a list")
        return
    for i, finding in enumerate(findings):
        validate_finding(finding, problems, where=f"{where}findings[{i}]: ")


def validate_manifest(doc, problems):
    check_required(
        doc,
        [
            "version",
            "run_id",
            "target_plugin_root",
            "baseline_commit",
            "invocation_mode",
            "scope_mode",
            "revision",
        ],
        problems,
    )
    # isinstance checked before the `in` membership test against each
    # values-set below -- same pattern as validate_finding, and for the same
    # reason: an unhashable value (e.g. a YAML list) would otherwise raise
    # TypeError from the set-membership test itself instead of producing a
    # clean validation problem.
    if "invocation_mode" in doc:
        if (
            not isinstance(doc["invocation_mode"], str)
            or doc["invocation_mode"] not in INVOCATION_MODE_VALUES
        ):
            err(
                problems,
                f"invocation_mode '{doc['invocation_mode']}' "
                f"not in {sorted(INVOCATION_MODE_VALUES)}",
            )
    if "scope_mode" in doc:
        if not isinstance(doc["scope_mode"], str) or doc["scope_mode"] not in SCOPE_MODE_VALUES:
            err(problems, f"scope_mode '{doc['scope_mode']}' not in {sorted(SCOPE_MODE_VALUES)}")
    phases = doc.get("optional_phases_selected", {})
    if isinstance(phases, dict):
        if "deep_test" in phases:
            if (
                not isinstance(phases["deep_test"], str)
                or phases["deep_test"] not in DEEP_TEST_VALUES
            ):
                err(
                    problems,
                    f"optional_phases_selected.deep_test '{phases['deep_test']}' "
                    f"not in {sorted(DEEP_TEST_VALUES)}",
                )
        if "grading" in phases:
            if not isinstance(phases["grading"], str) or phases["grading"] not in GRADING_VALUES:
                err(
                    problems,
                    f"optional_phases_selected.grading '{phases['grading']}' "
                    f"not in {sorted(GRADING_VALUES)}",
                )
    else:
        err(problems, "optional_phases_selected must be an object")


def validate_report(doc, problems):
    check_required(
        doc,
        [
            "version",
            "run_id",
            "report_id",
            "revision",
            "produced_by",
            "baseline_commit",
            "current_commit",
        ],
        problems,
    )
    validate_findings_list(doc, problems)


def validate_bundle(doc, problems):
    check_required(
        doc,
        [
            "version",
            "run_id",
            "scope_manifest_ref",
            "baseline_commit",
            "current_commit",
            "report_revisions",
        ],
        problems,
    )
    validate_findings_list(doc, problems)


VALIDATORS = {
    "manifest": validate_manifest,
    "finding": validate_finding,
    "report": validate_report,
    "bundle": validate_bundle,
}


def validate(shape, doc):
    problems = []
    VALIDATORS[shape](doc, problems)
    return problems


def run_self_test():
    valid_manifest = {
        "version": "1.0",
        "run_id": "run-001",
        "target_plugin_root": "plugins/example-plugin",
        "baseline_commit": "abc1234",
        "invocation_mode": "full_pipeline",
        "scope_mode": "full",
        "revision": 1,
    }
    invalid_manifest = {"version": "1.0", "run_id": "run-001"}
    invalid_manifest_non_string_fields = {
        "version": "1.0",
        "run_id": "run-001",
        "target_plugin_root": "plugins/example-plugin",
        "baseline_commit": "abc1234",
        "invocation_mode": ["full_pipeline"],
        "scope_mode": "full",
        "revision": 1,
        "optional_phases_selected": {"deep_test": ["scoped"]},
    }

    valid_finding = {
        "id": "consistency-reviewer:M1",
        "source": "consistency-reviewer",
        "scope": "skills/plugin-auditor/SKILL.md",
        "severity": "major",
        "status": "open",
    }
    invalid_finding = {
        "id": "no-colon-here",
        "source": "consistency-reviewer",
        "scope": "skills/plugin-auditor/SKILL.md",
        "severity": "major",
        "status": "not_a_real_status",
    }
    invalid_finding_bad_severity = {
        "id": "consistency-reviewer:M1",
        "source": "consistency-reviewer",
        "scope": "skills/plugin-auditor/SKILL.md",
        "severity": "urgent",
        "status": "open",
    }
    invalid_finding_severity_not_string = {
        "id": "consistency-reviewer:M2",
        "source": "consistency-reviewer",
        "scope": "skills/plugin-auditor/SKILL.md",
        "severity": ["major", "minor"],
        "status": "open",
    }

    valid_report = {
        "version": "1.0",
        "run_id": "run-001",
        "report_id": "phase5-plugin-auditor",
        "revision": 1,
        "produced_by": "plugin-auditor",
        "baseline_commit": "abc1234",
        "current_commit": "abc1234",
        "findings": [valid_finding],
    }
    invalid_report = {"version": "1.0", "run_id": "run-001", "findings": [invalid_finding]}

    valid_bundle = {
        "version": "1.0",
        "run_id": "run-001",
        "scope_manifest_ref": {"report_id": "manifest", "revision": 1},
        "baseline_commit": "abc1234",
        "current_commit": "def5678",
        "report_revisions": [
            {"report_id": "phase5-plugin-auditor", "revision": 1, "path": "reports/phase5.yaml"}
        ],
        "findings": [valid_finding],
    }
    invalid_bundle = {"version": "1.0", "run_id": "run-001"}

    cases = [
        ("manifest", valid_manifest, True),
        ("manifest", invalid_manifest, False),
        ("manifest", invalid_manifest_non_string_fields, False),
        ("finding", valid_finding, True),
        ("finding", invalid_finding, False),
        ("finding", invalid_finding_bad_severity, False),
        ("finding", invalid_finding_severity_not_string, False),
        ("report", valid_report, True),
        ("report", invalid_report, False),
        ("bundle", valid_bundle, True),
        ("bundle", invalid_bundle, False),
    ]

    failed = False
    for shape, doc, expect_valid in cases:
        problems = validate(shape, doc)
        is_valid = not problems
        outcome = "PASS" if is_valid == expect_valid else "FAIL"
        if outcome == "FAIL":
            failed = True
        label = "valid" if expect_valid else "invalid"
        detail = "no problems" if is_valid else "; ".join(problems)
        print(f"{outcome}  {shape} ({label} sample): {detail}")

    # Root-type guard (see main()): a truthy non-mapping YAML root ([], false,
    # ...) must be rejected, not silently folded into {} by a bare `or {}`.
    for source in ("[]", "false"):
        raw = yaml.safe_load(source)
        doc = {} if raw is None else raw
        outcome = "PASS" if not isinstance(doc, dict) else "FAIL"
        if outcome == "FAIL":
            failed = True
        print(
            f"{outcome}  root-type guard (YAML source {source!r}): "
            f"parsed as {type(doc).__name__}, not silently normalized to a mapping"
        )

    sys.exit(1 if failed else 0)


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        run_self_test()
        return

    if len(sys.argv) != 3 or sys.argv[1] not in VALIDATORS:
        print(
            f"Usage: {sys.argv[0]} <{'|'.join(VALIDATORS)}> <path-to-document.yaml>",
            file=sys.stderr,
        )
        print(f"       {sys.argv[0]} --self-test", file=sys.stderr)
        sys.exit(2)

    shape, path = sys.argv[1], Path(sys.argv[2])
    if not path.exists():
        print(f"No such file: {path}", file=sys.stderr)
        sys.exit(2)

    # An empty or comments-only YAML file parses to None, not {} -- normalize
    # only that case so every validator function can assume a dict without a
    # None-check of its own. A truthy non-mapping root ([], false, 0, '', a
    # scalar, a list) must NOT be silently folded into {} here -- `or {}`
    # would also catch those falsey-but-real roots, letting a malformed
    # document reach validate() as an empty mapping instead of failing
    # loudly on its actual (wrong) type.
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc = {} if raw is None else raw
    if not isinstance(doc, dict):
        print(f"FAIL  document root is a {type(doc).__name__}, not a mapping")
        sys.exit(1)
    problems = validate(shape, doc)
    if problems:
        for problem in problems:
            print(f"FAIL  {problem}")
        sys.exit(1)
    print(f"PASS  {path} conforms to the {shape} shape")


if __name__ == "__main__":
    main()
