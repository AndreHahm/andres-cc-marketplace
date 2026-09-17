#!/usr/bin/env python3
"""Persisted smoke test for context-window-analysis: this skill has no scripts/ helper
(pure model-applied guidance + a fixed report template), so the meaningful checks are
structural -- frontmatter validity, the report template/examples reference link (moved
out of SKILL.md by the 2026-09-17 R18 fix), and the documented Quality Gate about
Option 4's real session-kit reference."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
EXAMPLES_MD = SKILL_DIR / "references" / "context-window-examples.md"


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


def check_skill_md_links_the_examples_reference():
    # After the R18 fix (2026-09-17), the report template + worked examples live in
    # references/context-window-examples.md, not inline -- SKILL.md must still point
    # readers at it from Step 3.
    text = SKILL_MD.read_text(encoding="utf-8")
    if "references/context-window-examples.md" not in text:
        return False, "SKILL.md no longer points at references/context-window-examples.md"
    if not EXAMPLES_MD.exists():
        return False, "references/context-window-examples.md does not exist on disk"
    return True, "SKILL.md correctly points at the real references/context-window-examples.md"


def check_option4_names_real_session_kit_skill():
    # Quality gate: "Option 4 always names session-kit's real session-handoff skill
    # (trigger phrase, not a command) and its real .claude/handoffs/ storage location."
    # Lives in references/context-window-examples.md since the R18 fix moved it there.
    text = EXAMPLES_MD.read_text(encoding="utf-8")
    option4_idx = text.find("Option 4")
    if option4_idx == -1:
        return False, "Option 4 section not found in references/context-window-examples.md"
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


def check_skill_md_has_no_oversized_blocks():
    # After the R18 fix, SKILL.md itself must carry no ```text block over the
    # rulebook's 20-line weak-warning threshold -- everything that size moved to
    # references/context-window-examples.md.
    text = SKILL_MD.read_text(encoding="utf-8")
    fenced_blocks = re.findall(r"```text\n(.*?)```", text, re.DOTALL)
    oversized = [b for b in fenced_blocks if b.count("\n") > 20]
    if oversized:
        return False, f"SKILL.md still has {len(oversized)} oversized block(s) post-R18-fix"
    return True, f"SKILL.md has {len(fenced_blocks)} fenced text block(s), none oversized"


def check_examples_reference_has_no_oversized_blocks():
    # Regression guard for the 2026-09-17 R18 finding: the first extraction moved the
    # oversized blocks into this reference file without actually splitting them (a 40-line
    # single fence), which the original version of this check couldn't catch since it only
    # ever looked at SKILL.md. Every block here must now be <=20 lines (Weak-Warning tier
    # at worst) -- none in the Warning (>20) or Critical (>30) tier.
    text = EXAMPLES_MD.read_text(encoding="utf-8")
    fenced_blocks = re.findall(r"```text\n(.*?)```", text, re.DOTALL)
    if not fenced_blocks:
        return False, "no fenced text blocks found in references/context-window-examples.md at all"
    oversized = [b for b in fenced_blocks if b.count("\n") > 20]
    if oversized:
        sizes = [b.count("\n") for b in oversized]
        return False, f"{len(oversized)} block(s) over the 20-line threshold: {sizes}"
    return True, f"all {len(fenced_blocks)} block(s) in the reference file are <=20 lines"


def check_health_thresholds_table_is_ordered():
    # Regression guard for the 2026-09-17 consistency fix: this table's WARNING/CRITICAL
    # boundaries must match context-monitor.py's real THRESHOLD_WARN/THRESHOLD_CRITICAL
    # constants exactly, not an independently-invented pair of numbers -- that's exactly
    # the drift consistency-reviewer found (this table used to say 75/85, the real hook
    # used 80/90, producing contradictory advice for the same real percentage).
    monitor_py = SKILL_DIR.parent.parent / "scripts" / "context-monitor.py"
    monitor_text = monitor_py.read_text(encoding="utf-8")
    warn_match = re.search(r"THRESHOLD_WARN\s*=\s*(\d+)", monitor_text)
    critical_match = re.search(r"THRESHOLD_CRITICAL\s*=\s*(\d+)", monitor_text)
    if not warn_match or not critical_match:
        return False, "could not find THRESHOLD_WARN/THRESHOLD_CRITICAL in context-monitor.py"
    warn, critical = warn_match.group(1), critical_match.group(1)

    text = SKILL_MD.read_text(encoding="utf-8")
    if f"| {warn}-<{critical}%" not in text:
        return (
            False,
            f"WARNING row does not match context-monitor.py's real {warn}-<{critical}% band",
        )
    if f"| >= {critical}%" not in text:
        return (
            False,
            f"CRITICAL row does not match context-monitor.py's real >= {critical}% boundary",
        )
    return True, f"WARNING/CRITICAL boundaries ({warn}/{critical}) match context-monitor.py exactly"


CHECKS = [
    check_frontmatter,
    check_skill_md_links_the_examples_reference,
    check_option4_names_real_session_kit_skill,
    check_skill_md_has_no_oversized_blocks,
    check_examples_reference_has_no_oversized_blocks,
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
