#!/usr/bin/env python3
"""Persisted smoke test for plugin-ideation: frontmatter validity,
referenced-file existence, and Bash-scope grant consistency."""

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
    if not re.search(r"^name:", fm, re.MULTILINE) or not re.search(
        r"^description:", fm, re.MULTILINE
    ):
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def check_referenced_files():
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = r"`(references/[\w.-]+\.md|workflows/[\w.-]+\.md|scripts/[\w./-]+)`"
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # This skill's prose never uses the "scoped `Bash(...)`" phrasing (it cites the date
    # command in plain shorthand instead), so the meaningful check here is: does each
    # granted Bash(<cmd>:*) scope's base <cmd> word actually appear somewhere in the body?
    # An unused grant is an R6 least-privilege smell even without exact-string phrasing.
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    value = fm_line_match.group(1).strip()
    if value in (">-", ">", "|", "|-", "|+", ">+"):
        # YAML block scalar: the real value is on subsequent, more-indented lines.
        block_lines = []
        for line in frontmatter[fm_line_match.end() :].splitlines():
            if line.strip() == "":
                continue
            if line[:1] in (" ", "\t"):
                block_lines.append(line)
            else:
                break
        value = " ".join(block_lines)
    granted_cmds = re.findall(r"Bash\(([\w.*/ -]+?)(?::|\))", value)
    granted_cmds = [c.removeprefix("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    workflows_dir = SKILL_DIR / "workflows"
    if workflows_dir.exists():
        for wf in sorted(workflows_dir.glob("*.md")):
            body += "\n" + wf.read_text(encoding="utf-8")

    # Require the command to appear as the start of a backtick-wrapped inline code span
    # (e.g. `date -u ...`) -- the actual documented-invocation convention this skill's body
    # uses -- not just anywhere as a bare word, which would pass on an unrelated prose
    # mention of the same word (e.g. a grant for `Bash(date:*)` "passing" because the body
    # merely discusses timestamps).
    unused = [cmd for cmd in granted_cmds if not re.search(rf"`{re.escape(cmd)}\b", body)]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


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
