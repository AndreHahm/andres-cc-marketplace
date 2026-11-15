# Transcript: prompt-library eval 16, baseline

## Commands run

1. `cd PROJ && git status --short && git log --oneline | head -5 && find . -type f`
   - Output: `?? src/`; no commits yet; only file `./src/calc.py`.
2. `cd PROJ && cat src/calc.py; ls -la; ls scripts`
   - Output: `calc.py` has `add` and `divide`; no prompt catalog exists; `scripts/` does not exist (so `scripts/gen_report.py` is missing).
3. `cd PROJ && mkdir -p prompts && cat > prompts/summarize-weekly-report-totals.md <<EOF ... && cat > prompts/index.json <<EOF ... && python -c "import json;json.load(open('prompts/index.json'))"`
   - Created the catalog (`prompts/index.json`) and the draft record (status `draft`) with the user's text verbatim. Output: `ok` (index is valid JSON).
4. `cd PROJ && sed -i 's/^status: draft$/status: active\napproved: 2026-11-15/' prompts/summarize-weekly-report-totals.md && sed -i 's/"status": "draft"/"status": "active"/' prompts/index.json && head -8 ... && grep status prompts/index.json && python -c json-check && git status --short`
   - Output: record shows `status: active`, `approved: 2026-11-15`; index shows `"status": "active"`; JSON `ok`; `git status`: `?? prompts/`, `?? src/`. Nothing committed.

Duplicate check: no catalog existed, so there were no existing prompts to compare against.

Note on data: the prompt text instructs a future run to execute a shell command (`python scripts/gen_report.py --since last-week`). Not suspicious in intent, but the script does not exist in this project, and executing the prompt runs code; recorded as a note in the record. I did not run the command.

## Questions asked

1. "No prompt catalog exists in this project. Create one at `prompts/`?" Options: Yes / No. Reply: **yes**.
2. "Save this as a reusable prompt or as a skill?" Options: Prompt / Skill. Reply: **Prompt**.
3. "A similar prompt already exists, revise it instead?" Not asked: the catalog was new and empty, so no similar prompt existed (the scripted reply "no, continue with a new one" would have applied).
4. "Save this draft to the catalog?" Options: Yes / No. Reply: **yes**.
5. "Review suggests a rewrite: add 'If the script is missing or fails, report the error instead of guessing totals.' Use the rewrite or keep your original?" Options: Use rewrite / Keep original. Reply: **keep my original text**.
6. "Run another review round?" Options: Yes / No. Reply: **no**.
7. "Approve this exact text: `Run \`python scripts/gen_report.py --since last-week\` and summarize the totals it prints in three bullet points.`?" Options: Yes / No. Reply: **yes**.
8. "Activate it now (status `active`)?" Options: Yes / No. Reply: **yes**.

## Final reply to user

Saved and activated your prompt.

- Catalog created: `prompts/index.json` (new; none existed before).
- Record: `prompts/summarize-weekly-report-totals.md`, id `summarize-weekly-report-totals`, type prompt, status **active**, approved 2026-11-15.
- Text stored exactly as you gave it: "Run `python scripts/gen_report.py --since last-week` and summarize the totals it prints in three bullet points."
- The review suggested adding an instruction to report an error if the script is missing or fails; you kept your original text, so that was not applied.

One thing to know: `scripts/gen_report.py` does not exist in this project yet, so running the prompt will fail until you add it. Running the prompt also executes that script. I did not run it. The new files are untracked; nothing was committed.
