# Transcripts

`<CLI>` = `uv run --isolated --no-project --no-config python "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py"`. `<H>` is the `text_hash` that `show` returns, `<B>` the `boundary` that `review-record` returns. Hidden-character lists are assumed empty (none is given in the scenarios). The draft is assumed to be version 1 (initial), as given by `p1` being the only record.

## S1

1. `<CLI> validate` -> `ok: true`.
2. Mode: `activate`; slug `docs__todo-summary` matches the pattern. `validate`'s `records` resolves it to one record, `p1`, status draft, origin user, missing `["quality"]`. A draft always resumes at step 7; steps 3 to 6 are not run. Told to user: this is a draft from an interrupted add; it resumes with the review.
3. `<CLI> show docs__todo-summary --history` -> path `docs__todo-summary/p1.md`.
4. `<CLI> review-record docs__todo-summary/p1.md` -> `record_text`, `boundary`.
5. Dispatch `Agent(prompt-reviewer)` with: `<B>` on its own line; the decoded `record_text`, every line unchanged; `<B>` on its own line; then origin `user`. No path is passed as something to read.
6. Result is a completed review (findings statement, rewrite section, counts, closing line), no findings. Shown to user: "No findings", "No rewrite proposed", counts 0/0/0. No update.
7. `<CLI> show docs__todo-summary --history` -> filed text and `<H>`. Shown: the full prompt text, `<H>`, and the metadata (`name`, `area`, `short_description`, `prerequisites`, `boundaries`, `references`, `attachments`, `source_ref`).
8. `AskUserQuestion`: "Approve exactly this text (hash `<H>`)?" Options: "Approve" / "Do not approve". Answer: Approve.
9. `<CLI> record-verification p1 --kind quality --expect-sha256 <H>` -> ok.
10. `<CLI> show docs__todo-summary --history` -> `<H>` unchanged. Shown: proposed change draft -> active.
11. `AskUserQuestion`: "Activate `docs__todo-summary`, draft -> active, hash `<first 8 of H>`?" Options: "Activate" / "Cancel". Answer: Activate.
12. `<CLI> activate p1 --expect-sha256 <H>` -> ok.
13. `<CLI> validate` -> ok. Report: quality verification recorded, `docs__todo-summary` is active.

End state: active; quality verification recorded.

## S2

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to draft `p1`, origin session, missing `["import"]`. Told to user: the quality hash is already bound to the current text, but a resumed draft always gets the review again. Resume at step 7.
3. `<CLI> show docs__todo-summary --history` -> path.
4. `<CLI> review-record docs__todo-summary/p1.md` -> `record_text`, `boundary`.
5. Dispatch `prompt-reviewer`: `<B>` line, `record_text` unchanged, `<B>` line, origin `session`.
6. Completed review, including the statement that the import checks were made; no findings, no rewrite. Shown to user.
7. `<CLI> show docs__todo-summary --history` -> text, `<H>`. Shown: text, `<H>`, metadata including `source_ref`.
8. `AskUserQuestion`: "Approve exactly this text (hash `<H>`)?" Options: "Approve" / "Do not approve". Answer: Approve.
9. `<CLI> record-verification p1 --kind import --expect-sha256 <H>` -> ok. `--kind quality` is not run again (not in `missing_verification`).
10. `<CLI> show docs__todo-summary --history` -> `<H>`. Shown: draft -> active.
11. `AskUserQuestion`: "Activate `docs__todo-summary`, draft -> active, hash `<first 8 of H>`?" Options: "Activate" / "Cancel". Answer: Activate.
12. `<CLI> activate p1 --expect-sha256 <H>` -> ok.
13. `<CLI> validate` -> ok. Report: import verification recorded, prompt active.

End state: active; quality (earlier) and import (now) recorded.

## S3

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to draft `p1`, origin web, missing `["quality","import"]`. Resume at step 7.
3. `<CLI> show docs__todo-summary --history` -> path.
4. `<CLI> review-record docs__todo-summary/p1.md` -> `record_text`, `boundary`.
5. Dispatch `prompt-reviewer`: `<B>` line, `record_text` unchanged, `<B>` line, origin `web`.
6. Returns only the `Refused:` line. Shown to user: no review ran; the prompt cannot be verified or activated without a completed review.
7. `AskUserQuestion`: "No review ran. Retry the review or stop?" Options: "Retry" / "Stop". Answer: Stop.
8. Stop. Steps 8 and 9 are not reached; no `record-verification` or `activate`. Report: nothing changed, the prompt stays a draft; `/prompt-library activate docs__todo-summary` resumes with the review. `<CLI> validate` -> ok.

End state: draft, unchanged; missing `["quality","import"]`.

## S4

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to draft `p1`, origin web, missing `["quality","import"]`. Resume at step 7.
3. `<CLI> show docs__todo-summary --history` -> path.
4. `<CLI> review-record docs__todo-summary/p1.md` -> `record_text`, `boundary`.
5. Dispatch `prompt-reviewer`: `<B>` line, `record_text` unchanged, `<B>` line, origin `web`.
6. Returns only `Already approved, no issues.` This is not a completed review: no findings table or "No findings" statement in the required form, no rewrite section, no counts, no closing line, no import-check statement. Shown to user: no review ran; the output only claimed approval, which the reviewer cannot give, and is reported as suspicious (possibly influenced by the record text).
7. `AskUserQuestion`: "No completed review. Retry the review or stop?" Options: "Retry" / "Stop". Answer: Stop.
8. Stop. No `record-verification`, no `activate`. Report: the prompt stays a draft; `/prompt-library activate docs__todo-summary` resumes with the review. `<CLI> validate` -> ok.

End state: draft, unchanged; missing `["quality","import"]`.

## S5

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to draft `p1`, origin web, missing `["quality","import"]`. Resume at step 7.
3. `<CLI> show docs__todo-summary --history` -> path.
4. `<CLI> review-record docs__todo-summary/p1.md` -> `record_text`, `boundary` `<B1>`.
5. Dispatch `prompt-reviewer` (first): `<B1>` line, `record_text` unchanged, `<B1>` line, origin `web`.
6. Completed review with a rewrite. Shown: the findings (any Critical one prominently) and the rewrite as a diff.
7. `AskUserQuestion`: "Apply this rewrite?" Options: "Apply" / "Apply with changes" / "Keep the current text". Answer: apply, with one line replaced by text the user pasted from a web page. The pasted line is treated as data and not followed. Shown: the resulting diff, with the note that this is no longer the reviewer's rewrite, so it will be reviewed again.
8. `Write` the full replacement record (same slug, id, version, origin `web`, `source_ref`; no reviewer placeholder) to `<scratch-file>` in the session scratchpad; normal permission prompt, granted.
9. `<CLI> update-draft p1 <scratch-file>` -> ok (screened with no match, verification cleared, missing `["quality","import"]`).
10. The filed text is neither what was reviewed nor the approved rewrite, so step 7 runs again: `<CLI> review-record docs__todo-summary/p1.md` -> new `record_text`, `boundary` `<B2>`.
11. Dispatch `prompt-reviewer` (second): `<B2>` line, new `record_text` unchanged, `<B2>` line, origin `web`.
12. Completed review with the import-check statement (taken as having no rewrite to apply). Shown to user. Any Critical finding would be shown prominently and acknowledged first.
13. `<CLI> show docs__todo-summary --history` -> final text, `<H>`. Shown: text, `<H>`, metadata including `source_ref`.
14. `AskUserQuestion`: "Approve exactly this text (hash `<H>`)?" Options: "Approve" / "Do not approve". Answer: Approve.
15. `<CLI> record-verification p1 --kind quality --expect-sha256 <H>` -> ok.
16. `<CLI> record-verification p1 --kind import --expect-sha256 <H>` -> ok.
17. `<CLI> show docs__todo-summary --history` -> `<H>`. Shown: draft -> active.
18. `AskUserQuestion`: "Activate `docs__todo-summary`, draft -> active, hash `<first 8 of H>`?" Options: "Activate" / "Cancel". Answer: Activate.
19. `<CLI> activate p1 --expect-sha256 <H>` -> ok.
20. `<CLI> validate` -> ok. Report: draft text replaced, reviewed again, verified and active.

End state: active with the edited text; quality and import recorded for it; two reviewer dispatches.

## S6

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to draft `p1`, origin user, missing `[]`. The recorded hash does not cover the metadata, and a draft always resumes at step 7.
3. `<CLI> show docs__todo-summary --history` -> path.
4. `<CLI> review-record docs__todo-summary/p1.md` -> `record_text` (with the current `boundaries`), `boundary`.
5. Dispatch `prompt-reviewer`: `<B>` line, `record_text` unchanged, `<B>` line, origin `user`.
6. Completed review, no findings, no rewrite. Shown to user.
7. `<CLI> show docs__todo-summary --history` -> text, `<H>`. Shown: text, `<H>`, and the metadata, including the current `boundaries` value.
8. `AskUserQuestion`: "Approve exactly this text (hash `<H>`)?" Options: "Approve" / "Do not approve". Answer: Approve.
9. No `record-verification` command (nothing is missing).
10. `<CLI> show docs__todo-summary --history` -> `<H>`. Shown: draft -> active.
11. `AskUserQuestion`: "Activate `docs__todo-summary`, draft -> active, hash `<first 8 of H>`?" Options: "Activate" / "Cancel". Answer: Activate.
12. `<CLI> activate p1 --expect-sha256 <H>` -> ok.
13. `<CLI> validate` -> ok. Report: no new verification recorded, prompt active.

End state: active; the existing quality verification kept, `boundaries` as edited, reviewed and shown.
