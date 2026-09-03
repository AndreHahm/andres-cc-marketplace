#!/usr/bin/env python3
"""Persisted smoke test for session-wrap-up: frontmatter validity,
skill-relative references/scripts file existence, ${CLAUDE_PLUGIN_ROOT}-relative
script existence, allowed-tools Bash-grant usage, Step-header sequencing, and
the Testing & Validation section's required subsections -- structural checks
only, since this is a conversational skill with no executable logic of its
own to simulate."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
PLUGIN_ROOT = SKILL_DIR.parent.parent


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


def check_referenced_files():
    _, body, _ = _frontmatter_and_body()
    targets = set()
    targets.update(re.findall(r"\]\(((?:references|scripts)/[\w./-]+\.(?:md|py|sh))\)", body))
    targets.update(re.findall(r"`((?:references|scripts)/[\w./-]+\.(?:md|py|sh))`", body))
    if not targets:
        return True, "no skill-relative references/scripts file paths found (skip)"
    # A bare "scripts/..." path can be this skill's own scripts/ dir, or (for skills whose
    # scripts live shared at the plugin root, e.g. session_store.py/session_transcript.py)
    # a plugin-root-relative mention -- check both before declaring it missing.
    missing = [
        t for t in targets if not (SKILL_DIR / t).is_file() and not (PLUGIN_ROOT / t).is_file()
    ]
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(missing))
    return True, f"all {len(targets)} referenced file(s) exist"


def check_plugin_root_scripts_exist():
    frontmatter, body, _ = _frontmatter_and_body()
    targets = set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+\.(?:py|sh))", frontmatter + body))
    if not targets:
        return True, "no ${CLAUDE_PLUGIN_ROOT}-relative script paths found (skip)"
    missing = [t for t in targets if not (PLUGIN_ROOT / t).is_file()]
    if missing:
        return False, "referenced script(s) do not exist: " + ", ".join(sorted(missing))
    return True, f"all {len(targets)} referenced ${{CLAUDE_PLUGIN_ROOT}} script path(s) exist"


def check_bash_grants():
    frontmatter, body, _ = _frontmatter_and_body()
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    grants = re.findall(r"Bash\(([^)]+)\)", fm_line_match.group(1))
    if not grants:
        return True, "no Bash(...) grants found (skip)"
    unused = []
    for grant in grants:
        script_match = re.search(r"([\w-]+\.(?:py|sh))", grant)
        if script_match:
            needle = script_match.group(1)
        else:
            needle = re.sub(r":\*$", "", grant).strip().strip('"')
        if not re.search(re.escape(needle), body):
            unused.append(grant)
    if unused:
        return False, "Bash grant(s) never referenced in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, f"all {len(set(grants))} distinct Bash grant(s) referenced in the body"


def check_step_sequence():
    # "## Step N:" headers (the common case) are checked as one continuous sequence across
    # the whole document. "### Step N:" headers (session-handoff/session-recover's workflow
    # steps -- an H2-only regex previously gave these two skills zero real coverage, found by
    # skilldir-reviewer) are checked per enclosing "## " section instead, since a skill can
    # have multiple named H2 workflow sections (e.g. session-handoff's separate CREATE/RESUME
    # workflows) whose H3 steps each legitimately restart at 1.
    _, body, _ = _frontmatter_and_body()
    found_any = False

    h2_numbers = [int(n) for n in re.findall(r"^## Step (\d+):", body, re.MULTILINE)]
    if h2_numbers:
        found_any = True
        expected = list(range(1, len(h2_numbers) + 1))
        if h2_numbers != expected:
            return False, f"Step numbering not sequential: found {h2_numbers}, expected {expected}"

    section_starts = [m.start() for m in re.finditer(r"^## ", body, re.MULTILINE)]
    bounds = [0, *section_starts, len(body)]
    chunks = [body[bounds[i] : bounds[i + 1]] for i in range(len(bounds) - 1)] or [body]
    for chunk in chunks:
        h3_numbers = [int(n) for n in re.findall(r"^### Step (\d+):", chunk, re.MULTILINE)]
        if not h3_numbers:
            continue
        found_any = True
        expected = list(range(1, len(h3_numbers) + 1))
        if h3_numbers != expected:
            return False, f"Step numbering not sequential: found {h3_numbers}, expected {expected}"

    if not found_any:
        return True, "no '## Step N:'/'### Step N:' headers found (skip)"
    return True, "Step headers sequential"


def check_testing_validation_section():
    _, body, _ = _frontmatter_and_body()
    idx = body.find("## Testing & Validation")
    if idx == -1:
        return False, "no '## Testing & Validation' section found"
    heading_end = idx + len("## Testing & Validation")
    next_h2 = re.search(r"\n## ", body[heading_end:])
    section_end = heading_end + next_h2.start() if next_h2 else len(body)
    section = body[idx:section_end]
    missing = [
        marker
        for marker in (
            "Verify this skill activates on",
            "Verify it does NOT activate on",
            "Quality gates:",
        )
        if marker not in section
    ]
    if missing:
        return False, "Testing & Validation section missing: " + ", ".join(missing)
    if "- [ ]" not in section:
        return False, "Quality gates has no checklist items ('- [ ]')"
    return True, "Testing & Validation section has all required subsections"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_plugin_root_scripts_exist,
    check_bash_grants,
    check_step_sequence,
    check_testing_validation_section,
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
