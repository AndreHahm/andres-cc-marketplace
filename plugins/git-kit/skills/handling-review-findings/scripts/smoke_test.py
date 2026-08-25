#!/usr/bin/env python3
"""Persisted smoke test for handling-review-findings: frontmatter validity,
referenced-file existence, Bash-scope grant usage (searching SKILL.md's own
body plus every references/*.md file, since some grants are only used inside
an extracted reference), step-header sequencing (the "## Workflow" section),
evals.json presence, and the gh api -f/-F warning in
references/github-api-mechanics.md (6 checks total) -- structural checks
only, since this is a conversational, gh-CLI-orchestration skill with no
executable logic of its own to simulate. Adapted from codex-review-recovery's
own smoke_test.py (same shape and check set)."""

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

    # references/ and scripts/ paths are relative to this skill's own directory.
    skill_relative = r"`((?:references|scripts)/[\w./-]+\.(?:md|py|sh))`"
    for match in re.finditer(skill_relative, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))

    # evals/ paths are relative to the repo root, not this skill's directory.
    repo_root = _find_repo_root(SKILL_DIR)
    repo_relative = r"`(evals/[\w./-]+\.(?:md|json))`"
    for match in re.finditer(repo_relative, text):
        if repo_root is None:
            missing.append(match.group(1) + " (repo root not found)")
            continue
        path = repo_root / match.group(1)
        if not path.exists():
            missing.append(match.group(1))

    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.*/${} -]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    # A grant used only inside an extracted references/*.md file (progressive disclosure)
    # must still count as "used" -- search those too, not just SKILL.md's own body.
    references_dir = SKILL_DIR / "references"
    if references_dir.is_dir():
        for ref_file in sorted(references_dir.glob("*.md")):
            body += "\n" + ref_file.read_text(encoding="utf-8")

    # Match the full multi-word grant (e.g. "gh pr checks"), not just its first token --
    # a first-token-only match (e.g. bare "gh") would false-positive against any
    # unrelated word containing it anywhere in the body. A literal "*" inside a grant
    # (e.g. "gh api repos/*/pulls/*/comments") is a path-segment wildcard, not a literal
    # asterisk -- the body prose spells the same endpoint with {owner}/{repo}-style
    # placeholders instead, so it's translated to a flexible non-whitespace match rather
    # than escaped literally, or every path-pattern grant would false-FAIL here.
    # The trailing (?!/) guards against a shorter grant (e.g. ".../comments") silently
    # PASSing as "invoked" when the only real occurrence in the body is actually a longer,
    # differently-scoped path (e.g. ".../comments/{comment_id}/replies") that happens to
    # start with the same prefix -- without it, an unanchored match can't tell "invoked"
    # from "is a textual prefix of something else that's invoked".
    def _grant_pattern(cmd: str) -> str:
        return r"[^\s]*".join(re.escape(part) for part in cmd.split("*")) + r"(?!/)"

    unused = [cmd for cmd in granted_cmds if not re.search(_grant_pattern(cmd), body)]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def check_step_sequence():
    # Scoped to the "## Workflow" section only -- other sections (e.g. "Testing &
    # Validation") legitimately restart their own numbered lists for unrelated scenarios,
    # which a whole-file scan would wrongly flag as non-sequential.
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Workflow\n")
    if start == -1:
        return True, "no '## Workflow' section found (skip)"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. \*\*", section, re.MULTILINE)]
    if not numbers:
        return True, "no numbered steps found (skip)"
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        return False, f"step numbering not sequential: found {numbers}, expected {expected}"
    return True, "step headers sequential"


def _find_repo_root(start: pathlib.Path) -> pathlib.Path | None:
    # Walk up looking for the repo-root marker rather than a fixed parents[N]
    # index -- the canonical path (plugins/<plugin>/skills/<name>/scripts/)
    # and the .claude/ mirror (.claude/skills/<name>/scripts/) sit at
    # different depths below the repo root, so a hardcoded index is only
    # ever correct for one of the two.
    current = start
    for _ in range(10):
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def check_evals_json_exists():
    repo_root = _find_repo_root(SKILL_DIR)
    if repo_root is None:
        return False, "could not locate repo root (no .git found within 10 parent levels)"
    evals_path = repo_root / "evals" / "handling-review-findings" / "evals.json"
    if not evals_path.is_file():
        return False, f"evals.json not found at {evals_path}"
    import json

    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"evals.json is not valid JSON: {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("evals"), list) or not data["evals"]:
        return False, "evals.json has no scenarios in 'evals'"
    return True, f"evals.json present with {len(data['evals'])} scenario(s)"


def check_github_api_mechanics_fF_warning():
    path = SKILL_DIR / "references" / "github-api-mechanics.md"
    if not path.is_file():
        return False, f"references/github-api-mechanics.md not found at {path}"
    text = path.read_text(encoding="utf-8")
    if "-f" not in text or "-F" not in text:
        return False, "github-api-mechanics.md doesn't mention both -f and -F flags"
    if "@" not in text:
        return (
            False,
            "github-api-mechanics.md doesn't mention the @<path> file-reference syntax at all",
        )
    if "never interprets a leading" not in text and "never interpret a leading" not in text:
        return False, "github-api-mechanics.md is missing the -f/-F @-path warning callout"
    return True, "references/github-api-mechanics.md carries the -f/-F @-path warning"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_step_sequence,
    check_evals_json_exists,
    check_github_api_mechanics_fF_warning,
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
