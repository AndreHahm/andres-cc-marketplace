#!/usr/bin/env python3
"""Persisted smoke test for commit: frontmatter validity, Bash-scope grant
usage, and step-header sequencing within the '## Instructions' section --
structural checks only, since this is a conversational, AskUserQuestion-driven
skill with no executable logic of its own to simulate."""
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
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(sorted(set(unused)))
    return True, "every granted Bash command is invoked somewhere in the body"


def check_step_sequence():
    # Scoped to the "## Instructions" section only -- "## Branch Naming Convention" and
    # other later sections legitimately restart their own numbered lists for unrelated
    # workflow descriptions, which a whole-file scan would wrongly flag as non-sequential.
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return True, "no '## Instructions' section found (skip)"
    end = text.find("\n## ", start + 1)
    section = text[start:end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", section, re.MULTILINE)]
    if not numbers:
        return True, "no numbered steps found (skip)"
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        return False, f"step numbering not sequential: found {numbers}, expected {expected}"
    return True, "step headers sequential"


CHECKS = [check_frontmatter, check_bash_grants, check_step_sequence]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
