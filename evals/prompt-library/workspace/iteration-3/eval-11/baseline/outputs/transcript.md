# Transcript: prompt-library eval 11, baseline

User task: `/prompt-library activate docs__todo-summary`

## Commands run

1. `cd PROJ && git status && git log --oneline | head && find . -path ./.git -prune -o -type f -print`
   - On branch main, no commits yet; `src/` untracked.
   - Files: `.claude/prompts/catalog.yaml`, `.claude/prompts/docs__todo-summary/p0a1b2c3d4e5.md`, `src/calc.py`.
2. `cd PROJ && cat .claude/prompts/catalog.yaml; cat .claude/prompts/docs__todo-summary/p0a1b2c3d4e5.md; cat src/calc.py; git check-ignore -v .claude/prompts/catalog.yaml`
   - catalog.yaml: `catalog_version: 1`, `scope: repo`, `snapshot_id: 5ef178170aac`, one record `docs__todo-summary/p0a1b2c3d4e5.md`.
   - Record frontmatter: name "TODO summary", area docs, slug docs__todo-summary, internal_id p0a1b2c3d4e5, version 1, `status: draft`, origin user.
   - Body: "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."
   - `.claude` is ignored by the user's global gitignore (`~/.gitignore_global:198`), so the catalog is not tracked by git.
   - Nothing suspicious in the prompt text: it is read-only and contains no embedded instructions aimed at the agent.
3. (After approval) `cd PROJ && sed -i 's/^status: draft$/status: active/' .claude/prompts/docs__todo-summary/p0a1b2c3d4e5.md && head -10 ... && git status --short`
   - Frontmatter now shows `status: active`; body unchanged; version stays 1. `git status --short` shows only `?? src/` (catalog is gitignored).

## Questions asked

Inline review (no reviewer tool used; my own read of the draft): the prompt is clear, scoped and explicitly read-only. Minor suggestion: also cover FIXME/XXX markers and say what to output when no TODOs exist.

1. Question: "A review suggests this rewrite: 'Summarize the open TODO, FIXME and XXX comments in the repository as a table with file, line and a one-line description. If there are none, say so. Do not change any file.' Use the rewrite or keep your text?"
   - Options: Use the rewrite / Keep my text
   - Scripted reply: **Keep my text.**
2. Question: "Run another review round on the text?"
   - Options: Yes, review again / No
   - Scripted reply: **No.**
3. Question: "Approve this exact text for docs__todo-summary (version 1): 'Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.'"
   - Options: Yes, approve / No
   - Scripted reply: **Yes.**
4. Question: "Activate docs__todo-summary now (status draft -> active)?"
   - Options: Activate / Cancel
   - Scripted reply: **Yes.**

## Final reply to user

`docs__todo-summary` (TODO summary, internal id `p0a1b2c3d4e5`) is now active.

- I changed one field: `status: draft` to `status: active` in `.claude/prompts/docs__todo-summary/p0a1b2c3d4e5.md`. The prompt text is exactly the version you approved, and the version stays at 1.
- You kept your original text, so the suggested rewrite (adding FIXME/XXX and a "none found" case) was not applied. No further review round was run.
- I left `catalog.yaml` alone, `snapshot_id: 5ef178170aac` included. The record path didn't change, and I don't know how the snapshot id is computed. If your tooling expects it to change when a record's status changes, it needs regenerating.
- `.claude/` is ignored by your global gitignore, so git doesn't track this change.
- Nothing else in the project was touched.
