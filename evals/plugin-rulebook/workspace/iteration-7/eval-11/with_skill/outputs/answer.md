# R37 (Executable Bit: Directly-Invoked Scripts) assessment

R37 is REQUIRED and on by default. It applies to newly-created or structurally-modified skills, commands and hooks. It applies to a script that is run directly by path, and the committed git mode (from `git ls-files -s`) must be `100755`.

## guard.sh (hook)

- **Finding: yes.** The hook `command` is a bare path (`"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/guard.sh"`), so it counts as a direct invocation. The committed mode is `100644`, not `100755`.
- **`"shell": "bash"` does not exempt it.** `bash -c '"/path/x.sh"'` on a mode-644 file fails with `Permission denied` (exit 126). `"shell": "bash"` solves a different problem (Windows without Git Bash), and the hook needs both that setting and the executable bit. R37 checks only the executable bit. Whether `"shell": "bash"` is set is left to `hook-reviewer`.
- **Severity: REQUIRED, so FAIL.** It blocks finalization.
- **Which mode source counts:** the committed mode from `git ls-files -s guard.sh` (`100644`). The author's `ls -l` showing it executable does not count. A checkout with `core.fileMode=false` ignores local permission changes, so the file can look executable on disk while the committed mode is still 644 (issue #212).
- **Fix:** run `git update-index --chmod=+x <path>` (plus `chmod +x <path>` for the working copy), in every mirrored copy of the script. Re-check with `git ls-files -s` until it shows `100755`.

## tool.py (skill)

- **Finding: no.** `allowed-tools: Bash(python:*)` names an interpreter, which is not a direct invocation. The script runs as `python scripts/tool.py`, and the interpreter reads the file, so the executable bit is not needed. R37 does not check such a grant. Mode `100644` is acceptable here.
- **Severity:** none (PASS for R37).
- **Which mode source would count:** if tool.py were ever invoked directly (for example with a grant `Bash(${CLAUDE_SKILL_DIR}/scripts/tool.py:*)`), the `git ls-files -s` mode would count, not the disk.
- **Fix:** none required. Do not chmod it just for R37.

## Summary

| Script | R37 finding | Severity | Mode source | Fix |
|---|---|---|---|---|
| guard.sh | Yes (644, bare-path hook command; `shell: bash` no exemption) | REQUIRED / FAIL | `git ls-files -s`, not `ls -l` | `git update-index --chmod=+x` (and `chmod +x`), all mirrors, re-check |
| tool.py | No (interpreter grant `Bash(python:*)`) | n/a | `git ls-files -s` if it were checked | none |
