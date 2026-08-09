#!/usr/bin/env python3
"""Persisted smoke test for plugin-lifecycle-maintenance: frontmatter validity,
referenced-file existence, Bash-scope grant consistency, and phase/step/service-header
sequencing across workflows/*.md — this last check exists because a phase-insertion
edit (e.g. adding a new step between two existing ones) is exactly the kind of
change that silently leaves a stale "Step N" cross-reference elsewhere."""
import re
import sys
import pathlib

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


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
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = r"`(references/[\w.-]+\.md|workflows/[\w.-]+\.md|scripts/(?!test-agent-trigger\.sh|test-hook\.sh)[\w./-]+)`"
    missing = []
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
    # This skill's 3 workflow files each number independently (a fresh "Step 1"/"Service 1"
    # per file, not a shared global sequence) — checked per file, not merged across files.
    workflows_dir = SKILL_DIR / "workflows"
    if not workflows_dir.exists():
        return True, "no workflows/ directory (skip)"
    problems = []
    for wf in sorted(workflows_dir.glob("*.md")):
        text = wf.read_text(encoding="utf-8")
        numbers = [int(n) for n in re.findall(r"^##+ (?:Phase|Step|Service) (\d+):", text, re.MULTILINE)]
        if not numbers:
            continue
        expected = list(range(numbers[0], numbers[0] + len(numbers)))
        if numbers != expected:
            problems.append(f"{wf.name}: found {numbers}, expected consecutive {expected}")
    if problems:
        return False, "phase/step numbering not sequential: " + "; ".join(problems)
    return True, "phase/step headers sequential in every workflow file checked"


CHECKS = [check_frontmatter, check_referenced_files, check_bash_grants, check_phase_sequence]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
