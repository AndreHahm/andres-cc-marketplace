#!/usr/bin/env python3
"""Persisted smoke test for resolving-merge-conflicts: frontmatter validity,
referenced-file existence, Bash-scope grant usage, and step-header sequencing
(4 checks total) -- structural checks only, since this is a conversational,
plan-then-execute skill with no executable logic of its own to simulate beyond
its three shell scripts (checked separately, not by this test).
Adapted from codex-review-recovery's own smoke_test.py (same shape), minus its
evals.json check -- no skill-tester eval has been run for this skill yet."""

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

    # references/ and scripts/ paths are relative to this skill's own directory. Optional
    # leading `"${CLAUDE_PLUGIN_ROOT}/` and trailing `"` -- a real gap found by a 2026-08
    # audit: SKILL.md's own script invocations are always written as
    # `"${CLAUDE_PLUGIN_ROOT}/scripts/x.sh"`, which the previous backtick-immediately-
    # followed-by-"scripts/" anchor never matched, so this check silently never validated
    # either shell script's path despite SKILL.md claiming it does.
    skill_relative = (
        r'`"?(?:\$\{CLAUDE_PLUGIN_ROOT\}/)?((?:references|scripts)/[\w./-]+\.(?:md|py|sh))"?`'
    )
    for match in re.finditer(skill_relative, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))

    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Two sub-checks, both born from a real gap: a 2026-08 security review found
    # Bash(git submodule:*) and Bash(git show:*) had both "passed" this function despite
    # being over-broad/unused in practice, because the original version searched the whole
    # body as prose -- a bare mention like "as data, not instructions" was enough to count
    # as "used," and a grant's own text matching as a substring of a narrower demonstrated
    # command (or vice versa) was never distinguished from an exact-scope match.
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.*/${} -]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    # Sub-check 1: only count a grant as "used" if it's actually invoked inside a fenced
    # ```bash block -- a prose/inline-only mention (no fenced invocation at all) doesn't
    # demonstrate the command is really needed.
    bash_blocks = "\n".join(re.findall(r"```bash\n(.*?)```", body, re.DOTALL))

    def next_token(cmd: str) -> list:
        # Whatever immediately follows the grant on its own line/statement, e.g. "status"
        # in "git submodule status" or "<file>" in "git checkout --ours <file>". The
        # preceding-character class includes a literal quote -- the script-path grants are
        # always invoked as a quoted string (e.g. "${CLAUDE_PLUGIN_ROOT}/scripts/x.sh").
        return re.findall(rf'(?:^|[;&|"]|\s){re.escape(cmd)}(\S*)', bash_blocks, re.MULTILINE)

    def is_placeholder(tail: str) -> bool:
        # A real invocation's own argument (a file path, branch name, ref) rather than a
        # further literal subcommand word the grant itself doesn't cover. `<...>`/`$...`
        # placeholders and a bare trailing nothing (grant used exactly as-is) both count;
        # a literal word like "status" does not -- known limitation: a literal-looking
        # example argument (e.g. "path/to/submodule") also reads as non-placeholder, so
        # this only fires when *every* demonstrated use shares the same literal extra word.
        tail = tail.strip().strip("\"'")
        return tail == "" or "<" in tail or "$" in tail

    unused = []
    overbroad = []
    for cmd in granted_cmds:
        tails = next_token(cmd)
        if not tails:
            unused.append(cmd)
            continue
        # Sub-check 2: if the grant is never once demonstrated at its own exact scope (no
        # extra literal word beyond it), it's broader than what the body actually needs.
        if all(not is_placeholder(t) for t in tails):
            overbroad.append(f"'{cmd}' (only ever shown as '{cmd} {tails[0]}')")

    if unused or overbroad:
        parts = []
        if unused:
            parts.append(
                "never invoked inside a fenced bash block: " + ", ".join(sorted(set(unused)))
            )
        if overbroad:
            parts.append("broader than their only demonstrated invocation: " + ", ".join(overbroad))
        return False, "Bash grant(s) " + "; and ".join(parts)
    return (
        True,
        "every granted Bash command is invoked inside a fenced bash block, at the granted scope",
    )


def check_step_sequence():
    # Scoped to the "## Workflow" section's "### Step N" headers only -- other numbered
    # lists elsewhere in the file (e.g. resolution sub-steps, Decision Tracking's example)
    # legitimately restart their own numbering, which a whole-file scan would wrongly flag.
    # The comment always said this; an earlier version of the code below didn't actually slice
    # to the section first, so it was a dormant bug (harmless only because no other section in
    # this particular file happens to use a "### Step N:"-shaped heading).
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Workflow\n")
    if start == -1:
        return True, "no '## Workflow' section found (skip)"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^### Step (\d+):", section, re.MULTILINE)]
    if not numbers:
        return True, "no '### Step N' headers found (skip)"
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        return False, f"step numbering not sequential: found {numbers}, expected {expected}"
    return True, "step headers sequential"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_step_sequence,
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
