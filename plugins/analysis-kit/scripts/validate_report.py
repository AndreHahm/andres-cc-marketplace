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


PREAMBLE_BOUNDARY_RE = re.compile(r"^#{2,6}[ \t]", re.MULTILINE)


def _preamble_region(text: str) -> str:
    """Text from the start of the document up to the first `##`-or-deeper heading.

    Per report-evidence-convention.md, the Coverage Preamble sits between a
    report's own title and its first analysis section. Restricting the
    coverage-field search to this region prevents a later section that
    merely quotes or excerpts another report's own preamble lines (e.g. a
    fenced evidence block, or a source-report excerpt inside an
    `analyzing-plugin-components`/`reviewing-analysis-findings` report) from
    satisfying THIS report's own coverage-field requirement. Verified live:
    without this restriction, a report with no real preamble of its own but
    a later section quoting another report's four coverage lines returned
    `valid: true`.
    """
    match = PREAMBLE_BOUNDARY_RE.search(text)
    return text[: match.start()] if match else text


def check_common(text: str, contracts: dict) -> list[dict]:
    errors = []
    preamble = _preamble_region(_strip_fenced(text))
    for field in contracts["common"]["coverage_fields"]:
        value = _label_value(preamble, field)
        if value is None:
            errors.append(
                {
                    "code": "missing_coverage",
                    "message": f"Coverage preamble field '{field}' not found",
                    "subject": field,
                }
            )
        elif not value:
            errors.append(
                {
                    "code": "missing_coverage",
                    "message": f"Coverage preamble field '{field}' has no value",
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
    value = _label_value(_strip_fenced(text), "Next:")
    if value is None:
        return [
            {
                "code": "missing_next_step",
                "message": "Standard 'Next: ...' handoff line not found",
                "subject": "next-step",
            }
        ]
    if not value:
        return [
            {
                "code": "missing_next_step",
                "message": "'Next:' line found but has no content after it",
                "subject": "next-step",
            }
        ]
    return []


def check_dispositions(text: str, disposition_type: str | None) -> list[dict]:
    if disposition_type is None:
        return []

    # Fence-stripped once, up front: a report that quotes an
    # `<!-- inventory: -->`/`<!-- disposition: -->` example inside a fenced
    # code block (e.g. documenting the convention during self-analysis) must
    # not have that literal example counted as a real marker. Confirmed live:
    # without this, a fenced inventory example was counted as a genuine
    # inventory entry and required a matching disposition that doesn't exist.
    text = _strip_fenced(text)

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
NO_FINDINGS_RE = re.compile(r"<!--\s*no-findings\s*-->")
FENCE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)


def _strip_fenced(text: str) -> str:
    """`text` with every fenced ```...``` code block's own content removed.

    Every structural check in this module (marker/inventory/disposition/
    coverage/metadata lookups) must not mistake a documentation example -- a
    report quoting this convention's own syntax as an illustration, often
    during a skill's own self-analysis -- for real structural content.
    `_scan_finding_markers` filters fenced marker POSITIONS directly for its
    own depth-tracking scan (kept as-is, independent of this helper); every
    other regex/label lookup below instead calls this function first, so a
    fenced span is never visible to a plain `.search()`/`.findall()`/
    `_label_value()` call. Confirmed live as three independent false
    positives beyond the marker-nesting case this module already handled: a
    fenced `<!-- no-findings -->` example satisfying the no-findings escape
    hatch on an otherwise metadata-free report, a real finding's own
    fenced-quoted excerpt of another report's metadata satisfying that
    finding's own per-block requirement, and a fenced `<!-- inventory: -->`
    example being counted as a real inventory entry requiring a disposition.
    """
    return FENCE_RE.sub("", text)


def _label_value(block: str, label: str) -> str | None:
    """Text after `label` on its own line, or None if the label isn't present at all.

    Anchored to the start of a line (optionally through markdown `**bold**`
    wrapping, e.g. `**Requested scope:** value`) -- a bare, unanchored search
    would also match the label mentioned in ordinary prose elsewhere in the
    document (e.g. "as mentioned in Requested scope: above"), treating that
    prose mention as if it were the actual field.
    """
    pattern = r"^\*{0,2}" + re.escape(label) + r"\*{0,2}[ \t]*(.*)"
    match = re.search(pattern, block, re.MULTILINE)
    return match.group(1).strip() if match else None


FINDING_START_RE = re.compile(r"<!--\s*finding:start\s*-->")
FINDING_END_RE = re.compile(r"<!--\s*finding:end\s*-->")


def _fenced_spans(text: str) -> list[tuple[int, int]]:
    """Start/end positions of every fenced ``` ... ``` code block in `text`."""
    return [(m.start(), m.end()) for m in FENCE_RE.finditer(text)]


def _scan_finding_markers(text: str) -> tuple[list[str], list[tuple[int, int]], list[dict]]:
    """Walk finding markers in document order and extract top-level blocks.

    A start/end count comparison alone can't catch nesting: two starts
    followed by two ends balances numerically (2 == 2), but a non-greedy
    single-pass regex match collapses the outer start through the FIRST end
    marker into one block, silently losing independent validation of the
    inner finding -- verified live, this previously returned no errors at
    all for a nested pair. Tracking nesting depth explicitly, marker by
    marker, catches this instead of trusting a count.

    Markers found inside a fenced ```...``` code block are ignored entirely
    -- a report that quotes marker syntax as a documentation example (e.g.
    illustrating this convention inside a self-analysis report) must not
    have that literal example text mistaken for a real, structural marker.
    Confirmed live as a real false positive: a valid finding whose own body
    fenced-quoted the marker convention as an example previously had its
    real, correctly-paired outer markers reported as improperly nested.

    Returns `(blocks, spans, errors)` -- `blocks` is each top-level finding's
    own inner content (between its start/end markers, exclusive); `spans` is
    the corresponding `(start, end)` position of each full block INCLUDING
    both marker delimiters, in the same order, used by callers that need to
    compute what's left over once every real block is removed from `text`.
    """
    fenced_spans = _fenced_spans(text)

    def _outside_fence(pos: int) -> bool:
        return not any(start <= pos < end for start, end in fenced_spans)

    markers = sorted(
        [
            (m.start(), m.end(), "start")
            for m in FINDING_START_RE.finditer(text)
            if _outside_fence(m.start())
        ]
        + [
            (m.start(), m.end(), "end")
            for m in FINDING_END_RE.finditer(text)
            if _outside_fence(m.start())
        ],
        key=lambda item: item[0],
    )

    blocks: list[str] = []
    spans: list[tuple[int, int]] = []
    errors: list[dict] = []
    depth = 0
    outer_start = 0
    content_start = 0
    for marker_start, marker_end, kind in markers:
        if kind == "start":
            if depth == 0:
                outer_start = marker_start
                content_start = marker_end
            else:
                errors.append(
                    {
                        "code": "malformed_finding_marker",
                        "message": (
                            "Nested <!-- finding:start --> marker found -- findings must not "
                            "nest; each finding needs its own independent start/end pair"
                        ),
                        "subject": "evidence-metadata",
                    }
                )
            depth += 1
        else:
            if depth == 0:
                errors.append(
                    {
                        "code": "malformed_finding_marker",
                        "message": (
                            "<!-- finding:end --> marker found with no matching "
                            "<!-- finding:start --> -- every finding must be fully wrapped"
                        ),
                        "subject": "evidence-metadata",
                    }
                )
                continue
            depth -= 1
            if depth == 0:
                blocks.append(text[content_start:marker_start])
                spans.append((outer_start, marker_end))
    if depth > 0:
        errors.append(
            {
                "code": "malformed_finding_marker",
                "message": (
                    f"{depth} <!-- finding:start --> marker(s) left unclosed -- every finding "
                    "must be fully wrapped, and an unmatched marker means at least one finding "
                    "was not validated"
                ),
                "subject": "evidence-metadata",
            }
        )
    return blocks, spans, errors


def check_evidence_metadata(text: str, required: bool) -> list[dict]:
    if not required:
        return []

    blocks, block_spans, marker_errors = _scan_finding_markers(text)
    if marker_errors:
        return marker_errors

    if not blocks:
        # Fence-stripped: a report that quotes <!-- no-findings --> as a
        # documentation example inside a fenced code block (rather than
        # actually declaring no findings) must not have that literal example
        # satisfy the no-findings escape hatch. Confirmed live: without this,
        # a fenced no-findings example on an otherwise metadata-free report
        # returned `valid: true`.
        no_findings_text = _strip_fenced(text)
        if NO_FINDINGS_RE.search(no_findings_text):
            # A stray, unwrapped evidence-metadata label alongside a
            # <!-- no-findings --> marker means the report actually contains
            # substantive finding content that contradicts its own
            # no-findings claim -- e.g. a draft that kept a stale
            # <!-- no-findings --> marker after a finding was added but
            # never wrapped. Verified live: without this check, that exact
            # combination returned `valid: true`, silently bypassing the
            # per-finding metadata requirement via the no-findings escape
            # hatch.
            stray_labels = [
                label
                for label in EVIDENCE_METADATA_LABELS
                if _label_value(no_findings_text, label) is not None
            ]
            if stray_labels:
                return [
                    {
                        "code": "contradictory_no_findings",
                        "message": (
                            f"<!-- no-findings --> marker present but evidence metadata "
                            f"label(s) {stray_labels} also found -- report contains "
                            "unwrapped finding content contradicting the no-findings claim"
                        ),
                        "subject": "evidence-metadata",
                    }
                ]
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

    # A substantive finding whose metadata was written but never wrapped in
    # <!-- finding:start/end --> markers is otherwise invisible to the
    # per-block loop below -- this catches the common case of forgetting the
    # wrapper while still writing the metadata fields. `remainder` is built
    # from the same fence-aware, nesting-aware block spans `_scan_finding_markers`
    # already computed, not a second, independently regex-matched pass over
    # the text -- reusing one source of truth for "what's inside a real
    # block" avoids the two mechanisms disagreeing on a fenced or nested
    # example. It cannot catch a finding with no metadata attempt at all and
    # no markers -- that's a documented, structural-only limitation (see this
    # script's own module docstring); nothing short of understanding each
    # skill's own finding format could detect that case.
    remainder_parts = []
    prev_end = 0
    for span_start, span_end in block_spans:
        remainder_parts.append(text[prev_end:span_start])
        prev_end = span_end
    remainder_parts.append(text[prev_end:])
    remainder = "".join(remainder_parts)

    # `is not None`, not a truthy check: a stray label present with a BLANK
    # value (e.g. a lone "Evidence origin:" with nothing after it) must still
    # count as stray, unwrapped metadata -- a truthy check silently ignored
    # that case, since `_label_value` returns "" (falsy) for a present-but-empty
    # label, not None. Fence-stripped too: a fenced example of the metadata
    # convention sitting outside any real block must not be mistaken for a
    # genuine stray, unwrapped label.
    stray_labels = [
        label
        for label in EVIDENCE_METADATA_LABELS
        if _label_value(_strip_fenced(remainder), label) is not None
    ]
    if stray_labels:
        errors.append(
            {
                "code": "unwrapped_evidence_metadata",
                "message": (
                    f"Evidence metadata label(s) {stray_labels} found outside any "
                    "<!-- finding:start -->/<!-- finding:end --> block -- likely a finding whose "
                    "metadata was written but never wrapped"
                ),
                "subject": "evidence-metadata",
            }
        )

    for index, block in enumerate(blocks, start=1):
        # Fence-stripped: a finding may legitimately quote another report's
        # metadata inside a fenced excerpt as supporting evidence -- that
        # quoted text must not satisfy THIS finding's own per-block metadata
        # requirement. Confirmed live: a finding with no real metadata of its
        # own but a fenced excerpt of another report's four metadata lines
        # returned `valid: true`.
        block_stripped = _strip_fenced(block)
        for label in EVIDENCE_METADATA_LABELS:
            value = _label_value(block_stripped, label)
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
    except (OSError, UnicodeDecodeError) as exc:
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
