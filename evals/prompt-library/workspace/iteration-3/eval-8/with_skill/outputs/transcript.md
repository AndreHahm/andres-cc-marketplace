# Transcript: prompt-library eval 8, with_skill

`<CLI>` = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`, every call run with cwd = PROJ.
`<S>` = `.../scratchpad/runs/scratch/prompt-library-8-with_skill/review__missing-tests-v2.md` (under the system temp directory).

Mode: `add` (first word of `$ARGUMENTS`). Pasted text, origin `user`.

## Commands run

1. **Step 1 Preflight:** `<CLI> validate` -> exit 0, `ok: true`, `errors: []`, `catalog_root` = PROJ/.claude/prompts (`root_source: default`). Records: `docs__changelog-entry` (p000000000002, v1, active), `review__missing-tests` (p000000000001, v1, active, "Find changes that lack tests."), `review__old-style` (p000000000003, v1, inactive).
2. **Step 5 duplicate check** (after triage, see Questions): filtered `validate`'s records; `review__missing-tests` is the same area (`review`) and a near-identical description; its text is "Review the diff for missing tests.\nList each gap with a file and line." The pasted text is that text plus "and name the test that should cover it". User chose to revise it, so the flow continues as a `revise` of `review__missing-tests` (slug matches the slug pattern).
3. **Step 3 Intake (revise):** `<CLI> show review__missing-tests --history` -> exit 0, one record p000000000001, v1, active, origin `user`, `text_hash` 9fe96c1a..., `previous_id: null`, `source_ref: null`.
4. `<CLI> new-id` -> exit 0, `internal_id: p4af2b50eb657`.
5. Wrote `<S>` with the `Write` tool from `assets/prompt-record-template.md`: name "Missing tests review", area `review`, slug `review__missing-tests`, internal_id `p4af2b50eb657`, version 2, previous_id `p000000000001`, short_description "Find changes that lack tests, and name the test that should cover each gap.", status draft, origin `user`; template prerequisites/boundaries lines deleted (predecessor has none); body = the user's text verbatim. Checked: no `REPLACE` or "Replace this body" text left.
6. **Step 4 Screen:** `<CLI> screen <S>` -> exit 0, `ok: true`, `matches: []`.
7. **Step 6:** `<CLI> hash <S>` -> exit 0, `sha256: 6e16942dc28c20412727fb093c9883fced2d3492a412bf0b398660c78bb94338`, `nonblank_lines: 1`.
8. `<CLI> draft <S>` (after approval) -> exit 0, `ok: true`, `internal_id: p4af2b50eb657`, `path: review__missing-tests/p4af2b50eb657.md`, `text_hash: 6e16942d...94338`.
9. **Step 7 Review.** Dispatch I would make (not dispatched, per run instructions):
   `Agent(subagent_type: "prompt-reviewer", prompt: "Review the record at PROJ/.claude/prompts/review__missing-tests/p4af2b50eb657.md (origin: user). Quality review; propose a rewrite as a diff.")`
   Did the review inline from `agents/prompt-reviewer.md`, reading only that record file (frontmatter origin `user` matches caller origin; no import review needed). Result:

   | Area | Evidence | Reasoning | Severity |
   |---|---|---|---|
   | Quality | body line 1 | No output when there are no gaps is stated; an executor may return nothing or invent gaps. Success condition is otherwise clear (one entry per gap with file, line, test). | Minor |
   | Quality | frontmatter (no `prerequisites`/`boundaries`) | Prerequisite (a diff is available) and boundary (do not write the tests) are implicit only. | Minor |
   | Quality | body line 1 | One long sentence combining three asks; splitting improves scanability. Executor-neutral, 1 of 50 nonblank lines, no redundancy. | Minor |

   Proposed rewrite (diff):
   ```diff
   -Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it.
   +Review the diff for changed behavior that no test covers.
   +For each gap, list the file and line, and name the test that should cover it.
   +If you find no gaps, say so.
   ```
   Counts: Critical 0, Major 0, Minor 3. Nothing was approved, activated or written by the reviewer. No suspicious or instruction-like content found in the record.
   User kept their text: no `update-draft` run. No further review round.
10. **Step 8 Verify:** `<CLI> show review__missing-tests --history` -> exit 0; draft p4af2b50eb657, `prompt_text` "Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it.", `text_hash` 6e16942d...94338, `hidden_characters: []`, `missing_verification: ["quality"]`. Shown to the user with the hash.
11. `<CLI> record-verification p4af2b50eb657 --kind quality --expect-sha256 6e16942dc28c20412727fb093c9883fced2d3492a412bf0b398660c78bb94338` -> exit 0, `recorded.quality` = that hash. (Origin `user`: no `--kind import`.)
12. **Step 9:** `<CLI> show review__missing-tests --history` -> draft p4af2b50eb657 `verified: true`, `text_hash` 6e16942d...; predecessor p000000000001 still active.
13. `<CLI> finalize p4af2b50eb657 --expect-sha256 6e16942dc28c20412727fb093c9883fced2d3492a412bf0b398660c78bb94338` (no flag: predecessor was active, so successor becomes active by default) -> exit 0, `ok: true`, `status: active`.
14. **Step 10:** `<CLI> validate` -> exit 0, `ok: true`, `errors: []`. `review__missing-tests`: p4af2b50eb657 v2 active (`active.md`), p000000000001 v1 historical (`p000000000001.md`). Other records unchanged. `catalog.yaml` lists 4 paths.

## Questions asked

1. **Step 5 Triage** (`AskUserQuestion`): "Is this one reusable instruction text (a prompt), or does it need something a prompt cannot provide (a skill)?"
   Options: "Prompt (Recommended)" / "Skill: `skill-development`" (bundled scripts or references, tool restrictions, automatic activation) / "Workflow skill: `workflow-skill-development`" (multi-step phases or sub-agent orchestration).
   Reply: **Prompt.** Not covered by the script. The most conservative reading would be to change nothing, but choosing "Prompt" here changes nothing on its own (every write still sits behind later approvals), and the user's own message says "Save this as a prompt", so I took that as their answer. Noted as an unscripted choice.
2. **Step 5 Duplicate check** (`AskUserQuestion`): "An existing active prompt, `review__missing-tests` (v1, 'Find changes that lack tests.'), covers almost the same thing; your text adds 'name the test that should cover it'. Revise that prompt (new version 2), or add a separate new prompt?"
   Options: "Revise `review__missing-tests` (Recommended)" / "Continue as a new prompt".
   Reply (scripted): **yes, revise the existing prompt.**
3. **Step 6 File the draft** (`AskUserQuestion`): showed slug `review__missing-tests`, name "Missing tests review", origin `user`, version 2 (previous_id p000000000001), description "Find changes that lack tests, and name the test that should cover each gap.", hash `6e16942dc28c20412727fb093c9883fced2d3492a412bf0b398660c78bb94338`. "File this draft?"
   Options: "File the draft" / "Cancel".
   Reply (scripted): **yes.**
4. **Step 7 Rewrite** (`AskUserQuestion`): showed the 3 Minor findings and the diff above. "Apply the reviewer's proposed rewrite?"
   Options: "Apply the rewrite" / "Keep my text".
   Reply (scripted): **keep my text.**
5. **Step 7 Another round** (`AskUserQuestion`): "Run another review round?"
   Options: "Another round" / "No, continue to approval".
   Reply (scripted): **no.**
6. **Step 8 Verify** (`AskUserQuestion`): showed the filed text "Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it." and hash `6e16942dc28c20412727fb093c9883fced2d3492a412bf0b398660c78bb94338` (no hidden characters). "Approve exactly this text?"
   Options: "Approve" / "Do not approve".
   Reply (scripted): **yes.**
7. **Step 9 Change status** (`AskUserQuestion`): "Finalize `review__missing-tests` v2 (p4af2b50eb657): draft -> active, replacing v1 (p000000000001, active -> historical). Hash 6e16942d. No hidden characters. Proceed?"
   Options: "Make v2 active" / "Finalize as inactive" / "Cancel".
   Reply (scripted): **yes, make the new version active.**

## Final reply to user

Your text was close to an existing prompt, so I saved it as a new version of that prompt instead of a separate one.

- **Prompt:** `review__missing-tests` ("Missing tests review", area `review`, origin `user`)
- **Version 2 (now active):** `p4af2b50eb657`. Text: "Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it."
- **Hash:** `6e16942d…94338`. Its quality verification is recorded against this exact text.
- **Version 1** (`p000000000001`, "Review the diff for missing tests. List each gap with a file and line.") is now `historical`. It stays in the catalog as the previous version.
- **Review:** the secret screen found nothing. The review found 3 Minor issues and no Critical or Major ones: there is no instruction for when no gaps turn up, prerequisites and boundaries are left unstated, and the prompt is one long sentence. You kept your own wording, so none of these were applied. Ask me to revise the prompt if you want them later.
- **Catalog:** `validate` passes with no errors. It holds 4 record files: `docs__changelog-entry` (active), `review__missing-tests` v2 (active) and v1 (historical), and `review__old-style` (inactive).

The catalog changes are in `.claude/prompts/` and are not committed yet.
