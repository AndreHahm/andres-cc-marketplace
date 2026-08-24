#!/usr/bin/env python3
"""Persisted smoke test for analyzing-sessions: frontmatter validity,
Bash-grant usage, Reference-Guide table file existence, and Phase-header
sequencing -- structural checks only, since this is a conversational,
multi-phase retrospective skill with no executable logic of its own to
simulate."""

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


def check_reference_table_files_exist():
    _, _, text = _frontmatter_and_body()
    idx = text.find("## Reference Guide")
    if idx == -1:
        return True, "no '## Reference Guide' section found (skip)"
    section = text[idx:]
    link_targets = re.findall(r"\]\(([^)]+)\)", section)
    backtick_targets = re.findall(r"\|\s*`([^`]+)`\s*\|", section)
    targets = {
        t
        for t in set(link_targets) | set(backtick_targets)
        if "<" not in t and "." in t.rsplit("/", 1)[-1]
    }
    if not targets:
        return True, "no file paths found in '## Reference Guide' (skip)"
    missing = [t for t in targets if not (SKILL_DIR / t).is_file()]
    if missing:
        return False, "'## Reference Guide' file(s) do not exist: " + ", ".join(sorted(missing))
    return True, f"all {len(targets)} '## Reference Guide' file path(s) exist"


def check_phase_sequence():
    _, _, text = _frontmatter_and_body()
    numbers = [int(n) for n in re.findall(r"^## Phase (\d+):", text, re.MULTILINE)]
    if not numbers:
        return True, "no '## Phase N:' headers found (skip)"
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        return False, f"Phase numbering not sequential: found {numbers}, expected {expected}"
    return True, "Phase headers sequential"


CHECKS = [
    check_frontmatter,
    check_bash_grants,
    check_reference_table_files_exist,
    check_phase_sequence,
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
