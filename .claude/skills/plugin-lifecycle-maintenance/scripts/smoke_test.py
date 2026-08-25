#!/usr/bin/env python3
"""Persisted smoke test for plugin-lifecycle-maintenance: frontmatter validity,
referenced-file existence, Bash-scope grant consistency, and phase/step/service-header
sequencing across workflows/*.md — this last check exists because a phase-insertion
edit (e.g. adding a new step between two existing ones) is exactly the kind of
change that silently leaves a stale "Step N" cross-reference elsewhere."""

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
    # `test-agent-trigger.sh`/`test-hook.sh` are excluded: this skill's prose splits the
    # owning plugin name and the script path across separate backtick spans
    # ("`agent-development`'s `scripts/test-agent-trigger.sh`"), so a bare
    # `scripts/test-agent-trigger.sh` match here is a cross-plugin reference, not a path
    # relative to this skill — already covered by check_bash_grants' full-path check instead.
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = (
        r"`(references/[\w.-]+\.md|workflows/[\w.-]+\.md"
        r"|scripts/(?!test-agent-trigger\.sh|test-hook\.sh)[\w./-]+)`"
    )
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Unlike plugin-lifecycle-upstream/-downstream, this skill's prose never uses the
    # "scoped `Bash(...)`" phrasing — it cites Bash grants in shorthand instead
    # (`` `Bash(date:*)` for the cutoff timestamp``, `` `Bash(git log/diff)` ``), which
    # wouldn't exact-match the frontmatter's own canonical grant strings either. So the
    # meaningful check here is: does each granted Bash(<cmd>:*) scope's base <cmd> word
    # actually appear somewhere in the body (SKILL.md + every workflows/*.md file)? An
    # unused grant is an R6 least-privilege smell even without exact-string phrasing.
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    value = fm_line_match.group(1).strip()
    if value in (">-", ">", "|", "|-", "|+", ">+"):
        # YAML block scalar: the real value is on subsequent, more-indented lines.
        block_lines = []
        for line in frontmatter[fm_line_match.end() :].splitlines():
            if line.strip() == "":
                continue
            if line[:1] in (" ", "\t"):
                block_lines.append(line)
            else:
                break
        value = " ".join(block_lines)
    granted_cmds = re.findall(r"Bash\(([\w.*/ -]+?)(?::|\))", value)
    granted_cmds = [c.removeprefix("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    for wf in sorted((SKILL_DIR / "workflows").glob("*.md")):
        body += "\n" + wf.read_text(encoding="utf-8")

    unused = [cmd for cmd in granted_cmds if not re.search(rf"\b{re.escape(cmd)}\b", body)]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def check_phase_sequence():
    # This skill's 4 workflow files each number independently (a fresh "Step 1"/"Service 1"
    # per file, not a shared global sequence) — checked per file, not merged across files.
    workflows_dir = SKILL_DIR / "workflows"
    if not workflows_dir.exists():
        return True, "no workflows/ directory (skip)"
    problems = []
    for wf in sorted(workflows_dir.glob("*.md")):
        text = wf.read_text(encoding="utf-8")
        numbers = [
            int(n) for n in re.findall(r"^##+ (?:Phase|Step|Service) (\d+):", text, re.MULTILINE)
        ]
        if not numbers:
            continue
        expected = list(range(numbers[0], numbers[0] + len(numbers)))
        if numbers != expected:
            problems.append(f"{wf.name}: found {numbers}, expected consecutive {expected}")
    if problems:
        return False, "phase/step numbering not sequential: " + "; ".join(problems)
    return True, "phase/step headers sequential in every workflow file checked"


CHECKS = [check_frontmatter, check_referenced_files, check_bash_grants, check_phase_sequence]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
