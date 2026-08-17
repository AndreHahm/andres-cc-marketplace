#!/usr/bin/env python3
"""Persisted smoke test for codex-review-recovery: frontmatter validity,
referenced-file existence, Bash-scope grant usage, and step-header
sequencing -- structural checks only, since this is a conversational,
AskUserQuestion-driven skill with no executable logic of its own to
simulate. Adapted from merge-pr's own smoke_test.py (same shape, same
checks) since both are gh-CLI-orchestration skills in this plugin."""

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
    pattern = r"`(references/[\w.-]+\.md)`"
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
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
    granted_cmds = re.findall(r"Bash\(([\w.*/${}-]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    unused = [cmd for cmd in granted_cmds if not re.search(re.escape(cmd.split(" ")[0]), body)]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def check_step_sequence():
    # Scoped to the "## Instructions" section only -- other sections (e.g. "Testing &
    # Validation") legitimately restart their own numbered lists for unrelated scenarios,
    # which a whole-file scan would wrongly flag as non-sequential.
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return True, "no '## Instructions' section found (skip)"
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
    # ever correct for one of the two (a real bug caught here: parents[3]
    # from the mirror path landed one directory *above* the repo root).
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
    evals_path = repo_root / "evals" / "codex-review-recovery" / "evals.json"
    if not evals_path.is_file():
        return False, f"evals.json not found at {evals_path}"
    import json

    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"evals.json is not valid JSON: {exc}"
    if not data.get("evals"):
        return False, "evals.json has no scenarios in 'evals'"
    return True, f"evals.json present with {len(data['evals'])} scenario(s)"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_step_sequence,
    check_evals_json_exists,
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
