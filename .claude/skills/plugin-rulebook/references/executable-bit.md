# Executable Bit (R37)

Full detail for R37. `SKILL.md` carries the rule's statement and a pointer here. Forward-looking, like
R28-R30: checked on newly-created or structurally-modified skills and hooks.

## What is checked

A script that is run **directly by path**, rather than through an interpreter, must be committed with git
mode `100755`. Read the committed mode with `git ls-files -s <path>`, never from `ls -l`: a checkout with
`core.fileMode=false` (set on some of this repo's machines; this one reports `true`) makes git ignore a local
permission change, so a script can look executable on disk while the committed mode is `100644` (issue #212).

Two ways a script is run directly:

1. **A skill or command grant that names the script path** — `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/x.sh:*)`
   or `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/x.py:*)`. A grant naming an interpreter (`Bash(python:*)`,
   `Bash(bash:*)`) is not a direct invocation and is not checked. A grant is a permission, not proof of use:
   check it only when the skill's body or `references/*.md` invoke the script by that path. If that text runs it
   only through an interpreter (`python x.py`, `bash x.sh`), or never mentions it, report an informational
   note and leave the mismatched or unused grant to R6, not a REQUIRED FAIL.
2. **A hook `command` that is a bare path** — `"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/guard.sh"`, quoted or not,
   with nothing before it (`bash`, `python3`, `uv run`).

## No shell-selection exemption

A hook that sets `"shell": "bash"` is **not** exempt. Verified live: `bash -c '"/path/x.sh"'` on a mode-`644`
file fails with `Permission denied` (exit 126), because a shell running a path directly still needs the
executable bit. The two fixes in issue #305 solve different problems — `git update-index --chmod=+x` for
POSIX, `"shell": "bash"` for Windows without Git Bash — and a hook needs both. R37 checks only the first.
Whether a `.sh` hook command also sets `"shell": "bash"` is a separate concern, left to `hook-reviewer`.

## When the reviewer cannot read git

Reading the committed mode needs Bash (`git ls-files -s`). A reviewer without it — `plugin-rulebook-checker`
has `Read`, `Grep` and `Glob` only — confirms the script exists and reports R37 as `unverified`, never PASS.
`SKILL.md` grants `Bash(git ls-files:*)`, so a direct `plugin-rulebook` run can check it. Check the
`.claude/` mirror copy of each script too, not only the canonical one.

## Severity

REQUIRED. A committed mode other than `100755` on a directly-invoked script is a FAIL; a missing file is also
a FAIL (a grant or hook pointing at nothing).

## Fix

`git update-index --chmod=+x <path>` (and `chmod +x <path>` for the working copy), in every mirrored copy of
the script. Re-check with `git ls-files -s <path>`.
