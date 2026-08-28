#!/usr/bin/env python3
"""Persisted smoke test for mining-review-learnings: frontmatter validity,
referenced-script existence, Reference-Guide file existence, Bash-scope grant
usage, and Phase-header sequencing -- structural checks only, since this is a
conversational, AskUserQuestion-driven skill with no executable logic of its
own to simulate (it shells out to shared analysis-kit scripts, which own
their own correctness)."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _find_repo_root(start: pathlib.Path) -> pathlib.Path:
    for parent in (start, *start.parents):
        if (parent / ".git").exists():
            return parent
    return start.parents[2]  # fallback: should be unreachable inside this repo


# Resolved against the repository root rather than SKILL_DIR.parent.parent so this
# check works identically from the plugins/analysis-kit/ tree and from the .claude/
# development mirror -- the latter's SKILL_DIR.parent.parent is .claude/, which has
# no scripts/ or references/ of its own.
PLUGIN_ROOT = _find_repo_root(SKILL_DIR) / "plugins" / "analysis-kit"


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
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter = text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.*/${}\s-]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/").split("/")[-1] for c in granted_cmds]

    body = text[header_end:]
    # Exclude the Reference Guide table from the "used" search -- a grant's basename
    # appearing only as a documentation pointer there (e.g. a Reference Guide row
    # naming a file that happens to share a basename with a granted script) must not
    # count as "used". Everything before that section (Phase prose, inline command
    # examples) still counts, including invocations described outside a literal
    # Bash(...) span (e.g. a shared references/ file's own plain command text).
    ref_guide_start = body.find("\n## Reference Guide\n")
    searchable_body = body[:ref_guide_start] if ref_guide_start != -1 else body
    unused = [
        cmd for cmd in granted_cmds if not re.search(re.escape(cmd.split(" ")[0]), searchable_body)
    ]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def check_referenced_scripts_exist():
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter = text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    script_paths = re.findall(
        r"Bash\(python \*/analysis-kit/(scripts/[\w./-]+\.py):", fm_line_match.group(1)
    )
    missing = [p for p in script_paths if not (PLUGIN_ROOT / p).is_file()]
    if missing:
        return False, "referenced script(s) do not exist: " + ", ".join(missing)
    if not script_paths:
        return True, "no scripts/*.py Bash grants found (skip)"
    return True, f"all {len(script_paths)} referenced script(s) exist"


def check_reference_guide_files_exist():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Reference Guide\n")
    if start == -1:
        return True, "no '## Reference Guide' section found (skip)"
    section = text[start:]
    paths = re.findall(r"\|\s*`([^`]+)`\s*\|", section)
    missing = []
    for p in paths:
        if p.endswith("/"):
            continue  # output directory, not expected to exist yet
        if "<" in p:
            continue  # runtime-resolved placeholder (e.g. <plugin-devkit-root>), not a literal path
        resolved = (SKILL_DIR / p).resolve()
        if not resolved.is_file():
            missing.append(p)
    if missing:
        return False, "Reference Guide file(s) do not exist: " + ", ".join(missing)
    if not paths:
        return True, "no file paths found in Reference Guide (skip)"
    return True, f"all {len(paths)} Reference Guide file path(s) exist"


def check_phase_sequence():
    text = SKILL_MD.read_text(encoding="utf-8")
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
    check_referenced_scripts_exist,
    check_reference_guide_files_exist,
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
