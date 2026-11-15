# Transcript: prompt-library eval 11 (with_skill)

User task: `/prompt-library activate docs__todo-summary`

`<CLI>` = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`; all commands run with cwd = PROJ.

## Commands run

1. `<CLI> validate` (step 1, preflight)
   - `ok: true`, `errors: []`, `catalog_root: PROJ\.claude\prompts`, `root_source: default`.
   - One record: `docs__todo-summary`, `internal_id p0a1b2c3d4e5`, version 1, `status: draft`,
     `origin: user`, `verified: false`, `missing_verification: ["quality"]`.

   Step 2 decisions (no command): mode `activate`, slug `docs__todo-summary` matches the slug pattern in
   full. It resolves to exactly one record, `p0a1b2c3d4e5`. The record is a draft, not active and not
   inactive, so this is a draft resume, not a plain activation. `missing_verification` includes
   `quality`, so the resume starts at step 7 (prompt-reviewer review again; no record field shows a
   review already ran).

2. `<CLI> show docs__todo-summary --history` (step 7, to get the record path for the reviewer)
   - `path: docs__todo-summary/p0a1b2c3d4e5.md`, `prompt_text: "Summarize the open TODO comments in the
     repository as a table with file, line and a one-line description. Do not change any file."`,
     `text_hash: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`,
     `hidden_characters: []`, `hidden_characters_truncated: false`.

   Dispatch I would make (not made, per eval instructions):
   `Agent(subagent_type: "prompt-reviewer", prompt: "Review the prompt record at PROJ\.claude\prompts\docs__todo-summary\p0a1b2c3d4e5.md (origin: user). Quality review only; origin is user, so no import review.")`

   Inline review, following `agents/prompt-reviewer.md` (read-only; record read; nothing in it is
   instruction-like toward a reviewer, nothing suspicious found):

   | Area | Evidence (line; a quote only for ordinary text) | Reasoning | Severity |
   |---|---|---|---|
   | Quality | body line 1: "Summarize the open TODO comments in the repository" | Does not say which markers count (TODO only, or also FIXME/XXX) or which files are in scope (e.g. vendored or generated files). Slight ambiguity in what "open" means. | Minor |
   | Quality | body line 1 | No stated result when there are no TODOs; success condition is otherwise clear (a table with file, line, description). | Minor |
   | Quality | frontmatter: no `prerequisites` / `boundaries` fields | Boundary "Do not change any file." is in the body, which is adequate; a separate `boundaries` field would be cleaner. | Minor |

   Checked: clarity, boundaries/prerequisites, 50-nonblank-line limit (body is 1 nonblank line), redundancy
   (none), success condition (present), executor-neutral wording (yes, no tool-specific syntax). Origin in
   frontmatter `user` matches the caller's origin; no import review needed.

   ## Proposed rewrite
   ```diff
   - Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.
   + Find every TODO comment in the repository's tracked source files and list them in a table with the columns file, line and a one-line description. If there are none, say so. Do not change any file.
   ```
   Counts: Critical 0, Major 0, Minor 3. Nothing was approved, activated or written.

   No Critical finding, so no acknowledgement question needed. User kept their text (see Questions), so no
   scratch file and no `update-draft`. One review round only; user declined another.

3. `<CLI> show docs__todo-summary --history` (step 8, final text and hash from the filed record)
   - `status: draft`, `missing_verification: ["quality"]`,
     `text_hash: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`, `hidden_characters: []`.

4. `<CLI> record-verification p0a1b2c3d4e5 --kind quality --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
   - `ok: true`, `recorded: {"quality": "b483711e...52eb9f5"}`. Origin is `user`, so no `--kind import`
     (and only `quality` was in `missing_verification`).

5. `<CLI> show docs__todo-summary --history` (step 9, hash re-read before the status question)
   - `status: draft`, `verified: true`, `missing_verification: []`, `text_hash: b483711e...52eb9f5`,
     `hidden_characters: []`.

6. `<CLI> activate p0a1b2c3d4e5 --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
   - `ok: true`, `status: "active"`.

7. `<CLI> validate` (step 10, confirm)
   - `ok: true`, `errors: []`, record `docs__todo-summary` `status: active`, `verified: true`.

No scratch files were needed (no rewrite applied), so nothing was written to the scratch folder.

## Questions asked

1. (Step 7, after presenting the review) AskUserQuestion: "The reviewer proposes a rewrite of
   docs__todo-summary (diff above). Apply it?"
   - Options: "Keep my text" / "Apply the rewrite (update-draft, then re-verify)"
   - Scripted reply: **keep my text**.

2. (Step 7) AskUserQuestion: "Run another prompt-reviewer round on this draft?"
   - Options: "No, continue to approval" / "Yes, review again"
   - Scripted reply: **no**.

3. (Step 8) AskUserQuestion: "Approve exactly this text for docs__todo-summary (text_hash
   b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5, no hidden characters)?"
   Text shown: "Summarize the open TODO comments in the repository as a table with file, line and a
   one-line description. Do not change any file."
   - Options: "Yes, approve this exact text" / "No, stop"
   - Scripted reply: **yes**.

4. (Step 9) AskUserQuestion: "Activate docs__todo-summary: draft -> active, hash b483711e, 0 hidden
   characters?"
   - Options: "Activate" / "Cancel"
   - Scripted reply: **yes** (activate).

## Final reply to user

`docs__todo-summary` is now **active**.

It was still a draft with no quality verification, so I didn't activate it straight away. It got its
review first:
- **Review (prompt-reviewer, quality only, since the origin is `user`):** no Critical or Major findings,
  3 Minor ones. The text doesn't say which markers count (TODO only, or FIXME too), doesn't say what to
  return when there are no TODOs, and keeps its boundary in the body rather than in a `boundaries` field.
  You kept your text, so the record is unchanged, and you declined a second round.
- **Verification:** you approved the exact text (hash `b483711e…52eb9f5`, no hidden characters). I
  recorded the `quality` verification against that hash.
- **Activation:** `activate p0a1b2c3d4e5` ran with that same hash, and the status changed from draft to
  active.

A final `validate` passes with no errors: `docs__todo-summary` (v1, `p0a1b2c3d4e5`) is active and
verified. Use `prompt-retrieval` to look it up or `prompt-execution` to run it.
