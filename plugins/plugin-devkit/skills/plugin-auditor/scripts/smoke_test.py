#!/usr/bin/env python3
"""Persisted smoke test for plugin-auditor: frontmatter validity, referenced-file
existence, and Bash-scope grant consistency between the body and allowed-tools."""
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
    text = SKILL_MD.read_text(encoding="utf-8")
    missing = []
    for match in re.finditer(r"`(references/[\w.-]+\.md|scripts/[\w./-]+)`", text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Only "scoped `Bash(...)`" counts as a real invocation instruction — this codebase's
    # consistent phrasing for "run this via the scoped Bash(...) tool". A bare `Bash(...)`
    # mention elsewhere (e.g. an illustrative example of a bad grant in a test scenario)
    # is not an instruction to invoke it and must not be flagged as an unmet grant.
    # references/*.md is scanned too — a grant can be invoked entirely from a reference
    # file (e.g. codex-backend.md), not just SKILL.md's own body.
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter, body = text[:header_end], text[header_end:]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    granted = set(re.findall(r"Bash\([^)]*\)", fm_line_match.group(1))) if fm_line_match else set()
    referenced = set(re.findall(r"scoped `(Bash\([^)]*\))", body))
    for ref_file in sorted((SKILL_DIR / "references").glob("*.md")):
        referenced |= set(re.findall(r"scoped `(Bash\([^)]*\))", ref_file.read_text(encoding="utf-8")))
    missing = referenced - granted
    if missing:
        return False, "body/references invoke Bash scope(s) missing from allowed-tools: " + ", ".join(sorted(missing))
    return True, "every scoped Bash invocation in the body/references is granted"


CHECKS = [check_frontmatter, check_referenced_files, check_bash_grants]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
