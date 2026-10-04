# Baseline transcript: /prompt-library add

Commands run (all from the project dir, `cd` first):
1. `pwd && ls -la && git status | head -5` -> project has .claude/prompts, src/calc.py; git: no commits yet.
2. `find .claude src -type f` -> catalog.yaml plus 4 prompt files (docs__changelog-entry, review__missing-tests, review__old-style, review__orphan-draft), src/calc.py.
3. `cat catalog.yaml` and every prompt .md -> learned record format (frontmatter name/area/slug/internal_id/version/short_description/status/origin/verification.quality, body after blank line). Orphan draft is not in the catalog.
4. sha256sum experiments on changelog body -> quality hash = sha256 of body with no trailing newline (matched 1adb7a93...).
5. Created `.claude/prompts/review__todo-summary/active.md` (id p000000000004, area review, status active, origin user, quality b483711e...) and appended it to catalog.yaml `records` via sed (placed after review__missing-tests).
6. `cat` of new file and catalog to verify.

Questions: none asked (no AskUserQuestion available). Assumed: area=review, name "TODO summary", id p000000000004, approved.

## Final reply
Saved the prompt as "TODO summary" (review__todo-summary, id p000000000004, status active) at .claude/prompts/review__todo-summary/active.md, and added it to .claude/prompts/catalog.yaml. The body is exactly your text. I chose the "review" area and wrote a short description, "Tabulate open TODO comments, read-only"; say if you want a different area or name. I computed the quality hash the same way the existing records do (sha256 of the body). I did not touch src/ or any other prompt. The catalog's snapshot_id is unchanged, since I don't know how it is derived.
