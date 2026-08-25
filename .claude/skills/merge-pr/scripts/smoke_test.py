#!/usr/bin/env python3
"""Persisted smoke test for merge-pr: frontmatter validity, referenced-file
existence, Bash-scope grant usage, step-header sequencing, step 7's
remote-branch-deletion verification fallback, and step 5's unconditional
worktree branch-delete note -- structural checks only, since this is a
conversational, AskUserQuestion-driven skill with no executable logic of its
own to simulate."""

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


def check_referenced_files():
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = r"`(references/[\w.-]+\.md)`"
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.*/${}-]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    unused = [cmd for cmd in granted_cmds if not re.search(re.escape(cmd.split(" ")[0]), body)]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def check_step_sequence():
    # Scoped to the "## Instructions" section only -- other sections (e.g. "Testing &
    # Validation") legitimately restart their own numbered lists for unrelated scenarios,
    # which a whole-file scan would wrongly flag as non-sequential.
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return True, "no '## Instructions' section found (skip)"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. \*\*", section, re.MULTILINE)]
    if not numbers:
        return True, "no numbered steps found (skip)"
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        return False, f"step numbering not sequential: found {numbers}, expected {expected}"
    return True, "step headers sequential"


def _get_step_text(number):
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return None
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    step_start = re.search(rf"^{number}\. \*\*", section, re.MULTILINE)
    if not step_start:
        return None
    next_step = re.search(r"^\d+\. \*\*\b", section[step_start.end() :], re.MULTILINE)
    step_end = step_start.end() + next_step.start() if next_step else len(section)
    return section[step_start.start() : step_end]


def check_step7_remote_delete_fallback():
    step7 = _get_step_text(7)
    if step7 is None:
        return False, "step 7 ('## Instructions') not found"
    if "git ls-remote --heads origin" not in step7:
        return (
            False,
            "step 7 doesn't verify remote branch deletion with git ls-remote --heads origin",
        )
    if "gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>" not in step7:
        return (
            False,
            "step 7's ls-remote fallback doesn't complete deletion via the documented gh api path",
        )
    if "finishing-work" not in step7 or "1.5" not in step7:
        return (
            False,
            "step 7 doesn't cite finishing-work step 1.5 as the origin of this fallback (R20)",
        )
    return (
        True,
        "step 7 verifies remote branch deletion, falls back to gh api DELETE (finishing-work 1.5)",
    )


def check_step7_skips_delete_fallback_for_fork_prs():
    step1 = _get_step_text(1)
    step7 = _get_step_text(7)
    if step1 is None or step7 is None:
        return False, "step 1 or step 7 ('## Instructions') not found"
    if "isCrossRepository" not in step1:
        return False, "step 1 doesn't resolve isCrossRepository via gh pr view"
    if "isCrossRepository" not in step7:
        return (
            False,
            "step 7's remote-branch-deletion fallback doesn't gate on isCrossRepository "
            "-- a fork PR's branch could be misread as living in this repo",
        )
    return True, "step 7's remote-branch-deletion fallback is gated on isCrossRepository"


def check_headrefname_validated_before_first_use():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return False, "'## Instructions' section not found"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    validation_pos = section.find(r"^[A-Za-z0-9._/-]+$")
    if validation_pos == -1:
        return False, "headRefName regex validation string not found anywhere in Instructions"
    first_use_pos = section.find("git ls-remote --heads origin")
    if first_use_pos == -1:
        return False, "git ls-remote --heads origin not found anywhere in Instructions"
    if validation_pos > first_use_pos:
        return (
            False,
            "headRefName validation appears AFTER its first use (git ls-remote) -- validate at "
            "the source (step 1) before any use, not just before the later DELETE call",
        )
    return True, "headRefName is validated before its first shell interpolation (git ls-remote)"


def check_step5_worktree_note():
    step5 = _get_step_text(5)
    if step5 is None:
        return False, "step 5 ('## Instructions') not found"
    if "already used by worktree" not in step5:
        return False, "step 5 doesn't note the possible worktree branch-delete git error"
    if "merge_auto_delete_branch" in step5:
        return (
            False,
            "step 5's worktree note looks gated on merge_auto_delete_branch (unread until step 6)",
        )
    return True, "step 5's worktree branch-delete note is present and unconditional"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_step_sequence,
    check_step7_remote_delete_fallback,
    check_step7_skips_delete_fallback_for_fork_prs,
    check_headrefname_validated_before_first_use,
    check_step5_worktree_note,
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
