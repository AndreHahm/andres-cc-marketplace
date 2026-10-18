# Eval 17 report (blind agent, with_skill)

Skill A (set_mode.py): no R37 finding. The grant begins with the interpreter python3, so the script runs through
an interpreter and needs no executable bit, whatever the committed 100644 mode. At most an informational note.
Do not chmod it.

Skill B (run.sh): REQUIRED FAIL. The path is the first word of the grant and the body runs it directly, and the
committed mode is 100644. Fix: `git update-index --chmod=+x` on the canonical script and on its `.claude/` mirror
copy if one exists, then re-check with `git ls-files -s`.
