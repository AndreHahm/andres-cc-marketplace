#!/usr/bin/env python3
"""Persisted smoke test for skill-development: frontmatter validity, referenced-file
existence, and Bash-scope grant usage consistency."""
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
    # This skill's body cites paths both as bare `references/foo.md` and as
    # `${CLAUDE_SKILL_DIR}/references/foo.md` — both forms must be checked, or the
    # majority of this file's real references silently go unverified.
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = r"`(?:\$\{CLAUDE_SKILL_DIR\}/)?(references/[\w.-]+\.md|scripts/[\w./-]+)`"
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # This skill doesn't use the "scoped `Bash(...)`" invocation phrasing the lifecycle
    # skills use — its body cites commands as literal invocation examples instead
    # (e.g. "python -m scripts.aggregate_benchmark", "mkdir -p ..."). So the meaningful
    # check here is: does each granted Bash(<cmd>:*) scope's <cmd> actually appear as a
    # word-boundary command mention in the body? An unused grant is an R6 least-privilege
    # smell even when nothing in the body's own phrasing names the grant explicitly.
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter, body = text[:header_end], text[header_end:]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.-]+):", fm_line_match.group(1))
    unused = [cmd for cmd in granted_cmds if not re.search(rf"\b{re.escape(cmd)}\b", body)]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(sorted(set(unused)))
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
