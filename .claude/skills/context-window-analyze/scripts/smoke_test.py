#!/usr/bin/env python3
"""Persisted smoke test for context-window-analyze: this skill has no scripts/ helper
(pure model-applied guidance + a fixed report template), so the meaningful checks are
structural -- frontmatter validity and the documented Quality Gates about Option 4's
real session-kit reference and the R18 oversized-block exception notes."""

import pathlib
import re
import sys

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


def check_option4_names_real_session_kit_skill():
    # Quality gate: "Option 4 always names session-kit's real session-handoff skill
    # (trigger phrase, not a command) and its real .claude/handoffs/ storage location."
    text = SKILL_MD.read_text(encoding="utf-8")
    option4_idx = text.find("Option 4")
    if option4_idx == -1:
        return False, "Option 4 section not found"
    option4_section = text[option4_idx : option4_idx + 500]
    if "session-handoff" not in option4_section:
        return False, "Option 4 does not name the real session-handoff skill"
    if ".claude/handoffs/" not in option4_section:
        return False, "Option 4 does not name the real .claude/handoffs/ storage location"
    # Must be described as a trigger phrase, never as a slash command (e.g. no
    # literal "/session-handoff" invocation form).
    if "/session-handoff" in option4_section:
        return False, "Option 4 references session-handoff as if it were a slash command"
    return True, "Option 4 correctly names session-handoff as a trigger phrase, not a command"


def check_every_oversized_block_has_r18_exception_note():
    # Every fenced ```text block over the rulebook's line thresholds must carry its
    # own stated "R18 exception (recorded)" note -- count blocks vs. notes.
    text = SKILL_MD.read_text(encoding="utf-8")
    fenced_blocks = re.findall(r"```text\n(.*?)```", text, re.DOTALL)
    oversized = [b for b in fenced_blocks if b.count("\n") > 20]
    exception_notes = text.count("R18 exception (recorded)")
    if len(oversized) > exception_notes:
        return False, f"{len(oversized)} oversized block(s) but only {exception_notes} R18 note(s)"
    return (
        True,
        f"{len(oversized)} oversized block(s), all covered by R18 notes ({exception_notes} total)",
    )


def check_health_thresholds_table_is_ordered():
    # Sanity check the Context Health Thresholds table's own internal consistency
    # (< 50%, 50-<75%, 75-85%, > 85% -- monotonic, no gaps/overlaps stated wrong).
    text = SKILL_MD.read_text(encoding="utf-8")
    if "| < 50% | HEALTHY" not in text:
        return False, "HEALTHY threshold row missing or reworded unexpectedly"
    if "| > 85% | CRITICAL" not in text:
        return False, "CRITICAL threshold row missing or reworded unexpectedly"
    return True, "Context Health Thresholds table's boundary rows are present as documented"


CHECKS = [
    check_frontmatter,
    check_option4_names_real_session_kit_skill,
    check_every_oversized_block_has_r18_exception_note,
    check_health_thresholds_table_is_ordered,
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
