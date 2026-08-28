#!/usr/bin/env python3
"""Persisted smoke test for github-issue-lifecycle: frontmatter validity,
referenced-file existence, and Bash-scope grant consistency across SKILL.md
plus every workflows/*.md and references/*.md file. Adapted from
plugin-lifecycle-upstream's own scripts/smoke_test.py, minus its
phase-sequencing checks -- this skill's workflow files use independent
"## Step N:" headers per file, not a single shared "Phase N" sequence
spanning files, so there is no cross-file sequence to validate here."""

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
    # Scans SKILL.md plus every workflows/*.md and references/*.md file -- a workflow file
    # can cross-reference a references/*.md file (or vice versa) without SKILL.md itself
    # ever repeating that link, so checking SKILL.md alone would miss a broken cross-link
    # introduced entirely within workflows/ or references/.
    pattern = r"`(references/[\w.-]+\.md|workflows/[\w.-]+\.md|scripts/[\w./-]+)`"
    texts = [SKILL_MD.read_text(encoding="utf-8")]
    for sub in ("workflows", "references"):
        d = SKILL_DIR / sub
        if d.is_dir():
            texts.extend(f.read_text(encoding="utf-8") for f in sorted(d.glob("*.md")))

    missing = []
    for text in texts:
        for match in re.finditer(pattern, text):
            path = SKILL_DIR / match.group(1)
            if not path.exists():
                missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Only "scoped `Bash(...)`" counts as a real invocation instruction -- a bare mention
    # elsewhere is not an instruction to invoke it. Checked across SKILL.md and every
    # workflows/*.md and references/*.md file, since real invocations live in all three.
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    value = ""
    if fm_line_match:
        value = fm_line_match.group(1).strip()
        if value in (">-", ">", "|", "|-", "|+", ">+"):
            # YAML block scalar: the real value is on subsequent, more-indented lines.
            block_lines = []
            for line in frontmatter[fm_line_match.end():].splitlines():
                if line.strip() == "":
                    continue
                if line[:1] in (" ", "\t"):
                    block_lines.append(line)
                else:
                    break
            value = " ".join(block_lines)
    granted = set(re.findall(r"Bash\([^)]*\)", value))

    search_text = fm_text[header_end:]
    for sub in ("workflows", "references"):
        d = SKILL_DIR / sub
        if d.is_dir():
            for f in sorted(d.glob("*.md")):
                search_text += "\n" + f.read_text(encoding="utf-8")

    # Body text here uses bare `gh ...`/`gh api ...` commands, not the literal
    # `Bash(...)` scope syntax -- match on the underlying command instead of requiring
    # the frontmatter's own scope-string spelling to appear verbatim in prose.
    unused = []
    for grant in sorted(granted):
        cmd = grant[len("Bash("):-1].strip()
        if cmd.endswith("*"):
            cmd = cmd[:-1]
        cmd = cmd.rstrip(":").strip()
        # Glob wildcards (`*`, standing in for a repo owner/name or issue number
        # segment) must match any non-whitespace run in the body's real example
        # commands, not a literal asterisk -- escape everything else first, then
        # swap the escaped wildcard marker back to a real regex wildcard.
        cmd_pattern = re.escape(cmd).replace(r"\*", r"[^\s]*").replace(r"\ ", r"\s+")
        if not re.search(cmd_pattern, search_text):
            unused.append(grant)
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the skill's own files: " + ", ".join(
            unused
        )
    return True, "every granted Bash command is invoked somewhere in the skill's own files"


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
