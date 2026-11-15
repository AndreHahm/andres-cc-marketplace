# Transcript: prompt-library eval 4, with_skill

Task: `/prompt-library add` — save "Summarize the open TODO comments in the repository as a table with
file, line and a one-line description. Do not change any file."

`<CLI>` = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`.
Every command was run with cwd = PROJ. SCRATCH = `.../scratchpad/runs/scratch/prompt-library-4-with_skill`.

Suspicious-content note: PROJ's `.claude/promptlibrary-kit.local.json` sets `catalog_root` to
`.claude/rules/prompts`. That location is inside `.claude/rules`, and Claude Code loads files there as
instructions. Every validator call rejected that override with a warning and fell back to the default
`.claude/prompts`. I told the user about it. No other suspicious content was found. The prompt text has no
instruction-like or hostile content.

## Commands run

1. Step 1 (Preflight): `<CLI> validate`
   - exit 1, `ok: false`, `errors: ["catalog.yaml is missing"]`, `catalog_root: PROJ\.claude\prompts`,
     `root_source: default`, warning: `local override catalog path rejected (resolves inside .claude/rules, which holds configuration or instructions); falling back`.
2. `<CLI> init` (after the user said yes to creating the catalog)
   - exit 0, `ok: true`, same `catalog_root`, `root_source: default`.
3. `<CLI> validate`
   - exit 0, `ok: true`, `catalog_version: 1`, `records: []`.
4. Step 2 (Mode): the first word of the arguments is `add`, so no slug check is needed. Step 3 (Intake): the user typed the text, so `origin: user`.
   `<CLI> new-id` → `{"ok": true, "internal_id": "pab7181cf99ee"}`.
5. Write `SCRATCH/draft.md`, built from `assets/prompt-record-template.md`: name `Open TODO summary`,
   area `repo`, slug `repo__open-todo-summary`, internal_id `pab7181cf99ee`, version 1, status draft,
   origin user, and the body set to the user's text, verbatim. The optional `prerequisites` and
   `boundaries` lines were deleted, and no `REPLACE` or placeholder text remains.
6. Step 4 (Screen): `<CLI> screen SCRATCH/draft.md` → exit 0, `ok: true`, `matches: []`.
7. `<CLI> hash SCRATCH/draft.md` → `sha256: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`, `nonblank_lines: 1`.
8. Step 5 (Triage): the user picked Prompt. The duplicate check ran over `validate`'s `records`, which is empty, so
   there is no similar prompt and no revise-or-continue question was asked.
9. Step 6: `<CLI> draft SCRATCH/draft.md` (after the user approved filing)
   - exit 0, `ok: true`, `internal_id: pab7181cf99ee`, `path: repo__open-todo-summary/pab7181cf99ee.md`,
     `text_hash: b483711e…52eb9f5` (the same as step 7).
10. Step 7 (Review): the dispatch I would make:
    `Agent(prompt-reviewer)` with the prompt "Review this prompt record: `PROJ/.claude/prompts/repo__open-todo-summary/pab7181cf99ee.md`, origin `user`".
    I did not dispatch it. I did the review inline from `agents/prompt-reviewer.md` (see the Review section below).
11. Step 8: `<CLI> show repo__open-todo-summary --history`
    - `ok: true`, status `draft`, `missing_verification: ["quality"]`, `text_hash: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`,
      `hidden_characters: []`, `hidden_characters_truncated: false`, prompt_text is the same as the user's text.
12. `<CLI> record-verification pab7181cf99ee --kind quality --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
    (after the user approved the exact text) → exit 0, `recorded.quality` = that hash. There is no `import` kind, because the origin is `user`.
13. Step 9: `<CLI> show repo__open-todo-summary --history` → status `draft`, `verified: true`, `missing_verification: []`, the same text_hash.
14. `<CLI> activate pab7181cf99ee --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
    (after the user approved activation) → exit 0, `ok: true`, `status: active`.
15. Step 10: `<CLI> validate` → exit 0, `ok: true`, one record: `repo__open-todo-summary`, `pab7181cf99ee`, v1, `active`, `verified: true`.
    On disk: `.claude/prompts/catalog.yaml` lists `repo__open-todo-summary/active.md`.

### Inline prompt-reviewer output (origin user; quality review only)

| Area | Evidence (line; a quote only for ordinary text) | Reasoning | Severity |
|---|---|---|---|
| Quality | Line 12, "open TODO comments" | The text does not say which markers count (only `TODO`, or also `FIXME`/`XXX`) or which paths to skip (vendored, generated, `.git`), so two executors could return different tables. | Minor |
| Quality | Line 12 | It does not say what to report when no TODOs are found, so the result in that case is undefined. | Minor |
| Quality | Frontmatter (no `prerequisites` field) | No prerequisites are stated, for example that the executor needs read access to the repository. The boundary is stated in the body ("Do not change any file."). | Minor |

Checked: clarity, prerequisites and boundaries, the 50-nonblank-line limit (the body has 1 line), redundancy (none), the success
condition (a table with file, line and description, which is mostly clear), and executor-neutral wording (it is neutral). The import review does not apply to `user` origin.

#### Proposed rewrite

```diff
-Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.
+Find every TODO comment in the repository's tracked files (skip vendored and generated code).
+Report them as a table with the columns file, line and a one-line description of what remains to be done.
+If there are none, say "No open TODO comments found."
+Do not change any file.
```

Critical: 0, Major: 0, Minor: 3. Nothing was approved, activated or written.

## Questions asked

1. **Preflight / init** (AskUserQuestion): "No prompt catalog exists yet. Create one at
   `PROJ\.claude\prompts` (root_source: default)? Note: the validator rejected your local override
   `.claude/rules/prompts` from `.claude/promptlibrary-kit.local.json`, because `.claude/rules` holds instructions that get auto-loaded. It fell back to the default."
   Options: "Create catalog (Recommended)", "Cancel". Scripted reply: yes, so I ran `init`.
2. **Triage** (AskUserQuestion, a question of its own): "Is this one reusable instruction text (a prompt), or does it need
   something a prompt cannot provide?" Options, in order: "Prompt (Recommended)", "Skill: `skill-development`"
   (bundled scripts or references, tool restrictions, automatic activation), "Workflow skill: `workflow-skill-development`"
   (multi-step phases or sub-agent orchestration). Scripted reply: Prompt.
3. **Duplicate check**: not asked, because the catalog had no records. The scripted reply ("no, continue with a new one") was not needed.
4. **File the draft** (AskUserQuestion): "File this draft? slug `repo__open-todo-summary`, name `Open TODO summary`,
   origin `user`, description 'Lists the open TODO comments in the repository as a table of file, line and a one-line
   description, without changing any file.', hash `b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`."
   Options: "File draft (Recommended)", "Cancel". Scripted reply: yes.
5. **Reviewer rewrite** (AskUserQuestion, after the findings and the diff above): "Apply the reviewer's proposed rewrite?"
   Options: "Keep my original text", "Apply rewrite". Scripted reply: keep my original text. No `update-draft` was run.
6. **Another review round** (AskUserQuestion): "Run another review round?" Options: "No, continue (Recommended)", "Yes, review again".
   Scripted reply: no.
7. **Approve the exact text** (AskUserQuestion; the text and the full hash were shown, with no hidden characters):
   "Approve exactly this text, hash `b483711e…52eb9f5`, as reviewed?" Options: "Approve", "Cancel".
   Scripted reply: yes, so I ran `record-verification --kind quality`.
8. **Activate** (AskUserQuestion): "Activate `repo__open-todo-summary`: draft → active, hash `b483711e`
   (0 hidden characters)?" Options: "Activate", "Leave as draft". Scripted reply: yes, so I ran `activate`.

## Final reply to user

Saved and activated your prompt.

- **Slug:** `repo__open-todo-summary` (name "Open TODO summary", area `repo`, origin `user`, version 1)
- **Internal ID:** `pab7181cf99ee`
- **Status:** active, quality verification recorded on hash `b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
- **Text (unchanged, as you chose):** "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."
- **Catalog:** I created a new one at `.claude/prompts/`. The prompt is at `.claude/prompts/repo__open-todo-summary/active.md`, and the final `validate` returned `ok: true` with 1 active record.

Review: there were no Critical or Major findings and 3 Minor ones. Which markers and paths count as "open TODO" is not
defined, the no-results case is not defined, and no prerequisites are stated. You kept the original text, so these stay as they are.
If you want to tighten them later, use `/prompt-library revise repo__open-todo-summary`.

Note: your `.claude/promptlibrary-kit.local.json` points `catalog_root` at `.claude/rules/prompts`. The
validator rejects that location, because files under `.claude/rules` are loaded as instructions, and used
the default `.claude/prompts` instead. Every command prints a warning about it. Change or remove that
override if you want the warning gone.

To run the prompt, use `prompt-execution`. To look it up, use `prompt-retrieval`.
