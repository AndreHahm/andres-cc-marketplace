#!/usr/bin/env python3
"""Persisted smoke test for agent-development: frontmatter validity, Bash-grant
usage, referenced-script existence, Additional-Resources table file existence,
and Frontmatter-Summary/documented-field cross-consistency -- structural checks
only, since this is a conversational, reference-driven skill with no executable
logic of its own to simulate beyond the two scripts it shells out to (which own
their own correctness)."""

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
    if "name:" not in fm or "description:" not in fm:
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def _granted_bash_tokens(frontmatter):
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return None
    bash_blocks = re.findall(r"Bash\(([^)]+)\)", fm_line_match.group(1))
    tokens = []
    for block in bash_blocks:
        for token in block.split():
            tokens.append(token.split(":")[0])
    return tokens


def check_bash_grants():
    frontmatter, body, _ = _frontmatter_and_body()
    tokens = _granted_bash_tokens(frontmatter)
    if tokens is None:
        return True, "no allowed-tools line found (skip)"
    if not tokens:
        return True, "no Bash(...) grants found (skip)"
    unused = []
    for t in tokens:
        needle = t.split("/")[-1] if "/" in t else t
        if not re.search(re.escape(needle), body):
            unused.append(t)
    if unused:
        return False, "Bash grant(s) never referenced anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, f"all {len(set(tokens))} distinct Bash grant(s) referenced in the body"


def check_scripts_exist():
    frontmatter, _, _ = _frontmatter_and_body()
    tokens = _granted_bash_tokens(frontmatter)
    if not tokens:
        return True, "no allowed-tools/Bash grants found (skip)"
    path_like = [t for t in tokens if "/" in t and re.search(r"\.(sh|py|mjs|js)$", t)]
    if not path_like:
        return True, "no file-path-shaped Bash grants found (skip)"
    missing = [p for p in path_like if not (SKILL_DIR / p).is_file()]
    if missing:
        return False, "referenced script(s) do not exist: " + ", ".join(missing)
    return True, f"all {len(path_like)} referenced script(s) exist"


def check_reference_table_files_exist():
    _, _, text = _frontmatter_and_body()
    idx = text.find("## Additional Resources")
    if idx == -1:
        return True, "no '## Additional Resources' section found (skip)"
    section = text[idx:]
    link_targets = re.findall(r"\]\(([^)]+)\)", section)
    backtick_targets = re.findall(r"\|\s*`([^`]+)`\s*\|", section)
    targets = {
        t
        for t in set(link_targets) | set(backtick_targets)
        if "<" not in t and "." in t.rsplit("/", 1)[-1]
    }
    if not targets:
        return True, "no file paths found in '## Additional Resources' (skip)"
    missing = [t for t in targets if not (SKILL_DIR / t).is_file()]
    if missing:
        return False, "'## Additional Resources' file(s) do not exist: " + ", ".join(
            sorted(missing)
        )
    return True, f"all {len(targets)} '## Additional Resources' file path(s) exist"


def check_frontmatter_fields_documented():
    _, _, text = _frontmatter_and_body()
    table_start = text.find("### Frontmatter Summary")
    if table_start == -1:
        return True, "no '### Frontmatter Summary' section found (skip)"
    table_end = text.find("\n### ", table_start + 10)
    table_section = text[table_start : table_end if table_end != -1 else None]
    rows = re.findall(r"^\|\s*(\w+)\s*\|", table_section, re.MULTILINE)
    field_names = [r for r in rows if r != "Field"]
    if not field_names:
        return True, "no field rows found in Frontmatter Summary table (skip)"
    before_table = text[:table_start]
    missing = [
        f
        for f in field_names
        if not re.search(rf"^### {re.escape(f)}\b", before_table, re.MULTILINE)
    ]
    if missing:
        return False, (
            "Frontmatter Summary table lists field(s) with no matching "
            "'### <field>' subsection above: " + ", ".join(missing)
        )
    return True, (
        f"all {len(field_names)} Frontmatter Summary field(s) have a "
        "matching '### <field>' subsection"
    )


CHECKS = [
    check_frontmatter,
    check_bash_grants,
    check_scripts_exist,
    check_reference_table_files_exist,
    check_frontmatter_fields_documented,
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
