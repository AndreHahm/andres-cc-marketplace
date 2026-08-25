#!/usr/bin/env python3
"""Persisted smoke test for plugin-grader: frontmatter validity, referenced-file
existence, and Bash-scope grant consistency between the body and allowed-tools."""

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
    missing = []
    for match in re.finditer(r"`(references/[\w.-]+\.md|scripts/[\w./-]+|assets/[\w.-]+)`", text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Real invocation instructions in this body live as a literal command line inside a
    # fenced ```bash block (e.g. "python scripts/compute_score.py <input.json>") -- not as
    # a bare `Bash(...)` mention, which never actually appears verbatim in the body and
    # made the previous version of this check a silent no-op (referenced was always empty).
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter, body = text[:header_end], text[header_end:]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    granted_prefixes = (
        [
            g.rsplit(":", 1)[0].strip()
            for g in re.findall(r"Bash\(([^)]*)\)", fm_line_match.group(1))
        ]
        if fm_line_match
        else []
    )
    invoked = set()
    for block in re.findall(r"```bash\n(.*?)```", body, re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            invoked.add(" ".join(tokens[:2]) if len(tokens) > 1 else tokens[0])
    uncovered = [cmd for cmd in invoked if not any(cmd.startswith(p) for p in granted_prefixes)]
    if uncovered:
        return False, "body invokes command(s) not covered by any granted Bash scope: " + ", ".join(
            sorted(uncovered)
        )
    if not invoked:
        return True, "no shell commands found in fenced bash blocks (nothing to check)"
    return True, f"every invoked command ({len(invoked)}) is covered by a granted Bash scope"


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
