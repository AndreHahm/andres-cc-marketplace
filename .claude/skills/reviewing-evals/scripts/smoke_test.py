#!/usr/bin/env python3
"""Persisted smoke test for reviewing-evals: frontmatter validity, Bash-grant
usage, bundled-script existence (check_evals.py / test_check_evals.py), and
Pre-Review Self-Audit check-header sequencing -- structural checks only, since
this is a conversational, instruction-driven skill whose executable logic
lives in its own bundled scripts (which own their own correctness via
test_check_evals.py)."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _frontmatter_and_body():
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    return text[:header_end], text[header_end:], text


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if not re.search(r"^name:", fm, re.MULTILINE) or not re.search(
        r"^description:", fm, re.MULTILINE
    ):
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def _granted_bash_tokens(frontmatter):
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return None
    bash_blocks = re.findall(r"Bash\(([^)]+)\)", fm_line_match.group(1))
    tokens = []
    for block in bash_blocks:
        for token in block.split():
            tokens.append(token.split(":")[0])
    return tokens


def check_bash_grants():
    frontmatter, body, _ = _frontmatter_and_body()
    tokens = _granted_bash_tokens(frontmatter)
    if tokens is None:
        return True, "no allowed-tools line found (skip)"
    if not tokens:
        return True, "no Bash(...) grants found (skip)"
    unused = []
    for t in tokens:
        needle = t.split("/")[-1] if "/" in t else t
        if not re.search(re.escape(needle), body):
            unused.append(t)
    if unused:
        return False, "Bash grant(s) never referenced anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, f"all {len(set(tokens))} distinct Bash grant(s) referenced in the body"


def check_bundled_scripts_exist():
    _, _, text = _frontmatter_and_body()
    refs = set(re.findall(r"reviewing-evals/scripts/([\w.]+\.py)", text))
    if not refs:
        return True, "no skills/reviewing-evals/scripts/*.py references found in body (skip)"
    missing = [r for r in refs if not (SKILL_DIR / "scripts" / r).is_file()]
    if missing:
        return False, "referenced bundled script(s) do not exist: " + ", ".join(sorted(missing))
    return True, f"all {len(refs)} referenced bundled script(s) exist"


def check_audit_check_sequence():
    _, _, text = _frontmatter_and_body()
    start = text.find("## Pre-Review Self-Audit")
    if start == -1:
        return True, "no '## Pre-Review Self-Audit' section found (skip)"
    end = text.find("\n## ", start + 10)
    section = text[start : end if end != -1 else None]
    numbers = [int(n) for n in re.findall(r"^### (\d+)\. ", section, re.MULTILINE)]
    if not numbers:
        return True, "no numbered '### N. ' check headers found (skip)"
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        return False, f"Check numbering not sequential: found {numbers}, expected {expected}"
    return True, "Check headers sequential"


CHECKS = [
    check_frontmatter,
    check_bash_grants,
    check_bundled_scripts_exist,
    check_audit_check_sequence,
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
