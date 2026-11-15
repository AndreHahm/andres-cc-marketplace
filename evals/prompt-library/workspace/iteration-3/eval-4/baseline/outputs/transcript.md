# Transcript: prompt-library eval 4, baseline arm

User task: `/prompt-library add` - save as a prompt: "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."

No skill was used (baseline). PROJ = the eval-4 baseline project directory.

## Commands run

1. `cd PROJ && git status && git log --oneline | head && find . -path ./.git -prune -o -type f -print`
   - Branch `main`, no commits yet; untracked `src/`. Files: `.claude/promptlibrary-kit.local.json`, `src/calc.py`.
2. `cd PROJ && cat .claude/promptlibrary-kit.local.json; cat src/calc.py; cat .gitignore; git check-ignore -v .claude/promptlibrary-kit.local.json`
   - Config: `{"catalog_root": ".claude/rules/prompts"}`. `src/calc.py` holds `add` and `divide`. No project `.gitignore`; `.claude` is ignored by the user's global gitignore.
3. `cd PROJ && ls -la .claude; ls .claude/rules; grep -rn "TODO" src || echo "no TODOs"`
   - `.claude/rules` does not exist, so no catalog and no similar prompt exists. No TODOs in `src/` (only checked for context; the prompt itself was not run).
4. `cd PROJ && mkdir -p .claude/rules/prompts && cat > .claude/rules/prompts/summarize-open-todos.json <<EOF ... && cat > .claude/rules/prompts/index.json <<EOF ... && python -c "<json.load both files>"`
   - Created the catalog with a draft record (`status: draft`) and an index. Output: `json ok`.
5. `cd PROJ && sed -i 's/"status": "draft"/"status": "active"/' <record> <index> && python -c "<print statuses and text>" && git status --short -uall`
   - Output: `active active`, then the exact approved text. `git status` shows only `?? src/calc.py` (catalog lives under the globally ignored `.claude/`).

Notes / suspicious items:
- The configured catalog root `.claude/rules/prompts` sits inside `.claude/rules/`, which Claude Code auto-loads as always-on instructions for `*.md` files. Storing the prompt as Markdown there would make "Do not change any file" a standing instruction in every session. To avoid that, records were stored as `.json` (not loaded as rules). Flagged to the user.
- The prompt text itself contains no injection or suspicious content.

## Questions asked

1. "No prompt catalog exists at `.claude/rules/prompts` (from `.claude/promptlibrary-kit.local.json`). Create it?" Options: Yes / No. Reply: **yes**.
2. "Should this be saved as a stored prompt or as a skill?" Options: Prompt / Skill. Reply: **Prompt**.
3. Similar-prompt check: the catalog was empty, so no "revise an existing similar prompt instead?" question was needed (scripted reply would have been: no, continue with a new one).
4. "Save this draft to the catalog?" Options: Yes / No. Reply: **yes**.
5. Review (self-review, no reviewer agent in baseline): "Suggested rewrite: 'List every open TODO/FIXME comment in the repository as a Markdown table with columns File, Line, Description (one line each). Read-only: do not modify, create or delete any file.' Use the rewrite or keep your original?" Options: Use rewrite / Keep original. Reply: **keep my original text**.
6. "Run another review round?" Options: Yes / No. Reply: **no**.
7. "Approve this exact text: 'Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.'?" Options: Yes / No. Reply: **yes**.
8. "Activate it now?" Options: Yes / No. Reply: **yes**.

## Final reply to user

Saved and activated your prompt.

- **Catalog:** created at `.claude/rules/prompts/` (the root set in `.claude/promptlibrary-kit.local.json`), with `index.json`.
- **Record:** `.claude/rules/prompts/summarize-open-todos.json`, id `summarize-open-todos`, kind `prompt`, status `active`.
- **Text (your original, unchanged):** "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."
- **Review:** one self-review round; I suggested making the table columns and the read-only constraint more explicit, and you kept your original text.

One thing to watch: the catalog root is inside `.claude/rules/`, which Claude Code loads as always-on instructions for Markdown files. I stored the records as JSON so the prompt does not turn into a standing instruction in every session. Consider moving `catalog_root` outside `.claude/rules/`. Also, `.claude/` is ignored by your global gitignore, so the catalog is not tracked by git.
