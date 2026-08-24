#!/usr/bin/env python3
"""Persisted smoke test for workflow-skill-development: frontmatter validity,
Bash-grant usage, Reference-Index table file existence, and Anti-Pattern
table AP-N identifier uniqueness -- structural checks only, since this is a
conversational, reference-driven skill with no executable logic of its own
to simulate."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _frontmatter_and_body():
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    return text[:header_end], text[header_end:], text


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


def _granted_bash_tokens(frontmatter):
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return None, False
    grant_text = fm_line_match.group(1)
    bare_bash = bool(re.search(r"\bBash\b(?!\()", grant_text))
    bash_blocks = re.findall(r"Bash\(([^)]+)\)", grant_text)
    tokens = []
    for block in bash_blocks:
        for token in block.split():
            tokens.append(token.split(":")[0])
    return tokens, bare_bash


def _usage_search_body(body):
    # Exclude the Tool Assignment Quick Reference section, which documents R6's own
    # scoped-Bash example (e.g. "Bash(git:*)") -- a real grant must be used in an actual
    # instruction elsewhere, not merely satisfied by the guidance text that explains the rule.
    start = body.find("## Tool Assignment Quick Reference")
    if start == -1:
        return body
    end = body.find("\n## ", start + 10)
    return body[:start] + body[end if end != -1 else len(body) :]


def check_bash_grants():
    frontmatter, body, _ = _frontmatter_and_body()
    tokens, bare_bash = _granted_bash_tokens(frontmatter)
    if bare_bash:
        return (
            False,
            "bare 'Bash' grant found in allowed-tools -- scope it to specific "
            "command(s), per plugin-rulebook R6",
        )
    if tokens is None:
        return True, "no allowed-tools line found (skip)"
    if not tokens:
        return True, "no Bash(...) grants found (skip)"
    search_body = _usage_search_body(body)
    unused = []
    for t in tokens:
        needle = t.split("/")[-1] if "/" in t else t
        if not re.search(rf"\b{re.escape(needle)}\b", search_body):
            unused.append(t)
    if unused:
        return False, "Bash grant(s) never referenced anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, f"all {len(set(tokens))} distinct Bash grant(s) referenced in the body"


def check_reference_table_files_exist():
    _, _, text = _frontmatter_and_body()
    idx = text.find("## Reference Index")
    if idx == -1:
        return True, "no '## Reference Index' section found (skip)"
    section = text[idx:]
    link_targets = re.findall(r"\]\(([^)]+)\)", section)
    backtick_targets = re.findall(r"\|\s*`([^`]+)`\s*\|", section)
    targets = {
        t
        for t in set(link_targets) | set(backtick_targets)
        if "<" not in t and "." in t.rsplit("/", 1)[-1]
    }
    if not targets:
        return True, "no file paths found in '## Reference Index' (skip)"
    missing = [t for t in targets if not (SKILL_DIR / t).is_file()]
    if missing:
        return False, "'## Reference Index' file(s) do not exist: " + ", ".join(sorted(missing))
    return True, f"all {len(targets)} '## Reference Index' file path(s) exist"


def check_ap_numbers_unique():
    _, _, text = _frontmatter_and_body()
    start = text.find("## Anti-Pattern Quick Reference")
    if start == -1:
        return True, "no '## Anti-Pattern Quick Reference' section found (skip)"
    end = text.find("\n## ", start + 10)
    section = text[start : end if end != -1 else None]
    ids = re.findall(r"^\|\s*(AP-\d+)\s*\|", section, re.MULTILINE)
    if not ids:
        return True, "no AP-N row identifiers found in the table (skip)"
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        return False, "duplicate AP-N identifier(s) in Anti-Pattern table: " + ", ".join(dupes)
    return True, f"all {len(ids)} AP-N identifiers in the table are unique"


CHECKS = [
    check_frontmatter,
    check_bash_grants,
    check_reference_table_files_exist,
    check_ap_numbers_unique,
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
