#!/usr/bin/env python3
"""Persisted smoke test for context-engineering: this skill has no scripts/ helper
(pure model-applied guidance), so the meaningful checks are structural -- frontmatter
validity, sibling cross-references resolve, and the documented Quality Gates about
canonical-source ownership and cross-skill duplication actually hold against the real
sibling files, not just asserted in prose."""

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


def check_sibling_skills_referenced_exist():
    # Regression guard for a real completeness-reviewer finding (2026-09-18): a hardcoded
    # 3-name alternation only ever covered the siblings named at the time it was written --
    # SKILL.md's own cross-references to context-window-analysis and context-audit grew
    # after that, and the hardcoded set silently never covered either. Derive the checked
    # name set from the real sibling skill directories instead, so a future addition is
    # covered automatically.
    text = SKILL_MD.read_text(encoding="utf-8")
    real_sibling_names = {
        p.parent.name
        for p in SIBLINGS_DIR.glob("*/SKILL.md")
        if p.parent.name != "context-engineering"
    }
    pattern = r"`(" + "|".join(re.escape(name) for name in sorted(real_sibling_names)) + r")`"
    siblings = re.findall(pattern, text)
    missing = [s for s in set(siblings) if not (SIBLINGS_DIR / s / "SKILL.md").exists()]
    if missing:
        return False, f"referenced sibling skill(s) do not exist: {missing}"
    if not siblings:
        return False, "no sibling skill cross-references found at all (expected at least one)"
    return True, f"all referenced sibling skills exist: {sorted(set(siblings))}"


def check_is_sole_canonical_source_for_framework():
    # Quality gate: "No sibling skill restates this skill's own Write/Select/
    # Compress/Isolate framework in full -- this skill is the single canonical
    # source". Regression guard for a real completeness-reviewer finding
    # (2026-09-18): this check previously inspected only context-degradation by
    # name, leaving every other sibling unguarded -- broadened to iterate the
    # real sibling set, matching check_sibling_skills_referenced_exist's own
    # 2026-09-18 fix for the identical hardcoded-set gap.
    real_sibling_names = {
        p.parent.name
        for p in SIBLINGS_DIR.glob("*/SKILL.md")
        if p.parent.name != "context-engineering"
    }
    restating: list[str] = []
    for name in sorted(real_sibling_names):
        sibling_md = (SIBLINGS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        operation_headers = re.findall(
            r"^###?\s*\d*\.?\s*(Write|Select|Compress|Isolate)\s*[—-]", sibling_md, re.MULTILINE
        )
        if operation_headers:
            restating.append(f"{name}: {operation_headers}")
    if restating:
        return False, f"sibling(s) restate operation headers: {restating}"
    return True, f"no sibling in {sorted(real_sibling_names)} restates the four-operation framework"


def check_compress_section_names_strategic_compact():
    # Quality gate: "The Compress section's compaction-strategy table and trigger
    # list always name strategic-compact explicitly where its hooks are the
    # mechanism, never a bare unnamed 'strategic compact' phrase."
    text = SKILL_MD.read_text(encoding="utf-8")
    compress_start = text.find("### 3. Compress")
    isolate_start = text.find("### 4. Isolate")
    if compress_start == -1 or isolate_start == -1:
        return False, "could not locate '### 3. Compress' / '### 4. Isolate' section headers"
    compress_section = text[compress_start:isolate_start]
    if "`strategic-compact`" not in compress_section:
        return False, "Compress section never names strategic-compact by its exact identifier"
    return True, "Compress section correctly names strategic-compact explicitly"


def check_scratchpad_guidance_never_bare_repo_root():
    # Quality gate (found by cross-model review 2026-09-16): the Write operation's
    # scratchpad guidance never presents a bare repo-root filename as the default.
    text = SKILL_MD.read_text(encoding="utf-8")
    write_start = text.find("### 1. Write")
    select_start = text.find("### 2. Select")
    if write_start == -1 or select_start == -1:
        return False, "could not locate '### 1. Write' / '### 2. Select' section headers"
    write_section = text[write_start:select_start]
    if "NOTES.md" in write_section and "never bare at the repo root" not in write_section:
        return (
            False,
            "Write section mentions a scratchpad filename with no 'never bare at repo root' note",
        )
    return (
        True,
        "Write section's scratchpad guidance correctly qualifies against bare repo-root placement",
    )


def check_resume_never_labeled_clean_slate():
    # Quality gate: "The Isolate table never labels /resume as a 'clean slate' --
    # /resume loads the prior session's context back into memory (continuity, not
    # isolation); only a genuinely fresh session (no /resume) is a clean slate."
    # This gate was moved here from context-audit's own checklist (2026-09-17) but,
    # until now, its test coverage was never migrated with it (found by
    # completeness-reviewer, 2026-09-17).
    text = SKILL_MD.read_text(encoding="utf-8")
    isolate_start = text.find("### 4. Isolate")
    if isolate_start == -1:
        return False, "could not locate '### 4. Isolate' section header"
    isolate_section = text[isolate_start : isolate_start + 2000]
    resume_rows = re.findall(r"^\|.*`/resume`.*\|$", isolate_section, re.MULTILINE)
    if not resume_rows:
        return False, "Isolate section has no table row mentioning /resume to check"
    # A row naming bare `/resume` (not qualified with "no") must never pair it with
    # "Clean slate" -- but a row like "Fresh session (no `/resume`)" correctly does,
    # since that row is describing the *absence* of /resume, not /resume itself.
    bad_rows = [
        row
        for row in resume_rows
        if "clean slate" in row.lower() and "no `/resume`" not in row and "no /resume" not in row
    ]
    if bad_rows:
        return False, f"a table row pairs bare /resume with 'clean slate': {bad_rows}"
    if "Clean slate" not in isolate_section:
        return False, "expected a 'Clean slate' row for the no-/resume case, none found"
    return True, "/resume is never labeled a clean slate; only a fresh no-/resume session is"


CHECKS = [
    check_frontmatter,
    check_sibling_skills_referenced_exist,
    check_is_sole_canonical_source_for_framework,
    check_compress_section_names_strategic_compact,
    check_scratchpad_guidance_never_bare_repo_root,
    check_resume_never_labeled_clean_slate,
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
