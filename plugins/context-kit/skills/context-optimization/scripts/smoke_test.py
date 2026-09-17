#!/usr/bin/env python3
"""Persisted smoke test for context-optimization: this skill has no scripts/ helper
(pure model-applied guidance), so the meaningful checks are structural -- frontmatter
validity and the documented Quality Gate that it never duplicates context-engineering's
full four-operation framework, only the "Select" tactics specific to this skill."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SIBLINGS_DIR = SKILL_DIR.parent


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


def check_references_context_engineering():
    text = SKILL_MD.read_text(encoding="utf-8")
    if "`context-engineering`" not in text:
        return False, "does not reference context-engineering by its exact identifier"
    if not (SIBLINGS_DIR / "context-engineering" / "SKILL.md").exists():
        return False, "referenced context-engineering skill does not exist on disk"
    return True, "correctly references the real context-engineering sibling skill"


def check_never_duplicates_full_four_operation_framework():
    # Quality gate: "Never duplicates context-engineering's full Write/Select/
    # Compress/Isolate framework -- only the 'Select' tactics specific to @
    # mentions and semantic search." Write/Compress/Isolate as operation headers
    # must not appear here at all -- only Select-adjacent content is in scope.
    text = SKILL_MD.read_text(encoding="utf-8")
    operation_headers = re.findall(r"^##\s*(Write|Compress|Isolate)\b", text, re.MULTILINE)
    if operation_headers:
        return (
            False,
            f"duplicates operation header(s) owned by context-engineering: {operation_headers}",
        )
    return True, "never restates Write/Compress/Isolate as its own operation headers"


def check_references_context_degradation_for_active_failures():
    text = SKILL_MD.read_text(encoding="utf-8")
    if "`context-degradation`" not in text:
        return (
            False,
            "does not defer active-failure diagnosis to context-degradation by exact identifier",
        )
    return True, "correctly defers active-failure diagnosis to context-degradation"


CHECKS = [
    check_frontmatter,
    check_references_context_engineering,
    check_never_duplicates_full_four_operation_framework,
    check_references_context_degradation_for_active_failures,
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
