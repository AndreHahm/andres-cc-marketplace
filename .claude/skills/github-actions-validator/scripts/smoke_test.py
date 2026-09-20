#!/usr/bin/env python3
"""Persisted smoke test for github-actions-validator: SKILL.md frontmatter
validity, plus real --lint-only invocations of scripts/validate_workflow.py
against the skill's own bundled examples/with-errors.yml (must be flagged)
and examples/valid-ci.yml (must run to completion without crashing).

No PYTHONIOENCODING override is set for the subprocess: validate_workflow.py's
own log helpers print unicode glyphs (e.g. "✗"), and main() now reconfigures
sys.stdout/sys.stderr to UTF-8 itself so this doesn't depend on the caller's
console codepage -- running the subprocess with the plain inherited
environment is what actually exercises that self-healing, rather than
papering over a regression with an env override of our own. This parent
process still decodes the child's captured bytes explicitly as UTF-8 (see
_run_lint_only) -- that's a separate, decode-side concern from the child's own
encoding self-heal above, since Python's default text-mode decode otherwise
follows the parent's own locale, not the child's.
"""

import pathlib
import subprocess  # nosec B404 -- only used to invoke this skill's own bundled script
import sys

import yaml

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "validate_workflow.py"
EXAMPLES_DIR = SKILL_DIR / "examples"


def _parse_frontmatter_fields(fm: str) -> dict:
    # A real YAML parser, not a naive `:`-split -- a line-split parser accepts malformed YAML
    # (e.g. an unterminated quoted description) as long as the split still produces a non-empty
    # value, which silently defeats the "frontmatter missing/invalid" checks below.
    try:
        parsed = yaml.safe_load(fm)
    except yaml.YAMLError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): ("" if v is None else str(v)) for k, v in parsed.items()}


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    fields = _parse_frontmatter_fields(fm)
    if not fields.get("name"):
        return False, "frontmatter missing non-empty 'name' field"
    if not fields.get("description"):
        return False, "frontmatter missing non-empty 'description' field"
    if fields["name"] != SKILL_DIR.name:
        return (
            False,
            f"frontmatter name '{fields['name']}' does not match directory '{SKILL_DIR.name}'",
        )
    return True, "frontmatter present, closed, and name matches directory"


def check_script_and_examples_exist():
    missing = []
    if not SCRIPT.is_file():
        missing.append(str(SCRIPT))
    for name in ("valid-ci.yml", "with-errors.yml"):
        if not (EXAMPLES_DIR / name).is_file():
            missing.append(str(EXAMPLES_DIR / name))
    if missing:
        return False, "missing file(s): " + ", ".join(missing)
    return True, "script and both documented example files exist"


def _run_lint_only(target: pathlib.Path):
    # validate_workflow.py's own stdout is UTF-8 (it reconfigures itself), but this parent's
    # subprocess.run(text=True) still decodes with locale.getpreferredencoding(False) unless told
    # otherwise -- on a non-UTF-8 Windows console that silently mojibakes the captured ✓/✗
    # diagnostics instead of raising, the same decode-side gap already fixed inside
    # validate_workflow.py's own actionlint/act subprocess calls.
    # Fixed argv (sys.executable + this skill's own script path resolved from __file__,
    # "--lint-only", and one of two hardcoded example filenames -- no shell, no untrusted input)
    # -- static analysis can't see that SCRIPT/target are constants.
    return subprocess.run(  # nosemgrep
        [sys.executable, str(SCRIPT), "--lint-only", str(target)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )  # nosec B603


def check_with_errors_detected():
    if not SCRIPT.is_file():
        return False, "scripts/validate_workflow.py missing -- skipping execution check"

    proc = _run_lint_only(EXAMPLES_DIR / "with-errors.yml")
    combined = proc.stdout + proc.stderr

    if "Traceback (most recent call last)" in combined:
        return (
            False,
            f"validate_workflow.py crashed with an unhandled exception:\n{combined[-800:]}",
        )
    if proc.returncode == 0:
        return False, "expected a nonzero exit for examples/with-errors.yml, got 0"
    if "actionlint" not in combined.lower():
        return False, "expected actionlint to be invoked and mentioned in output"

    return (
        True,
        "examples/with-errors.yml correctly flagged (nonzero exit, actionlint output present)",
    )


def check_valid_ci_runs_without_crashing():
    if not SCRIPT.is_file():
        return False, "scripts/validate_workflow.py missing -- skipping execution check"

    proc = _run_lint_only(EXAMPLES_DIR / "valid-ci.yml")
    combined = proc.stdout + proc.stderr

    if "Traceback (most recent call last)" in combined:
        return (
            False,
            f"validate_workflow.py crashed with an unhandled exception:\n{combined[-800:]}",
        )
    if "Validation Summary" not in combined:
        return False, "expected a 'Validation Summary' section in output"

    return (
        True,
        "examples/valid-ci.yml ran to completion with a printed Validation Summary (no crash)",
    )


CHECKS = [
    check_frontmatter,
    check_script_and_examples_exist,
    check_with_errors_detected,
    check_valid_ci_runs_without_crashing,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
