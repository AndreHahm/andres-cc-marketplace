# Transcript (baseline, eval-10)

## Commands
1. `cd <proj> && pwd && ls -la && find . -maxdepth 3 -not -path './.git/*' | head -50`
   - Output: .git, src/calc.py, src/deep (empty dir). No prompt library exists.
2. `cd <proj> && find . -not -path './.git/*' -type f && cat src/calc.py; ls -a ~/.claude/commands`
   - Output: only src/calc.py (add, divide). No existing prompt-library convention.
3. `cd <proj> && mkdir -p prompts && cat > prompts/summarize-open-todos.md <<EOF ... EOF; cat prompts/summarize-open-todos.md`
   - Created prompts/summarize-open-todos.md with frontmatter (name, description) and the prompt text verbatim.
4. `mkdir -p <outputs dir>` and wrote this transcript.

## Questions
Q: No prompt library exists and "/prompt-library" is not a known command here; store as a markdown file under prompts/ in the project?
Assumed reply: yes.

## Final reply
I couldn't find a prompt-library command or existing library in this project, so I created one: I saved your prompt as `prompts/summarize-open-todos.md` (name `summarize-open-todos`, with a short description and your text verbatim). No other files were touched. If you use a different storage location or format, tell me and I'll move it.
