#!/usr/bin/env python3
"""Fixture-based test for check_evals.py. Run: python scripts/test_check_evals.py

Recreates the cases exercised during development (2026-08-19, extended after a
PR review pass found real bugs -- wrong haystack, one-sided anchoring, silently
dropped non-literal calls, unbounded regex evaluation, unvalidated JSON
structure) so every claim about this script's behavior stays checkable rather
than asserted. Builds temporary fixtures, runs check_evals.py as a subprocess,
and asserts on exit code + expected substrings in stdout/stderr.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "check_evals.py"

# Each function exercises one distinct check_evals.py behavior:
# - check_referenced_files: zero-match guard (pattern matches nothing in SKILL.md)
# - check_bad_word: one-sided anchoring (\bcat matches "catalog", must FAIL)
# - check_workflow_headers: haystack-unclear SKIP (arg isn't SKILL.md content)
# - check_dynamic: non-literal pattern (rf-string), must be flagged for manual review
# - check_catastrophic: ReDoS pattern, must be caught by the regex timeout
# - check_multiline_flag: re.MULTILINE must be forwarded, or ^target$ false-FAILs
# - check_unsupported_flag: an unrecognized flag must be flagged for manual review
SMOKE_TEST_PY = r"""
import re

def check_referenced_files(skill_md_text):
    matches = re.findall(r"references/[^\s]+\.md", skill_md_text)
    for m in matches:
        assert True

def check_bad_word(skill_md_text):
    if re.search(r"\bcat", skill_md_text):
        return True

def check_workflow_headers(workflow_text):
    return re.findall(r"^##+ Phase (\d+):", workflow_text, re.MULTILINE)

def check_dynamic(skill_md_text, needle):
    return re.search(rf"{needle}", skill_md_text)

def check_catastrophic(skill_md_text):
    return re.findall(r"(a+)+$", skill_md_text)

def check_multiline_flag(skill_md_text):
    return re.findall(r"^target$", skill_md_text, re.MULTILINE)

def check_unsupported_flag(skill_md_text):
    return re.findall(r"unused_pattern", skill_md_text, re.LOCALE)
"""

SKILL_MD = (
    "This is a skill about cats and dogs.\n"
    "No references directory here.\n"
    "aaaaaaaaaaaaaaaaaaaaaaaaa!\n"
    "target\n"
)

EVALS_GOOD = json.dumps(
    {
        "testing_validation_coverage": {
            "declared_scenarios_total": 4,
            "declared_scenarios_covered": 3,
            "uncovered": ["scenario x"],
        }
    }
)
EVALS_BAD = json.dumps(
    {
        "testing_validation_coverage": {
            "declared_scenarios_total": 4,
            "declared_scenarios_covered": 3,
            "uncovered": [],
        }
    }
)
EVALS_MALFORMED = "{not valid json"
EVALS_ARRAY_ROOT = json.dumps([1, 2, 3])
EVALS_NON_INT_TOTAL = json.dumps(
    {
        "testing_validation_coverage": {
            "declared_scenarios_total": "four",
            "declared_scenarios_covered": 3,
            "uncovered": [],
        }
    }
)
EVALS_NON_LIST_UNCOVERED = json.dumps(
    {
        "testing_validation_coverage": {
            "declared_scenarios_total": 4,
            "declared_scenarios_covered": 3,
            "uncovered": "none",
        }
    }
)


def run(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        smoke_test = tmp_path / "smoke_test.py"
        smoke_test.write_text(SMOKE_TEST_PY, encoding="utf-8")
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(SKILL_MD, encoding="utf-8")
        evals_good = tmp_path / "evals_good.json"
        evals_good.write_text(EVALS_GOOD, encoding="utf-8")
        evals_bad = tmp_path / "evals_bad.json"
        evals_bad.write_text(EVALS_BAD, encoding="utf-8")
        evals_malformed = tmp_path / "evals_malformed.json"
        evals_malformed.write_text(EVALS_MALFORMED, encoding="utf-8")
        evals_array_root = tmp_path / "evals_array_root.json"
        evals_array_root.write_text(EVALS_ARRAY_ROOT, encoding="utf-8")
        evals_non_int_total = tmp_path / "evals_non_int_total.json"
        evals_non_int_total.write_text(EVALS_NON_INT_TOTAL, encoding="utf-8")
        evals_non_list_uncovered = tmp_path / "evals_non_list_uncovered.json"
        evals_non_list_uncovered.write_text(EVALS_NON_LIST_UNCOVERED, encoding="utf-8")

        cases = [
            (
                "Check 1: zero-match, one-sided anchoring, haystack-unclear, "
                "non-literal, and ReDoS timeout",
                [
                    "--smoke-test",
                    str(smoke_test),
                    "--skill-md",
                    str(skill_md),
                    "--regex-timeout",
                    "0.5",
                ],
                1,
                [
                    "FAIL (zero-match guard)",
                    "FAIL (anchored matching)",
                    "SKIP (haystack unclear)",
                    "SKIP (manual review)",
                    "could not be evaluated",
                    "PASS (zero-match guard): re.findall(r'^target$') found",
                    "LOCALE",
                ],
            ),
            ("good coverage arithmetic", ["--evals-json", str(evals_good)], 0, ["PASS (counting)"]),
            ("bad coverage arithmetic", ["--evals-json", str(evals_bad)], 1, ["FAIL (counting)"]),
            (
                "malformed evals.json (invalid JSON)",
                ["--evals-json", str(evals_malformed)],
                1,
                ["FAIL (blocking)"],
            ),
            (
                "malformed evals.json (array root)",
                ["--evals-json", str(evals_array_root)],
                1,
                ["FAIL (blocking)", "root value"],
            ),
            (
                "malformed evals.json (non-int total)",
                ["--evals-json", str(evals_non_int_total)],
                1,
                ["FAIL (blocking)", "declared_scenarios_total"],
            ),
            (
                "malformed evals.json (non-list uncovered)",
                ["--evals-json", str(evals_non_list_uncovered)],
                1,
                ["FAIL (blocking)", "uncovered"],
            ),
            ("no args", [], 2, ["at least one of"]),
        ]

        for name, args, expected_code, expected_substrings in cases:
            code, out, err = run(*args)
            combined = out + err
            if code != expected_code:
                failures.append(f"[{name}] exit code {code}, expected {expected_code}")
            for s in expected_substrings:
                if s not in combined:
                    failures.append(f"[{name}] missing expected substring: {s!r}")

    if failures:
        print(f"FAIL: {len(failures)} case(s) failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"PASS: all {len(cases)} fixture cases behaved as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
