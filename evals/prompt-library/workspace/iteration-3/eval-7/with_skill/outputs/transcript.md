# Eval 7 (with_skill) transcript

`<CLI>` = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`.
All commands run with cwd = PROJ.

## Commands run

1. `<CLI> validate` (step 1, preflight) -> exit 1:
   - `ok: false`, `catalog_root: PROJ\.claude\prompts`, `root_source: default`
   - `errors: ["unlisted record file on disk: review__orphan-draft/p0000000000ff.md"]`
   - records: `docs__changelog-entry` (active), `review__missing-tests` (active), `review__old-style` (inactive)
   - This is the one error class the skill repairs (orphan from an interrupted draft), so the add flow was
     paused and the removal offered.
2. `cat .claude/prompts/review__orphan-draft/p0000000000ff.md` (inspected as data before offering removal):
   a `status: draft`, `origin: user` record, "Orphan draft", body "Review the orphan handling." Nothing
   suspicious (no instructions aimed at the agent, no secret-like text).
3. After the user approved: `<CLI> discard-orphan review__orphan-draft/p0000000000ff.md` -> exit 0,
   `ok: true`, `removed: "review__orphan-draft/p0000000000ff.md"`, `slug: review__orphan-draft`,
   `internal_id: p0000000000ff`.
4. `<CLI> validate` (confirm) -> exit 0, `ok: true`, `errors: []`, same three records.
5. `git status --short` -> only the pre-existing untracked `src/`; no other change.

Not run: `new-id`, `screen`, `hash`, `draft` or anything else from steps 3 to 9, because the user chose to
stop after the repair. No scratch record file was written, and no catalog file other than the orphan was
touched.

## Questions asked

1. (AskUserQuestion, step 1 preflight) "The prompt catalog at `PROJ\.claude\prompts` (root source:
   default) fails validation with one error: `unlisted record file on disk:
   review__orphan-draft/p0000000000ff.md`. It is an orphan draft ("Orphan draft", status draft) left by an
   interrupted add and is not listed in catalog.yaml. Remove it with `discard-orphan`?"
   - Options: "Remove the orphan (Recommended)" — runs `<CLI> discard-orphan review__orphan-draft/p0000000000ff.md`;
     "Keep it and stop" — no change, the catalog stays invalid and no prompt can be added.
   - Scripted reply: **yes, remove it**.
2. (AskUserQuestion, after the repair) "The catalog now validates (`ok: true`). Continue with saving the
   new prompt ("Summarize the open TODO comments in the repository as a table...")?"
   - Options: "Continue with the add" — intake, screen, triage (prompt vs. skill), file the draft, review,
     approve, activate; "Stop here" — nothing more is changed.
   - Scripted reply: **no, stop here**.

## Final reply to user

Before saving your prompt, the preflight check found a problem in the prompt catalog
(`.claude/prompts`): an orphan draft file, `review__orphan-draft/p0000000000ff.md`, left behind by an
interrupted add and not listed in `catalog.yaml`. With your approval I removed it with `discard-orphan`,
and `validate` now reports the catalog as `ok` with no errors. Its three records are unchanged:
`docs__changelog-entry` (active), `review__missing-tests` (active) and `review__old-style` (inactive).

As you asked, I stopped there. Your new prompt ("Summarize the open TODO comments in the repository as a
table with file, line and a one-line description. Do not change any file.") was not saved: no draft was
created and nothing else in the catalog changed. To save it later, run `/prompt-library add` again with
that text; it will go through screening, the prompt-or-skill check, review and your approval before it is
activated.
