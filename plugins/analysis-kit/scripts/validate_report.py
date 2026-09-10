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
    # Counts, not a set: the same identifier can legitimately appear more than
    # once in the inventory (e.g. two same-type sub-agent dispatches sharing
    # one agent-type identifier) -- each occurrence needs its own disposition,
    # so collapsing repeats into a set would silently let one disposition
    # marker cover multiple undisposed dispatches.
    inventory_counts: dict[str, int] = {}
    for kind, ident in INVENTORY_RE.findall(text):
        if kind == disposition_type:
            inventory_counts[ident] = inventory_counts.get(ident, 0) + 1

    disposition_counts: dict[str, int] = {}
    for kind, ident in DISPOSITION_RE.findall(text):
        if kind == disposition_type:
            disposition_counts[ident] = disposition_counts.get(ident, 0) + 1

    for ident in sorted(inventory_counts):
        inv_count = inventory_counts[ident]
        disp_count = disposition_counts.get(ident, 0)
        if disp_count < inv_count:
            errors.append(
                {
                    "code": "missing_disposition",
                    "message": (
                        f"{inv_count} inventory occurrence(s) of {disposition_type}:{ident} but "
                        f"only {disp_count} disposition(s) found"
                    ),
                    "subject": f"{disposition_type}:{ident}",
                }
            )
        elif disp_count > inv_count:
            errors.append(
                {
                    "code": "duplicate_disposition",
                    "message": (
                        f"{disp_count} dispositions found for {disposition_type}:{ident}, but only "
                        f"{inv_count} inventory occurrence(s)"
                    ),
                    "subject": f"{disposition_type}:{ident}",
                }
            )

    for ident in sorted(set(disposition_counts) - set(inventory_counts)):
        errors.append(
            {
                "code": "orphaned_disposition",
                "message": (
                    f"Disposition found for {disposition_type}:{ident} but no matching "
                    f"inventory marker exists"
                ),
                "subject": f"{disposition_type}:{ident}",
            }
        )
    return errors


EVIDENCE_METADATA_LABELS = ("Evidence origin:", "Coverage:", "Confidence:", "Evidence source:")
EVIDENCE_METADATA_ENUMS = {
    "Evidence origin:": ("direct", "inherited", "inferred"),
    "Coverage:": ("complete", "sampled", "partial"),
    "Confidence:": ("high", "medium", "low"),
}
FINDING_BLOCK_RE = re.compile(r"<!--\s*finding:start\s*-->(.*?)<!--\s*finding:end\s*-->", re.DOTALL)
NO_FINDINGS_RE = re.compile(r"<!--\s*no-findings\s*-->")


def _label_value(block: str, label: str) -> str | None:
    """Text after `label` on its line, or None if the label isn't present at all."""
    match = re.search(re.escape(label) + r"[ \t]*(.*)", block)
    return match.group(1).strip() if match else None


def check_evidence_metadata(text: str, required: bool) -> list[dict]:
    if not required:
        return []

    blocks = FINDING_BLOCK_RE.findall(text)
    if not blocks:
        if NO_FINDINGS_RE.search(text):
            return []
        return [
            {
                "code": "missing_evidence_metadata",
                "message": (
                    "No <!-- finding:start --> / <!-- finding:end --> blocks found and no "
                    "<!-- no-findings --> marker present -- cannot verify per-finding evidence "
                    "metadata"
                ),
                "subject": "evidence-metadata",
            }
        ]

    errors = []
    for index, block in enumerate(blocks, start=1):
        for label in EVIDENCE_METADATA_LABELS:
            value = _label_value(block, label)
            if value is None:
                errors.append(
                    {
                        "code": "missing_evidence_metadata",
                        "message": f"Finding block {index}: metadata label {label!r} not found",
                        "subject": f"finding-{index}",
                    }
                )
                continue
            if not value:
                errors.append(
                    {
                        "code": "invalid_evidence_metadata",
                        "message": f"Finding block {index}: metadata label {label!r} has no value",
                        "subject": f"finding-{index}",
                    }
                )
                continue
            allowed = EVIDENCE_METADATA_ENUMS.get(label)
            if allowed is not None:
                first_token = value.split()[0].rstrip(".,;:").lower()
                if first_token not in allowed:
                    errors.append(
                        {
                            "code": "invalid_evidence_metadata",
                            "message": (
                                f"Finding block {index}: {label!r} value {value!r} is not one "
                                f"of {list(allowed)}"
                            ),
                            "subject": f"finding-{index}",
                        }
                    )
    return errors


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
