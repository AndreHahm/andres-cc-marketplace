# Transcript: prompt-library eval 3, with_skill

PROJ = `<scratchpad>/fx/prompt-library/eval-3/with_skill/proj`
`<CLI>` = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`
SCRATCH = `.../scratchpad/runs/scratch/prompt-library-3-with_skill/draft.md` (under the system temp directory)

Mode: `add` (first word of `$ARGUMENTS`). Intake path: text typed/pasted by the user, so `origin: user`
(quality review only, no import review, no `source_ref`). Nothing suspicious or instruction-like aimed at the
assistant in the pasted text; it is a plain read-only instruction.

## Commands run

1. `cd PROJ && <CLI> validate` -> exit 1, `ok: false`, `errors: ["catalog.yaml is missing"]`,
   `catalog_root: PROJ\.claude\prompts`, `root_source: default`.
2. (after the user agreed to initialize) `<CLI> init` -> exit 0, `ok: true`, catalog_root `PROJ\.claude\prompts`.
3. `<CLI> validate` -> exit 0, `ok: true`, `catalog_version: 1`, `records: []`.
4. `<CLI> new-id` -> `{"ok": true, "internal_id": "p7b8e1f8929c3"}`.
5. `Write` SCRATCH (built from `assets/prompt-record-template.md`, no `REPLACE` / placeholder body left):
   ```yaml
   name: Summarize open TODO comments
   area: repo-maintenance
   slug: repo-maintenance__summarize-todo-comments
   internal_id: p7b8e1f8929c3
   version: 1
   short_description: Lists the open TODO comments in the repository as a table with file, line and a one-line description, without changing any file.
   status: draft
   origin: user
   boundaries: Read-only; not for fixing or removing the TODOs.
   ```
   Body: `Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.`
   (The template's `prerequisites` line was deleted, as the template instructs, since nothing is required.)
6. `<CLI> screen SCRATCH` -> exit 0, `{"ok": true, "matches": [], "note": ""}` (clean).
7. `<CLI> hash SCRATCH` -> `sha256: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`, `nonblank_lines: 1`.
8. Step 5 duplicate check (after triage answer "Prompt"): `validate`'s `records` was empty, so no record
   with the same area or a similar name/description exists; no revise-instead offer was needed.
9. (after the user approved filing) `<CLI> draft SCRATCH` -> exit 0, `ok: true`, `internal_id: p7b8e1f8929c3`,
   `path: repo-maintenance__summarize-todo-comments/p7b8e1f8929c3.md`,
   `text_hash: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`.
10. Step 7 dispatch I would make (not dispatched, per run instructions):
    `Agent(subagent_type: "prompt-reviewer", prompt: "Review record PROJ/.claude/prompts/repo-maintenance__summarize-todo-comments/p7b8e1f8929c3.md; caller-recorded origin: user")`.
    Done inline from `agents/prompt-reviewer.md` (read the filed record with `cat -n`). Result:

    | Area | Evidence (line; a quote only for ordinary text) | Reasoning | Severity |
    |---|---|---|---|
    | Quality | line 13: "Summarize the open TODO comments in the repository as a table..." | No unambiguous done/empty condition: it does not say what to return when no TODO exists, or that every tracked file must be covered. | Major |
    | Quality | line 13: "open TODO comments" | "Open TODO" is undefined (only `TODO`, or also `FIXME`/`XXX`?; are vendored, generated or gitignored files in scope?). | Minor |
    | Quality | line 13: "a one-line description" | Does not say whether the description is the comment's own text or a summary; executors may differ. | Minor |
    | Scope | lines 7, 10, 13 | Text matches description and boundaries (read-only); executor-neutral; 1 nonblank line, within the 50-line limit; no prerequisites needed. | (no finding) |

    Import review not run: origin `user` in both frontmatter and caller value (no mismatch).

    Proposed rewrite (diff against current text):
    ```diff
    -Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.
    +List every TODO comment (lines containing `TODO`) in the repository's tracked files.
    +Output one markdown table with the columns File, Line and Description, where Description is a one-line summary of the comment.
    +Sort the rows by file path, then line number. If there are no TODO comments, say so instead of an empty table.
    +Do not change any file.
    ```
    Counts: Critical 0, Major 1, Minor 2. Nothing was approved, activated or written by the review.
11. User kept the original text: no `update-draft` was run. User declined another review round.
12. `<CLI> show repo-maintenance__summarize-todo-comments --history` -> `ok: true`, status `draft`,
    `missing_verification: ["quality"]`, `prompt_text` identical to the original, `text_hash b483711e...52eb9f5`,
    `hidden_characters: []`, `hidden_characters_truncated: false`.
13. (after the user approved this exact text) `<CLI> record-verification p7b8e1f8929c3 --kind quality --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
    -> exit 0, `ok: true`, `recorded: {quality: b483711e...52eb9f5}`. No `--kind import` (origin `user`).
14. `<CLI> show repo-maintenance__summarize-todo-comments --history` -> status `draft`, `verified: true`,
    `missing_verification: []`, `text_hash b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`.
15. (after the user approved activation) `<CLI> activate p7b8e1f8929c3 --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
    -> exit 0, `ok: true`, `status: active`.
16. `<CLI> validate` -> exit 0, `ok: true`, one record: `repo-maintenance__summarize-todo-comments`, version 1,
    status `active`, origin `user`, `verified: true`.
17. `find .claude -type f` -> `.claude/prompts/catalog.yaml`, `.claude/prompts/repo-maintenance__summarize-todo-comments/active.md`.
    `git status --short` -> only the pre-existing `?? src/` plus the new `.claude/` catalog (gitignored or
    not shown as tracked); no other project file changed.

## Questions asked

1. **AskUserQuestion (step 1, init):** "No prompt catalog exists. Create one at `PROJ\.claude\prompts`
   (root_source: default)?" Options: "Create catalog (Recommended)" / "Cancel".
   Scripted reply: **yes** (create).
2. **AskUserQuestion (step 5, triage):** "Is this one reusable instruction text (a prompt), or does it need
   something a prompt cannot provide?" Options, in order: "Prompt (Recommended)" /
   "Skill: `skill-development`" (bundled scripts or references, tool restrictions, automatic activation) /
   "Workflow skill: `workflow-skill-development`" (multi-step phases or sub-agent orchestration).
   Scripted reply: **Prompt**.
3. Duplicate check: no similar prompt exists (empty catalog), so the "revise the existing one instead?"
   question was not asked. (Scripted reply "no, continue with a new one" was not needed; the outcome is
   the same: a new record.)
4. **AskUserQuestion (step 6, file draft):** showed slug `repo-maintenance__summarize-todo-comments`, name
   "Summarize open TODO comments", origin `user` (typed by you), description, and hash
   `b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`. "File this draft?" Options:
   "File draft (Recommended)" / "Cancel". Scripted reply: **yes**.
5. **AskUserQuestion (step 7, rewrite):** showed the reviewer table and the diff above. "Apply the proposed
   rewrite?" Options: "Apply rewrite" / "Keep my original text". Scripted reply: **keep my original text**.
6. **AskUserQuestion (step 7, another round):** "Run another review round?" Options: "No, continue
   (Recommended)" / "Yes, review again". Scripted reply: **no**.
7. **AskUserQuestion (step 8, approve):** showed the filed text (from `show --history`) and its hash
   `b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`; no hidden characters.
   "Approve exactly this text (0 hidden characters)?" Options: "Approve" / "Cancel". Scripted reply: **yes**.
8. **AskUserQuestion (step 9, activate):** "Activate `repo-maintenance__summarize-todo-comments`:
   draft -> active, hash `b483711e`, 0 hidden characters?" Options: "Activate (Recommended)" / "Leave as
   draft". Scripted reply: **yes**.

No question outside the script came up.

## Final reply to user

Your prompt is saved and active.

- **Catalog:** created at `.claude/prompts/` (it did not exist yet).
- **Prompt:** `repo-maintenance__summarize-todo-comments` ("Summarize open TODO comments"), version 1,
  origin `user`, internal id `p7b8e1f8929c3`, status **active**.
- **Text (unchanged, as you chose):** "Summarize the open TODO comments in the repository as a table with
  file, line and a one-line description. Do not change any file."
- **Hash:** `b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`; quality verification recorded
  against it. The secret screen found nothing, and the text has no hidden characters.
- **Review:** one round, 0 Critical, 1 Major (no stated result for when there are no TODOs), 2 Minor (what
  counts as an "open TODO", what goes in the description). You kept your original text. If you want those
  points fixed later, run `/prompt-library revise repo-maintenance__summarize-todo-comments`.
- **Check:** a final `validate` reports the catalog `ok`, with this one active record. The catalog files are
  `.claude/prompts/catalog.yaml` and `.claude/prompts/repo-maintenance__summarize-todo-comments/active.md`.
  They are not committed yet.

To use it, ask `prompt-retrieval` to show it or `prompt-execution` to run it.
