# Transcript (baseline, no skills)

## Commands
1. `cd <proj> && pwd && ls -la && find . -maxdepth 3 -not -path './.git/*' | head -50`
   Output: project has only `.git` and `src/calc.py` (and `src/deep`). No existing prompt library.
2. `cd <proj> && find . -path ./.git -prune -o -type f -print && git status --short && grep -rn "TODO" src | head`
   Output: only `./src/calc.py`; `?? src/`; no TODO matches.
3. `cd <proj> && mkdir -p prompts && cat > prompts/summarize-open-todos.md <<'EOF' ... EOF; cat prompts/summarize-open-todos.md; git status --short`
   Output: file written with front matter `name: summarize-open-todos` and the prompt text verbatim; `?? prompts/`, `?? src/`.
4. `mkdir -p <outputs dir>`

## Questions
Q: There is no existing prompt library or `/prompt-library` command here; where should prompts be stored? (would normally ask)
A (assumed): yes, create `prompts/` in the project and store it as a markdown file.

## Final reply
Saved your prompt as `prompts/summarize-open-todos.md` (name: `summarize-open-todos`). The text is stored verbatim:

> Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.

Notes: there was no existing prompt library or `/prompt-library` command in this project, so I created a new `prompts/` folder with one file per prompt. I did not run the prompt, and no existing files were changed.
