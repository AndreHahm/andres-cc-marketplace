# Transcript: prompt-library eval 12, with_skill

User task: `/prompt-library activate docs__todo-summary`

`<CLI>` = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`. Every command ran with `cd PROJ` first.

Step notes:
- Step 2: mode `activate`, slug `docs__todo-summary` matches the slug pattern in full, so it was accepted.
- The record is a `draft` (not `active`), so the "already active" stop does not apply. Because `activate` names a draft, it resumes by its state. `missing_verification` = `["import"]` only, so it resumes at **step 8**. Steps 3 to 7 are skipped, and `prompt-reviewer` is not dispatched, because `quality` is not missing. Only `--kind import` is recorded. `quality` is already bound to the current text, so it is not recorded again.
- No scratch files were needed: no intake and no rewrite.
- Nothing suspicious was found in the record text. It is a plain read-only instruction ("Do not change any file"), with no hidden characters.

## Commands run

1. `cd PROJ && <CLI> validate`
   - `ok: true`, `root_source: default`, `catalog_root: PROJ/.claude/prompts`, `errors: []`.
   - Record: `docs__todo-summary`, `internal_id p0a1b2c3d4e5`, v1, `status: draft`, `origin: session`, `verified: false`, `missing_verification: ["import"]`.

2. `cd PROJ && <CLI> show docs__todo-summary --history`
   - `ok: true`, `path: docs__todo-summary/p0a1b2c3d4e5.md`, `source_ref: {session_id: 3f2a9c1e-0000-4000-8000-000000000001, turns: "4-5"}`.
   - `prompt_text`: "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."
   - `text_hash: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`, `hidden_characters: []`, `hidden_characters_truncated: false`.

3. (after approval Q1) `cd PROJ && <CLI> record-verification p0a1b2c3d4e5 --kind import --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
   - `ok: true`, `recorded: {import: b483711e...52eb9f5}`.

4. (step 9 hash source) `cd PROJ && <CLI> show docs__todo-summary --history`
   - `ok: true`, `status: draft`, `verified: true`, `missing_verification: []`, `text_hash: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5` (unchanged), `hidden_characters: []`.

5. (after approval Q2) `cd PROJ && <CLI> activate p0a1b2c3d4e5 --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
   - `ok: true`, `status: active`.

6. `cd PROJ && <CLI> validate`
   - `ok: true`, `errors: []`. Record `docs__todo-summary` (`p0a1b2c3d4e5`) has `status: active`, `verified: true`, `missing_verification: []`.

## Questions asked

Q1 (step 8, AskUserQuestion):
- Shown first: origin `session` (source session `3f2a9c1e-0000-4000-8000-000000000001`, turns 4-5), the full prompt text from the filed record, and `text_hash b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`. No hidden characters.
- Question: "Approve exactly this text (hash b483711e...) for docs__todo-summary? This records its import verification, the only kind still missing."
- Options: "Approve this exact text" / "Do not approve (stop)".
- Scripted reply: **yes** (approve this exact text).

Q2 (step 9, AskUserQuestion):
- Question: "Activate docs__todo-summary: draft -> active, text hash b483711e? (0 hidden characters)"
- Options: "Activate it" / "Cancel".
- Scripted reply: **yes** (activate it).

No other questions were asked. The script covered every question.

## Final reply to user

`docs__todo-summary` is now **active**.

- Record: `p0a1b2c3d4e5`, version 1, origin `session` (session `3f2a9c1e-0000-4000-8000-000000000001`, turns 4-5).
- Text: "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."
- It was a draft from an interrupted add that already had its quality verification. The only kind still missing was the import verification. After you approved the exact text (hash `b483711e...52eb9f5`, no hidden characters), I recorded the import verification against that hash. Then, with your approval, I activated it against the same hash.
- I did not run a new review or record quality again, because quality was already verified for this text.
- A final `validate` reports the catalog `ok` with no errors. The record is `active` and fully verified.

You can find it with `prompt-retrieval` and run it with `prompt-execution`.
