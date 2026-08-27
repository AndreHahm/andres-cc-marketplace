#!/usr/bin/env python3
"""Persisted smoke test for git-worktrees: frontmatter validity,
referenced-file existence, Bash-scope grant usage, and step-header
sequencing ("## Workflow Patterns" section) -- structural checks only, since this is a
conversational skill with no executable logic of its own to simulate.
Adapted from handling-review-findings's own smoke_test.py (same check set
and refined Bash-grant-match logic), extended to also search this skill's
own references/scripts files -- and any cross-skill reference file this
skill's own body explicitly points at -- before declaring a Bash grant
unused, since several git-kit skills push command usage into a references
file (progressive disclosure) rather than spelling it out in SKILL.md's
own body."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SECTION_HEADERS = ["## Workflow Patterns", "## Resolving a Cherry-Pick Commit List"]


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

    repo_root = _find_repo_root(SKILL_DIR)
    skill_relative = r"`((?:references|scripts)/[\w./-]+\.(?:md|py|sh))`"
    for match in re.finditer(skill_relative, text):
        path = SKILL_DIR / match.group(1)
        if path.exists():
            continue
        # A "scripts/..." path with its own subdirectory (e.g. "scripts/marketplace_ci/x.py")
        # can be this repo's own root-level tooling rather than the skill's own scripts/ --
        # fall back to a repo-root-relative resolution before declaring it missing.
        if repo_root is not None and (repo_root / match.group(1)).exists():
            continue
        missing.append(match.group(1))

    repo_relative = r"`((?:docs|evals)/[\w./-]+\.(?:md|json))`"
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


def _grant_pattern(cmd: str) -> str:
    # Boundary-safe on both ends so a short/common token (e.g. "diff") can't false-match
    # inside an unrelated word ("different", "differences") -- (?<!\w)/(?!\w) rather than
    # \b, since \b requires an actual word/non-word *transition* and would wrongly reject a
    # genuine match starting with a non-word character preceded by another non-word
    # character (e.g. a `${...}`-style grant preceded by a backtick in prose).
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

    # A cross-skill reference file this skill's own body explicitly names (e.g.
    # "skills/merge-pr/references/merge-rights-check.md") is fair game too -- a skill that
    # documents "Read <other skill>'s reference file" genuinely uses whatever Bash commands
    # that file demonstrates, even though it never repeats them in its own body.
    plugin_root = SKILL_DIR.parent.parent
    for m in re.finditer(r"skills/([\w-]+)/references/([\w.-]+\.md)", body):
        other = plugin_root / "skills" / m.group(1) / "references" / m.group(2)
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
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.*/${} -]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    search_text = _collect_search_text(body)

    unused = []
    for cmd in granted_cmds:
        # A script-path grant is normalized to its basename before matching -- the
        # frontmatter and body/references can spell the same script's path differently
        # (${CLAUDE_PLUGIN_ROOT}/... vs a portable */<plugin>/... glob), and what actually
        # matters is whether the script itself is invoked or described anywhere.
        script_match = re.search(r"([\w-]+\.(?:sh|py))", cmd)
        if script_match:
            if re.search(re.escape(script_match.group(1)), search_text):
                continue
            unused.append(cmd)
            continue
        if re.search(_grant_pattern(cmd), search_text):
            continue
        unused.append(cmd)

    if unused:
        return False, (
            "Bash grant(s) never invoked anywhere in the skill's own body/references/scripts "
            "(or a cross-skill reference file it names): " + ", ".join(sorted(set(unused)))
        )
    return True, "every granted Bash command is invoked somewhere in the skill's own files"


def check_step_sequence():
    # Scoped to the declared SECTION_HEADERS only -- other sections (e.g. "Testing &
    # Validation") legitimately restart their own numbered lists for unrelated scenarios,
    # which a whole-file scan would wrongly flag as non-sequential. Within a found section,
    # a "### " subsection (e.g. distinct scenarios/paths) is checked independently too --
    # each subsection legitimately restarts its own numbering.
    text = SKILL_MD.read_text(encoding="utf-8")
    found_any = False
    for header in SECTION_HEADERS:
        start = text.find("\n" + header + "\n")
        if start == -1:
            continue
        found_any = True
        end = text.find("\n## ", start + 1)
        section = text[start : end if end != -1 else len(text)]

        sub_starts = [m.start() for m in re.finditer(r"^### ", section, re.MULTILINE)]
        if sub_starts:
            bounds = [0, *sub_starts, len(section)]
            chunks = [section[bounds[i] : bounds[i + 1]] for i in range(len(bounds) - 1)]
        else:
            chunks = [section]

        for chunk in chunks:
            numbers = [int(n) for n in re.findall(r"^(\d+)\. ", chunk, re.MULTILINE)]
            if not numbers:
                continue
            expected = list(range(numbers[0], numbers[0] + len(numbers)))
            if numbers != expected:
                return False, (
                    f"step numbering not sequential in '{header}': "
                    f"found {numbers}, expected {expected}"
                )
    if not found_any:
        return True, f"none of {SECTION_HEADERS} found (skip)"
    return True, "step headers sequential in every found section/subsection"


def _find_repo_root(start: pathlib.Path) -> pathlib.Path | None:
    current = start
    for _ in range(10):
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def check_cherry_pick_resolution_fixes():
    ref = SKILL_DIR / "references" / "cherry-pick-resolution.md"
    if not ref.is_file():
        return False, "references/cherry-pick-resolution.md not found"
    text = ref.read_text(encoding="utf-8")
    if "lists a maximum of 250 commits" not in text.lower():
        return (
            False,
            "Path 2 no longer documents the 250-commit hard cap on the pulls/commits endpoint",
        )
    if "compare/<baseRefOid>...<headRefOid>" not in text:
        return False, "Path 2 no longer documents the compare-endpoint fallback beyond 250 commits"
    if "git fetch origin pull/<N>/head" not in text:
        return (
            False,
            "Path 2 no longer documents fetching a PR's commits before handing them to Strategy C",
        )
    if "stop and show the new list via a fresh" not in text:
        return False, "the re-resolve step no longer reconfirms with the user when the list changed"

    fm_text = SKILL_MD.read_text(encoding="utf-8")
    if "git cat-file -e" not in fm_text or "git branch --all --contains" not in fm_text:
        return (
            False,
            "SKILL.md's allowed-tools no longer grants git cat-file -e / "
            "git branch --all --contains",
        )
    return (
        True,
        "cherry-pick-resolution.md's 250-commit cap, fetch-before-pick, and reconfirm-on-change "
        "fixes are present, and their commands are granted",
    )


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_step_sequence,
    check_cherry_pick_resolution_fixes,
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
