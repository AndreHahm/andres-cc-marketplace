#!/usr/bin/env python3
"""Fixture-based test for check_evals.py. Run: python scripts/test_check_evals.py

Recreates the 5 cases exercised during development (2026-08-19) so the claim
"tested against 5 fixture cases" in SKILL.md's change history is checkable
rather than asserted. Builds temporary fixtures, runs check_evals.py as a
subprocess, and asserts on exit code + expected substrings in stdout/stderr.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "check_evals.py"

SMOKE_TEST_PY = """
import re

def check_referenced_files(text):
    matches = re.findall(r"references/[^\\s]+\\.md", text)
    for m in matches:
        assert True

def check_bad_word(text):
    if re.search(r"cat", text):
        return True
"""

SKILL_MD = "This is a skill about cats and dogs.\nNo references directory here.\n"

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

        cases = [
            (
                "zero-match + unanchored (smoke_test + skill-md)",
                ["--smoke-test", str(smoke_test), "--skill-md", str(skill_md)],
                1,
                ["FAIL (zero-match guard)", "FAIL (anchored matching)"],
            ),
            ("good coverage arithmetic", ["--evals-json", str(evals_good)], 0, ["PASS (counting)"]),
            ("bad coverage arithmetic", ["--evals-json", str(evals_bad)], 1, ["FAIL (counting)"]),
            (
                "malformed evals.json",
                ["--evals-json", str(evals_malformed)],
                1,
                ["FAIL (blocking)"],
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

    print("PASS: all 5 fixture cases behaved as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
