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


def check_plugin_root_paths():
    # ${CLAUDE_PLUGIN_ROOT} resolves to the PLUGIN root (plugins/<name>/), not this skill's own
    # directory -- a path like "${CLAUDE_PLUGIN_ROOT}/prompts/review.md" (missing the
    # "skills/<skill-name>/" segment) silently resolves to a location that doesn't exist. Verify
    # every such path actually resolves against the plugin root, not just this skill's directory.
    text = SKILL_MD.read_text(encoding="utf-8")
    plugin_root = SKILL_DIR.parent.parent
    raw = set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}(/[\w./-]+)", text))
    missing = []
    for rel in raw:
        # A trailing "/..." is a documentation ellipsis (e.g. ".../prompts/..."), not a
        # literal path segment -- strip it before checking existence, or every such
        # placeholder reports as a missing path even though it was never meant to resolve.
        concrete = re.sub(r"(/\.\.\.)+$", "", rel)
        if concrete and not (plugin_root / concrete.lstrip("/")).exists():
            missing.append(concrete)
    if missing:
        return (
            False,
            "${CLAUDE_PLUGIN_ROOT} path(s) do not resolve against the plugin root: "
            + ", ".join(sorted(missing)),
        )
    return True, "every concrete ${CLAUDE_PLUGIN_ROOT} path resolves against the plugin root"


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
        # Word-boundary anchored: an unanchored search would let a short/common-word
        # needle (e.g. "cat") false-pass on unrelated prose containing it as a substring
        # (e.g. "location", "classification", "duplicate").
        needle = cmd.rsplit("/", 1)[-1] if "/" in cmd else cmd
        if not re.search(r"\b" + re.escape(needle) + r"\b", body):
            unused.append(cmd)
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def _check_section_step_sequence(section_header):
    # Both callers below name a section this SKILL.md is required to have -- unlike a generic
    # reusable check, a missing section or a section with no numbered steps is the exact
    # structural regression this check exists to catch, not something to skip past.
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find(f"\n## {section_header}\n")
    if start == -1:
        return False, f"required '## {section_header}' section not found"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", section, re.MULTILINE)]
    if not numbers:
        return False, f"'## {section_header}' has no numbered steps"
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
    check_plugin_root_paths,
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
