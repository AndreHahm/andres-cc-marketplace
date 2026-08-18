#!/usr/bin/env python3
"""Persisted smoke test for cross-model-review: frontmatter validity,
referenced prompt-file existence, Bash-scope grant usage, and step-header
sequencing within the 'Preflight' and 'Codex dispatch resolver' sections --
structural checks only, since this is a conversational, AskUserQuestion-driven
skill with no executable logic of its own to simulate."""

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


def check_referenced_prompt_files():
    text = SKILL_MD.read_text(encoding="utf-8")
    referenced = set(re.findall(r"prompts/([\w.-]+\.md)", text))
    missing = [name for name in referenced if not (SKILL_DIR / "prompts" / name).exists()]
    if missing:
        return False, "referenced prompt file(s) do not exist: " + ", ".join(sorted(missing))
    return True, "all referenced prompt files exist"


def check_bash_grants():
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    # Unlike a bare "Bash(git:*)"-style grant, several of this skill's grants are
    # multi-token ("Bash(node plugins/.../bridge-invoke.mjs:*)") -- capture up to the
    # first ':' or ')' rather than a no-space character class, or the space after "node"
    # would truncate the match to nothing.
    granted = re.findall(r"Bash\(([^:)]+?)(?::|\))", fm_line_match.group(1))

    body = fm_text[header_end:]
    unused = []
    for cmd in granted:
        # For a script-path grant, the leading verb ("node") is too generic to prove
        # the specific grant is used -- check the distinctive basename instead. A plain
        # multi-word command ("git diff", "git show") is checked as the whole phrase.
        needle = cmd.rsplit("/", 1)[-1] if "/" in cmd else cmd
        if not re.search(re.escape(needle), body):
            unused.append(cmd)
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def _check_section_step_sequence(section_header):
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find(f"\n## {section_header}\n")
    if start == -1:
        return True, f"no '## {section_header}' section found (skip)"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", section, re.MULTILINE)]
    if not numbers:
        return True, f"no numbered steps found in '## {section_header}' (skip)"
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        msg = f"'{section_header}' steps not sequential: found {numbers}, expected {expected}"
        return False, msg
    return True, f"'{section_header}' step headers sequential"


def check_preflight_step_sequence():
    return _check_section_step_sequence("Preflight")


def check_resolver_step_sequence():
    return _check_section_step_sequence("Codex dispatch resolver")


CHECKS = [
    check_frontmatter,
    check_referenced_prompt_files,
    check_bash_grants,
    check_preflight_step_sequence,
    check_resolver_step_sequence,
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
