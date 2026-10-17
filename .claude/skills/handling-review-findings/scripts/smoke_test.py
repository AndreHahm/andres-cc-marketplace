#!/usr/bin/env python3
"""Persisted smoke test for handling-review-findings: frontmatter validity,
referenced-file existence, Bash-scope grant usage (searching SKILL.md's own
body plus every references/*.md file, since some grants are only used inside
an extracted reference), step-header sequencing (the "## Workflow" section),
evals.json presence, no raw GitHub grant left in allowed-tools, file writes
limited to scoped Edit(...) grants, and the
git-review-api.py wrapper's typed -F values plus its documented subcommands
(8 checks total) -- structural checks
only, since this is a conversational, gh-CLI-orchestration skill with no
executable logic of its own to simulate. Adapted from codex-review-recovery's
own smoke_test.py (same shape and check set)."""

import json
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

    # Shell quotes around a script path are not part of the grant text.
    body = fm_text[header_end:].replace('"', "")
    # A grant used only inside an extracted references/*.md file (progressive disclosure)
    # must still count as "used" -- search those too, not just SKILL.md's own body.
    references_dir = SKILL_DIR / "references"
    if references_dir.is_dir():
        for ref_file in sorted(references_dir.glob("*.md")):
            body += "\n" + ref_file.read_text(encoding="utf-8").replace('"', "")

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
    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"evals.json is not valid JSON: {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("evals"), list) or not data["evals"]:
        return False, "evals.json has no scenarios in 'evals'"
    return True, f"evals.json present with {len(data['evals'])} scenario(s)"


WRAPPER = SKILL_DIR.parent.parent / "scripts" / "git-review-api.py"
SUBCOMMANDS = [
    "threads",
    "resolve",
    "reply",
    "trigger-comment",
    "issue-create",
    "list-comments",
    "whoami",
    "push-destinations",
]
# Every `gh` grant outside this set is rejected, so a broad `Bash(gh:*)` or `Bash(gh api:*)` cannot
# slip past the wrapper; `sed` and `git remote get-url` were replaced by wrapper subcommands too.
ALLOWED_GH_GRANTS = {"gh pr checks", "gh pr view", "gh repo view", "gh issue list"}
RAW_GRANTS = ("sed", "git remote get-url")
# The two Bash commands the skill must hold, compared as whole parsed grants, not as substrings of
# the allowed-tools line (a `Read(...)` or unrelated `Bash(...)` grant naming the script would
# satisfy a substring test).
WRAPPER_GRANT = "python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py"
MARKER_GRANT = "bash ${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh gh-pr-review-wrapper"


def _bash_grants(grants):
    """The command part of every `Bash(<command>[:*])` entry in an allowed-tools value."""
    found = []
    for entry in grants.split(", "):
        match = re.fullmatch(r"Bash\((.*?)(?::\*)?\)", entry.strip())
        if match:
            found.append(match.group(1))
    return found


def check_no_raw_github_grants(path=None):
    """The skill must reach GitHub only through git-review-api.py (#580): no broad raw grant."""
    path = path or SKILL_MD
    text = path.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    line = re.search(r"^allowed-tools:\s*(.+)$", text[:header_end], re.MULTILINE)
    if not line:
        return False, "no allowed-tools line found"
    commands = _bash_grants(line.group(1))
    if WRAPPER_GRANT not in commands:
        return False, f"allowed-tools has no Bash grant for the pinned `{WRAPPER_GRANT}`"
    broad = [
        c for c in commands if (c == "gh" or c.startswith("gh ")) and c not in ALLOWED_GH_GRANTS
    ]
    raw = [c for c in commands if any(c == r or c.startswith(r + " ") for r in RAW_GRANTS)]
    if broad or raw:
        return False, "allowed-tools has a grant the wrapper replaced: " + ", ".join(broad + raw)
    if MARKER_GRANT not in commands:
        return False, f"the marker-writer grant is not the pinned `{MARKER_GRANT}`"
    return True, "allowed-tools reaches GitHub only through git-review-api.py"


# The whole allowed-tools line is pinned (#582). A denylist of bad grants is easy to get past (a
# bare `Write`, `Write(<glob>)` which is accepted but never matches, `Bash(git log:*)`,
# `Bash(git format-patch:*)`, a double-spaced or absolute-path `git diff`, all of which can write
# a file such as a pinned script), so the check compares the entries with this exact list.
# Changing a grant means changing this list in the same edit, which is the review point.
EXPECTED_ALLOWED_TOOLS = (
    "Bash(gh pr checks:*)",
    "Bash(gh pr view:*)",
    "Bash(gh repo view:*)",
    "Bash(git rev-parse:*)",
    "Bash(python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/git-review-fix-diff.py:*)",
    "Bash(git ls-files:*)",
    "Bash(python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py:*)",
    "Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/git-verify-fix-diff.py:*)",
    "Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py:*)",
    "Bash(gh issue list:*)",
    "Bash(date:*)",
    "Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh gh-pr-review-wrapper:*)",
    "Read",
    "Edit(//tmp/claude-*/*/*/scratchpad/**)",
    "Edit(issues/**)",
    "Skill(commit)",
    "Grep",
)


def check_file_write_grants_scoped(path=None):
    """allowed-tools must be exactly EXPECTED_ALLOWED_TOOLS: file writes only as the scoped `Edit`
    entries, diffs only through the pinned git-review-fix-diff.py."""
    path = path or SKILL_MD
    text = path.read_text(encoding="utf-8")
    header = text[: text.find("\n---\n", 4) + 5]
    if len(re.findall(r"^['\"]?allowed-tools['\"]?[ \t]*:", header, re.MULTILINE)) != 1:
        return False, "the frontmatter must hold exactly one allowed-tools key"
    line = re.search(r"^allowed-tools:[ \t]*(.+)$", header, re.MULTILINE)
    if not line:
        return False, "no single-line allowed-tools value found"
    # A YAML plain scalar continues on any more-indented next line, which a one-line read misses.
    following = header[line.end() + 1 :].split("\n", 1)[0]
    if not re.match(r"[A-Za-z_][\w-]*:|---$", following):
        return (
            False,
            "the line after allowed-tools must be another top-level key or the closing ---",
        )
    entries = line.group(1).strip().split(", ")
    unexpected = [e for e in entries if e not in EXPECTED_ALLOWED_TOOLS]
    missing = [e for e in EXPECTED_ALLOWED_TOOLS if e not in entries]
    if unexpected or missing or len(entries) != len(set(entries)):
        return False, (
            "allowed-tools differs from the pinned list: unexpected "
            f"{unexpected or 'none'}, missing {missing or 'none'}, duplicates "
            f"{len(entries) != len(set(entries))}"
        )
    return True, "allowed-tools is exactly the pinned list (scoped Edit writes, pinned diff script)"


def check_wrapper_documented_and_typed(path=None):
    """The wrapper must exist, send a typed null cursor and body file (issue #312), and every
    subcommand must be documented in references/github-api-mechanics.md."""
    path = path or WRAPPER
    if not path.is_file():
        return False, f"scripts/git-review-api.py not found at {path}"
    source = path.read_text(encoding="utf-8")
    if '"-f", "cursor=null"' in source:
        return False, "wrapper sends -f cursor=null (the string 'null'; issue #312)"
    if '"-F", "cursor=null"' not in source:
        return False, "wrapper does not send -F cursor=null on the first threads call"
    if '"-F", "body=@-"' not in source:
        return False, "wrapper does not post the reply body on stdin through -F body=@-"
    ref = SKILL_DIR / "references" / "github-api-mechanics.md"
    if not ref.is_file():
        return False, f"references/github-api-mechanics.md not found at {ref}"
    docs = ref.read_text(encoding="utf-8")
    missing = [s for s in SUBCOMMANDS if f"`{s}`" not in docs]
    if missing:
        return False, "github-api-mechanics.md does not document: " + ", ".join(missing)
    return True, "wrapper sends typed -F values and every subcommand is documented"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_step_sequence,
    check_evals_json_exists,
    check_no_raw_github_grants,
    check_file_write_grants_scoped,
    check_wrapper_documented_and_typed,
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
