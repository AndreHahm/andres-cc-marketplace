# Transcript: prompt-library eval 3, baseline arm

## Commands run

1. `cd PROJ && git status --short && git log --oneline | head && find . -path ./.git -prune -o -type f -print`
   - `?? src/`; "your current branch 'main' does not have any commits yet"; only file: `./src/calc.py`.
2. `cd PROJ && cat src/calc.py; ls -la; ls -la .claude`
   - calc.py has `add` and `divide`, no TODO comments. No `.claude/` directory -> no prompt catalog exists.
3. `cd PROJ && grep -rniE "prompt|catalog" --exclude-dir=.git .`
   - No matches (rc=1): no existing catalog and no similar prompt.
4. Created `.claude/prompts/summarize-open-todos.md` (frontmatter: id, title, type: prompt, status: draft, version 1, created, tags; body = the user's exact text) and `.claude/prompts/catalog.json` (index with one entry, status draft). Verified JSON parses: `draft`.
5. Self-review of the draft (no reviewer tool used in baseline): text is clear, read-only constraint explicit. Possible rewrite considered (also cover FIXME/XXX, define "open", sort by file) -> user kept original text.
6. `sed -i 's/^status: draft$/status: active\napproved: 2026-11-15/' .../summarize-open-todos.md && sed -i 's/"status": "draft"/"status": "active"/' .../catalog.json && cat ... && python -c "...json.load..." && git status --short`
   - Record now `status: active`, `approved: 2026-11-15`; body unchanged; catalog entry `status: active`. `git status` still only shows `?? src/`.
7. `git check-ignore -v .claude/prompts/catalog.json`
   - Ignored by the user's global gitignore (`~/.gitignore_global:198:.claude`), so the catalog is not visible to git.

No suspicious content found in files read (calc.py is plain code; the prompt text is a benign read-only request).

## Questions asked

1. "No prompt catalog exists in this project. Create one at `.claude/prompts/`?" Options: Yes / No. Reply: **yes**.
2. "Save this as a reusable prompt, or as a skill?" Options: Prompt / Skill. Reply: **Prompt**.
3. Similar-prompt check: none found, so the "revise an existing prompt instead?" question did not arise (scripted reply would have been: no, continue with a new one).
4. "Save this draft to the catalog as `summarize-open-todos` (status: draft)?" Options: Yes / No. Reply: **yes**.
5. "Review suggests an optional rewrite (also include FIXME/XXX markers, define 'open', sort by file then line). Use the rewrite or keep your original text?" Options: Use rewrite / Keep original. Reply: **keep my original text**.
6. "Run another review round?" Options: Yes / No. Reply: **no**.
7. "Approve this exact text: 'Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.'?" Options: Yes / No. Reply: **yes**.
8. "Activate the prompt now so it can be retrieved and used?" Options: Yes / No. Reply: **yes**.

## Final reply to user

Saved and activated your prompt.

- **Catalog:** created a new prompt catalog at `.claude/prompts/` (none existed before), with an index at `.claude/prompts/catalog.json`.
- **Record:** `.claude/prompts/summarize-open-todos.md`, id `summarize-open-todos`, type prompt, version 1, status **active** (approved 2026-11-15).
- **Text (your original, unchanged):** "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."
- No similar prompt existed, so this is a new entry. The review's optional rewrite was not applied, per your choice.

One thing to know: `.claude/` is ignored by your global gitignore (`~/.gitignore_global`), so git does not see the catalog. If you want it versioned with the project, add a `!.claude/prompts/` exception to the project's `.gitignore` or move the catalog. Nothing else in the project was changed.
