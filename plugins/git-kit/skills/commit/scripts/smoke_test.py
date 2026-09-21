#!/usr/bin/env python3
"""Persisted smoke test for commit: frontmatter validity, Bash-scope grant
usage, and step-header sequencing within the '## Instructions' section --
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


def _allowed_tools_value(frontmatter):
    """Extract allowed-tools' value, handling both a same-line value and a
    '>-'/'|'/'>' block-scalar followed by indented continuation lines."""
    line_match = re.search(r"^allowed-tools:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    if not line_match:
        return None
    rest = line_match.group(1).strip()
    if rest and not re.fullmatch(r"[|>][+-]?", rest):
        return rest
    # Block-scalar form: collect the indented lines that follow.
    start = line_match.end()
    block_lines = []
    for line in frontmatter[start:].splitlines():
        if line.strip() == "" or line.startswith((" ", "\t")):
            block_lines.append(line.strip())
        else:
            break
    return " ".join(block_lines)


def _grant_pattern(cmd: str) -> str:
    # Boundary-safe on both ends, built from the full grant phrase (not just its first word)
    # so distinct sibling commands sharing a first word ("gh pr comment" vs "gh pr edit")
    # aren't conflated, and wildcard-aware so "gh api repos/*/labels/*" matches the real
    # "gh api repos/{owner}/{repo}/labels/..." invocation -- same logic create-pr's own
    # smoke test uses, ported here after this check was found to only match a grant's first
    # word (a false-pass risk once a grant's only real use moved into a shared reference file).
    return r"(?<!\w)" + r"[^\s]*".join(re.escape(part) for part in cmd.split("*")) + r"(?!\w)"


def _collect_search_text(body: str) -> str:
    search_text = body
    for sub in ("references", "scripts"):
        d = SKILL_DIR / sub
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    try:
                        search_text += "\n" + f.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        pass

    # A plugin-root-level shared reference (e.g. "../../references/bypass-attestation-
    # protocol.md") this skill's own body points at -- a grant whose only real invocation
    # lives there still counts as used.
    plugin_root = SKILL_DIR.parent.parent
    for m in re.finditer(r"\.\./\.\./references/([\w.-]+\.md)", body):
        other = plugin_root / "references" / m.group(1)
        if other.is_file():
            try:
                search_text += "\n" + other.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass

    return search_text


def check_bash_grants():
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    value = _allowed_tools_value(frontmatter)
    if value is None:
        return True, "no allowed-tools line found (skip)"
    # Command text may contain spaces (e.g. "git status", "gh api user") -- match
    # everything up to an optional ':<args>' before the closing paren, not just
    # word/path characters.
    granted_cmds = re.findall(r"Bash\(([^():]+?)(?::[^)]*)?\)", value)
    granted_cmds = [c.strip().lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    search_text = _collect_search_text(body)
    unused = [cmd for cmd in granted_cmds if not re.search(_grant_pattern(cmd), search_text)]
    if unused:
        return False, (
            "Bash grant(s) never invoked anywhere in the body/references/scripts (or a "
            "plugin-root reference file it names): " + ", ".join(sorted(set(unused)))
        )
    return True, "every granted Bash command is invoked somewhere in the skill's own files"


def check_step_sequence():
    # Scoped to the "## Instructions" section only -- "## Branch Naming Convention" and
    # other later sections legitimately restart their own numbered lists for unrelated
    # workflow descriptions, which a whole-file scan would wrongly flag as non-sequential.
    # Note: the ^(\d+)\. pattern below only matches whole-integer step headers, so
    # decimal sub-steps (7.5., 13.5., 16.5.) are intentionally excluded from this check --
    # it validates the 1-18 whole-number sequence only, not sub-step placement/ordering.
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return True, "no '## Instructions' section found (skip)"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", section, re.MULTILINE)]
    if not numbers:
        return True, "no numbered steps found (skip)"
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        return False, f"step numbering not sequential: found {numbers}, expected {expected}"
    return True, "step headers sequential"


CHECKS = [check_frontmatter, check_bash_grants, check_step_sequence]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
