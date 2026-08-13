#!/usr/bin/env python3
"""Persisted smoke test for plugin-lifecycle-downstream: frontmatter validity,
referenced-file existence, Bash-scope grant consistency, phase-header
sequencing across workflows/*.md, and report-fixture schema conformance
(field completeness, optional-gate enum representation) via
plugin-rulebook's validate_evidence.py. The phase-header check exists because
a phase-insertion edit (e.g. adding a new phase between two existing ones) is
exactly the kind of change that silently leaves a stale "Phase N"
cross-reference elsewhere; the fixture check exists because a report/manifest
shape drifting from evidence-schema.md (a missing required field, an invalid
optional-gate value) has no other mechanical catch in this skill's own tree."""
import re
import subprocess
import sys
import pathlib

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
FIXTURES_DIR = SKILL_DIR / "scripts" / "fixtures"

# Fixture filename -> (evidence shape, expected to be schema-valid).
# One deliberately broken fixture per axis this check exists to catch:
# report_missing_field (a required Report Revision field absent) and
# manifest_invalid_optional_gate (an optional-phase field set to a
# non-enum value) must both come back invalid, or this check is not
# actually catching anything.
FIXTURE_CASES = {
    "manifest_valid.yaml": ("manifest", True),
    "manifest_invalid_optional_gate.yaml": ("manifest", False),
    "report_valid.yaml": ("report", True),
    "report_missing_field.yaml": ("report", False),
}


def _find_validate_evidence_script():
    for parent in SKILL_DIR.parents:
        candidate = parent / "skills" / "plugin-rulebook" / "scripts" / "validate_evidence.py"
        if candidate.exists():
            return candidate
        if parent.name == "plugin-devkit":
            break
    return None


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if "name:" not in fm or "description:" not in fm:
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def check_referenced_files():
    # `test-agent-trigger.sh`/`test-hook.sh` are excluded: this skill's prose splits the
    # owning plugin name and the script path across separate backtick spans
    # ("`agent-development`'s `scripts/test-agent-trigger.sh`"), so a bare
    # `scripts/test-agent-trigger.sh` match here is a cross-plugin reference, not a path
    # relative to this skill — already covered by check_bash_grants' full-path check instead.
    #
    # Scans SKILL.md and every workflows/*.md file (matching check_bash_grants' and
    # check_phase_sequence's scope), and matches both backtick-quoted paths and
    # markdown-link-style references (`[text](path)`), including bare root-level links
    # (e.g. `[X](FILENAME.md)`) — a cutover-time finding: this check originally only
    # matched references/workflows/scripts-prefixed link targets, so a broken root-level
    # link (`[REQUIRED_CHANGES.md](REQUIRED_CHANGES.md)`, pointing at a gitignored
    # planning doc that was never meant to ship) passed silently.
    backtick_pattern = r"`(references/[\w.-]+\.md|workflows/[\w.-]+\.md|scripts/(?!test-agent-trigger\.sh|test-hook\.sh)[\w./-]+)`"
    link_pattern = r"\]\(((?:references/|workflows/)?[\w.-]+\.md)\)"
    missing = []
    files_to_scan = [SKILL_MD] + sorted((SKILL_DIR / "workflows").glob("*.md"))
    for f in files_to_scan:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for pattern in (backtick_pattern, link_pattern):
            for match in re.finditer(pattern, text):
                path = SKILL_DIR / match.group(1)
                if not path.exists():
                    missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Only "scoped `Bash(...)`" counts as a real invocation instruction — a bare mention
    # elsewhere (e.g. an illustrative example) is not an instruction to invoke it. Checked
    # across SKILL.md and every workflows/*.md file, since real invocations live in both.
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    granted = set(re.findall(r"Bash\([^)]*\)", fm_line_match.group(1))) if fm_line_match else set()

    referenced = set(re.findall(r"scoped `(Bash\([^)]*\))", fm_text[header_end:]))
    for wf in sorted((SKILL_DIR / "workflows").glob("*.md")):
        referenced |= set(re.findall(r"scoped `(Bash\([^)]*\))", wf.read_text(encoding="utf-8")))

    missing = referenced - granted
    if missing:
        return False, "body invokes Bash scope(s) missing from allowed-tools: " + ", ".join(sorted(missing))
    return True, "every scoped Bash invocation is granted"


def check_phase_sequence():
    workflows_dir = SKILL_DIR / "workflows"
    if not workflows_dir.exists():
        return True, "no workflows/ directory (skip)"
    problems = []
    for wf in sorted(workflows_dir.glob("*.md")):
        text = wf.read_text(encoding="utf-8")
        numbers = [int(n) for n in re.findall(r"^##+ (?:Phase|Step|Service) (\d+):", text, re.MULTILINE)]
        if not numbers:
            continue
        expected = list(range(1, 13))
        if numbers != expected:
            problems.append(f"{wf.name}: found {numbers}, expected exactly {expected}")
    if problems:
        return False, "phase/step numbering not sequential: " + "; ".join(problems)
    return True, "phase/step headers sequential in every workflow file checked"


def check_report_fixtures():
    validator = _find_validate_evidence_script()
    if validator is None:
        return False, "could not locate plugin-rulebook/scripts/validate_evidence.py"
    if not FIXTURES_DIR.exists():
        return False, "scripts/fixtures/ directory is missing"

    problems = []
    for filename, (shape, expect_valid) in FIXTURE_CASES.items():
        fixture_path = FIXTURES_DIR / filename
        if not fixture_path.exists():
            problems.append(f"{filename}: fixture file missing")
            continue
        result = subprocess.run(
            [sys.executable, str(validator), shape, str(fixture_path)],
            capture_output=True,
            text=True,
        )
        is_valid = result.returncode == 0
        if is_valid != expect_valid:
            label = "valid" if expect_valid else "invalid"
            problems.append(
                f"{filename}: expected {label}, got "
                f"{'valid' if is_valid else 'invalid'} ({result.stdout.strip() or result.stderr.strip()})"
            )
    if problems:
        return False, "report/manifest fixture(s) failed: " + "; ".join(problems)
    return True, f"all {len(FIXTURE_CASES)} report/manifest fixtures matched their expected validity"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_phase_sequence,
    check_report_fixtures,
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
