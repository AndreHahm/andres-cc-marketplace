#!/usr/bin/env python3
"""Deterministic report-contract validator for analysis-kit's report-producing skills.

Checks a drafted or persisted report against references/report-contracts.json's
declared per-skill requirements: the shared Coverage Preamble fields, the
standard "Next: ..." handoff line (only for the skills that carry it),
component/actor disposition completeness (via inventory/disposition
HTML-comment markers), and presence of finding evidence metadata. Structural
checks only -- this never attempts to judge whether a finding's content is
actually correct.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CONTRACTS_PATH = Path(__file__).resolve().parent.parent / "references" / "report-contracts.json"

INVENTORY_RE = re.compile(r"<!--\s*inventory:\s*(\S+?):(\S+?)\s*-->")
DISPOSITION_RE = re.compile(r"<!--\s*disposition:\s*(\S+?):(\S+?)\s+.+?-->")


def load_contracts(path: Path = CONTRACTS_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_common(text: str, contracts: dict) -> list[dict]:
    errors = []
    for field in contracts["common"]["coverage_fields"]:
        if field not in text:
            errors.append(
                {
                    "code": "missing_coverage",
                    "message": f"Coverage preamble field '{field}' not found",
                    "subject": field,
                }
            )
    return errors


def check_required_headings(text: str, headings: list[str]) -> list[dict]:
    errors = []
    for heading in headings:
        if heading not in text:
            errors.append(
                {
                    "code": "missing_section",
                    "message": f"Required heading '{heading}' not found",
                    "subject": heading,
                }
            )
    return errors


def check_next_step(text: str, required: bool) -> list[dict]:
    if not required:
        return []
    if "Next:" not in text:
        return [
            {
                "code": "missing_next_step",
                "message": "Standard 'Next: ...' handoff line not found",
                "subject": "next-step",
            }
        ]
    return []


def check_dispositions(text: str, disposition_type: str | None) -> list[dict]:
    if disposition_type is None:
        return []

    errors = []
    inventory_ids: set[str] = set()
    for kind, ident in INVENTORY_RE.findall(text):
        if kind == disposition_type:
            inventory_ids.add(ident)

    disposition_counts: dict[str, int] = {}
    for kind, ident in DISPOSITION_RE.findall(text):
        if kind == disposition_type:
            disposition_counts[ident] = disposition_counts.get(ident, 0) + 1

    for ident in sorted(inventory_ids):
        count = disposition_counts.get(ident, 0)
        if count == 0:
            errors.append(
                {
                    "code": "missing_disposition",
                    "message": f"No disposition found for {disposition_type}:{ident}",
                    "subject": f"{disposition_type}:{ident}",
                }
            )
        elif count > 1:
            errors.append(
                {
                    "code": "duplicate_disposition",
                    "message": (
                        f"{count} dispositions found for {disposition_type}:{ident}, expected 1"
                    ),
                    "subject": f"{disposition_type}:{ident}",
                }
            )
    return errors


def check_evidence_metadata(text: str, required: bool) -> list[dict]:
    if not required:
        return []
    if "Evidence origin:" not in text:
        return [
            {
                "code": "missing_evidence_metadata",
                "message": "No 'Evidence origin:' metadata field found anywhere in the report",
                "subject": "evidence-metadata",
            }
        ]
    return []


def validate(skill: str, text: str, contracts: dict) -> dict:
    if skill not in contracts["skills"]:
        return {
            "valid": False,
            "errors": [
                {
                    "code": "unknown_skill",
                    "message": f"'{skill}' is not declared in report-contracts.json",
                    "subject": skill,
                }
            ],
        }

    skill_contract = contracts["skills"][skill]
    errors: list[dict] = []
    errors += check_common(text, contracts)
    errors += check_required_headings(text, skill_contract.get("required_headings", []))
    errors += check_next_step(text, skill_contract.get("next_step_required", False))
    errors += check_dispositions(text, skill_contract.get("disposition_type"))
    errors += check_evidence_metadata(text, skill_contract.get("requires_evidence_metadata", True))
    return {"valid": len(errors) == 0, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill", required=True, help="Skill name as declared in report-contracts.json"
    )
    parser.add_argument(
        "--report", required=True, help="Path to the drafted or persisted report text"
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON instead of text"
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Error: could not read {report_path}: {exc}", file=sys.stderr)
        return 2

    contracts = load_contracts()
    result = validate(args.skill, text, contracts)

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["valid"]:
        print(f"valid: {args.report} ({args.skill})")
    else:
        print(f"INVALID: {args.report} ({args.skill})", file=sys.stderr)
        for err in result["errors"]:
            print(f"  [{err['code']}] {err['subject']}: {err['message']}", file=sys.stderr)

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
