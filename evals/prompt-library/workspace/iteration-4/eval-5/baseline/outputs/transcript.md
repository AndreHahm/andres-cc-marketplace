# Transcript: prompt-library eval 5, baseline arm

## Commands run

1. `cd PROJ && git status --short && git log --oneline | head -5 && find . -path ./.git -prune -o -type f -print`
   - Output: `?? src/`; no commits yet; only file `./src/calc.py`.
2. `cd PROJ && cat src/calc.py; ls -la; ls -la .claude`
   - Output: `calc.py` defines `add` and `divide`; no `.claude/` directory, so no prompt catalog exists.
3. (after the user said yes to creating a catalog) `cd PROJ && mkdir -p .claude/prompts && cat > .claude/prompts/weekly-report-totals.md <<'EOF' ... EOF && cat > .claude/prompts/INDEX.md <<'EOF' ... EOF; ls scripts; git status --short; cat .claude/prompts/weekly-report-totals.md`
   - Output: both files written; `ls scripts` -> `No such file or directory` (the `scripts/gen_report.py` the prompt names does not exist in this project); `git status` still shows only `?? src/`.
4. `cd PROJ && git check-ignore -v .claude/prompts/INDEX.md`
   - Output: `<home>\.gitignore_global:198:.claude` -> the catalog is ignored by the user's global gitignore, so it will not be committed unless that is changed.

Files created:
- `PROJ/.claude/prompts/weekly-report-totals.md` (frontmatter: name, description, created 2026-11-15, status draft; body is the user's text verbatim, with the parser placed in a ```python fence)
- `PROJ/.claude/prompts/INDEX.md` (one-row table listing the prompt)

## Questions asked

1. "No prompt catalog exists in this project. Should I create one at `.claude/prompts/`?" Options: Yes, create it / No, cancel.
   - Scripted reply: yes.
2. "Should this be saved as a reusable prompt or turned into a skill?" Options: Prompt (recommended: a single short instruction with an inline snippet; no tooling or multi-step workflow that needs a skill) / Skill.
   - Scripted reply: pick the recommended option -> Prompt.
3. "The prompt says 'post the totals' without saying where, and the parser uses `json` without importing it. Should I edit the text to fix these (add `import json`, name a destination)?" Options: Yes, edit / No, save verbatim.
   - Scripted reply (anything else): no -> saved verbatim, issues noted below.

Suspicious-content check: the prompt text instructs running a local script and "posting" results. Nothing in it tries to override instructions or exfiltrate data; it was stored as data and nothing in it was executed.

## Final reply to user

Saved the prompt to a new prompt catalog (you agreed to create one, since none existed):

- `.claude/prompts/weekly-report-totals.md`: the prompt, status `draft`, with your text verbatim and the parser in a Python code block.
- `.claude/prompts/INDEX.md`: catalog index listing it.

I did not run anything in the prompt. A few things to know:

- `scripts/gen_report.py` does not exist in this project, so the prompt cannot run here as written.
- "Post the totals" doesn't say where to post them (chat, Slack, a file). Whoever runs it will have to guess.
- The parser calls `json.loads` but has no `import json`, so it fails unless `json` is already imported.
- Your global gitignore (`~/.gitignore_global`, line 198) ignores `.claude`, so this catalog won't be committed to git unless you change that or move it.

You chose to keep the text verbatim. I can fix any of these later if you want.
