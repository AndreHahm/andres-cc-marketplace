# Transcript (baseline)

## Commands
1. `cd <proj> && pwd && ls -la && find . -type f -not -path './.git/*' | head -50`
   Output: files `.claude/promptlibrary-kit.local.json`, `src/calc.py`.
2. `cd <proj> && cat .claude/promptlibrary-kit.local.json && cat src/calc.py && git status --short`
   Output: `{"catalog_root": ".claude/rules/prompts"}`; calc.py has add/divide, no TODOs; `?? src/`.
3. `cd <proj> && mkdir -p .claude/rules/prompts && cat > .claude/rules/prompts/summarize-open-todos.md <<EOF ... EOF; cat ...; git status --short`
   Created the prompt file with frontmatter (name, description) and the prompt text verbatim.

## Questions
Q: Name for the prompt? Assumed reply: yes, `summarize-open-todos`.

## Final reply
Saved the prompt to `.claude/rules/prompts/summarize-open-todos.md` (catalog root from `.claude/promptlibrary-kit.local.json`). The body is your text verbatim: "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file." I named it `summarize-open-todos`, with a short description in the frontmatter. No other files were touched.
