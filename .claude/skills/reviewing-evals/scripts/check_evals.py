#!/usr/bin/env python3
"""Mechanical portion of Checks 1-2 from reviewing-evals/SKILL.md.

Usage:
    python scripts/check_evals.py [--smoke-test PATH] [--skill-md PATH] [--evals-json PATH]

Any argument may be omitted; the check it feeds is skipped (matching the
skill's own "skip any check whose target artifact doesn't exist" rule) rather
than treated as a failure. This script only covers the parts of Checks 1-2
that are mechanical (regex extraction/arithmetic) -- the semantic judgment
calls (e.g. "does this eval prompt actually exercise this scenario") stay
agent-performed, per SKILL.md.
"""

import argparse
import json
import re
import sys
from pathlib import Path

FINDALL_RE = re.compile(r"re\.findall\(\s*r?([\"'])(.*?)\1")
SEARCH_RE = re.compile(r"re\.search\(\s*r?([\"'])(.*?)\1")


def check_zero_match_and_anchoring(smoke_test_path: Path, skill_md_text: str | None) -> list[str]:
    """Best-effort static scan: extract literal re.findall/re.search patterns
    from smoke_test.py and flag zero-match iteration and unanchored short needles.
    Non-literal (f-string/variable-built) patterns are skipped and reported as
    needing manual review -- this script does not execute the target script."""
    findings = []
    try:
        source = smoke_test_path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"FAIL: could not read {smoke_test_path}: {e}"]

    findall_matches = FINDALL_RE.findall(source)
    for _, pattern in findall_matches:
        if skill_md_text is None:
            findings.append(
                f"SKIP: re.findall(r'{pattern}') found but no --skill-md given "
                "to test it against -- cannot check for zero-match vacuity"
            )
            continue
        try:
            hits = re.findall(pattern, skill_md_text)
        except re.error as e:
            findings.append(
                f"SKIP: pattern '{pattern}' is not valid outside its original context: {e}"
            )
            continue
        if not hits:
            findings.append(
                f"FAIL (zero-match guard): re.findall(r'{pattern}') matches nothing "
                "against the target's SKILL.md -- any check iterating this result is vacuous"
            )
        else:
            findings.append(
                f"PASS (zero-match guard): re.findall(r'{pattern}') found {len(hits)} match(es)"
            )

    search_matches = SEARCH_RE.findall(source)
    for _, pattern in search_matches:
        is_anchored = (
            pattern.startswith(r"\b")
            or pattern.endswith(r"\b")
            or pattern.startswith("^")
            or pattern.endswith("$")
        )
        bare_needle = re.sub(r"[\\^$.*+?()\[\]{}|]", "", pattern)
        if not is_anchored and len(bare_needle) <= 4:
            findings.append(
                f"FAIL (anchored matching): re.search(r'{pattern}') is a short, unanchored "
                "needle -- likely to false-positive on unrelated prose"
            )
        else:
            findings.append(
                f"PASS (anchored matching): re.search(r'{pattern}') looks anchored "
                "or long enough to be specific"
            )

    if not findall_matches and not search_matches:
        findings.append(
            "INFO: no re.findall/re.search calls found via static scan "
            "-- nothing to check mechanically"
        )

    return findings


def check_coverage_arithmetic(evals_json_path: Path) -> list[str]:
    try:
        raw = evals_json_path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"FAIL: could not read {evals_json_path}: {e}"]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"FAIL (blocking): {evals_json_path} is not valid JSON: {e}"]

    coverage = data.get("testing_validation_coverage")
    if coverage is None:
        return ["INFO: no testing_validation_coverage field present -- nothing to check"]

    total = coverage.get("declared_scenarios_total")
    covered = coverage.get("declared_scenarios_covered")
    uncovered = coverage.get("uncovered", [])

    if total is None or covered is None:
        return ["SKIP: declared_scenarios_total/declared_scenarios_covered not both present"]

    findings = []
    if covered + len(uncovered) != total:
        findings.append(
            f"FAIL (counting): declared_scenarios_covered ({covered}) + len(uncovered) "
            f"({len(uncovered)}) = {covered + len(uncovered)}, "
            f"expected declared_scenarios_total ({total})"
        )
    else:
        findings.append(
            f"PASS (counting): {covered} covered + {len(uncovered)} uncovered == {total} total"
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", type=Path, default=None)
    parser.add_argument("--skill-md", type=Path, default=None)
    parser.add_argument("--evals-json", type=Path, default=None)
    args = parser.parse_args()

    if not any([args.smoke_test, args.evals_json]):
        parser.error("at least one of --smoke-test or --evals-json is required")

    exit_code = 0
    skill_md_text = None
    if args.skill_md is not None:
        try:
            skill_md_text = args.skill_md.read_text(encoding="utf-8")
        except OSError as e:
            print(f"FAIL: could not read --skill-md {args.skill_md}: {e}")
            exit_code = 1

    if args.smoke_test is not None:
        print(f"\n== Check 1: {args.smoke_test} ==")
        for line in check_zero_match_and_anchoring(args.smoke_test, skill_md_text):
            print(line)
            if line.startswith("FAIL"):
                exit_code = 1

    if args.evals_json is not None:
        print(f"\n== Check 2: {args.evals_json} ==")
        for line in check_coverage_arithmetic(args.evals_json):
            print(line)
            if line.startswith("FAIL"):
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
