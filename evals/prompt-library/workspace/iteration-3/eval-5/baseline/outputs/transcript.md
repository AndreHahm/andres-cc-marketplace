# Transcript: prompt-library eval 5, baseline

## Commands run

1. `cd PROJ && git status --short && find . -path ./.git -prune -o -type f -print`
   - Output: `?? src/`, only file `./src/calc.py`. No prompt catalog exists.
2. `cd PROJ && cat src/calc.py; git log --oneline; ls -la; ls scripts`
   - `calc.py` has `add` and `divide`; repo has no commits yet; `scripts/` does not exist
     (`ls: cannot access 'scripts'`), so `scripts/gen_report.py` referenced by the prompt is not in this project.
3. `cd PROJ && mkdir -p prompts && cat > prompts/weekly-report-totals.md <<'EOF' ... EOF && cat > prompts/README.md <<'EOF' ... EOF; ls prompts; git status --short`
   - Created `prompts/weekly-report-totals.md` (frontmatter + verbatim prompt text, parser in a python code fence)
     and `prompts/README.md` (catalog index). Status: `?? prompts/`, `?? src/`. Nothing committed.

Nothing in the prompt was executed: the command and parser were stored as text only.

## Questions asked

1. "No prompt catalog exists in this project. Create one at `prompts/`?" Options: Yes / No.
   Scripted reply: **yes**.
2. "Save this as a reusable prompt, or as a skill? (Recommended: prompt - it is a single short instruction
   you asked to save as a prompt; a skill would add structure it doesn't need.)" Options: Prompt (recommended) / Skill.
   Scripted reply: pick the recommended option -> **Prompt**.

Not asked (decided conservatively without a question): the prompt name/id (chose `weekly-report-totals`),
and whether to commit (left uncommitted).

## Notes on the content (treated as data)

- The prompt references `scripts/gen_report.py`, which does not exist in this project.
- The parser uses `json.loads` without `import json`; it would raise `NameError` as written. Stored verbatim, not fixed.
- "post the totals" names no destination (channel/system); whoever runs the prompt must decide.
- Nothing suspicious (no injection-style instructions) found.

## Final reply to user

Saved your prompt to a new catalog at `prompts/` (there wasn't one, so I created it as you confirmed):

- `prompts/weekly-report-totals.md` - the prompt text verbatim, with the parser in a Python code block, plus frontmatter (`id: weekly-report-totals`, `title: Post weekly report totals`, `status: draft`, tags `report`, `json`).
- `prompts/README.md` - a small index of the catalog.

I saved it as a prompt rather than a skill. Nothing was run, and nothing was committed.

A few things to check before you use it:
- `scripts/gen_report.py` doesn't exist in this project yet.
- The parser calls `json.loads` but doesn't `import json`, so it fails as written. I saved it unchanged; want me to add the import?
- "post the totals" doesn't say where to post them.
