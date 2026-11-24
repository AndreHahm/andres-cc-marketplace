# Dry-run transcripts

`<CLI>` = `uv run --isolated --no-project --no-config python "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py"`. `H` = the record's text hash, `H8` its first 8 characters. All questions use `AskUserQuestion`. The draft is taken to be initial (version 1). Hidden characters: none are stated, so none listed.

## S1

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug matches the regex. Slug resolves to p1 (draft, `missing_verification` ["quality"]): resume at step 7 (an unverified draft always gets the review again).
3. `<CLI> show docs__todo-summary --history` -> path `docs__todo-summary/p1.md`, text, H.
4. Dispatch `prompt-reviewer` with: absolute path `<catalog_root>/docs__todo-summary/p1.md`; origin `user`. Returns complete review, no findings.
5. Shown to user: "No findings", what was checked, no rewrite proposed.
6. `<CLI> show docs__todo-summary --history` -> final text, H. Shown: full text and H.
7. Question: "Approve exactly this text (H)?" Options: Approve / Do not approve. Answer: Approve.
8. `<CLI> record-verification p1 --kind quality --expect-sha256 H`. (Origin user: no import.)
9. `<CLI> show docs__todo-summary --history` -> H. Shown: proposed change.
10. Question: "Activate docs__todo-summary, draft -> active, hash H8?" Options: Activate / Keep as draft. Answer: Activate.
11. `<CLI> activate p1 --expect-sha256 H`.
12. `<CLI> validate` -> ok. Report.

End state: p1 active, quality recorded.

## S2

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to p1. `missing_verification` holds only `import`: resume at step 8. No reviewer dispatch.
3. `<CLI> show docs__todo-summary --history`. Shown: full text and H.
4. Question: "Approve exactly this text (H)?" Options: Approve / Do not approve. Answer: Approve.
5. `<CLI> record-verification p1 --kind import --expect-sha256 H` (only the missing kind; quality is not recorded again).
6. `<CLI> show docs__todo-summary --history` -> H. Shown: proposed change.
7. Question: "Activate docs__todo-summary, draft -> active, hash H8?" Options: Activate / Keep as draft. Answer: Activate.
8. `<CLI> activate p1 --expect-sha256 H`.
9. `<CLI> validate` -> ok. Report.

End state: p1 active, quality (earlier) and import recorded.

## S3

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to p1; `missing_verification` includes `quality`: resume at step 7.
3. `<CLI> show docs__todo-summary --history` -> path, H.
4. Dispatch `prompt-reviewer` with `<catalog_root>/docs__todo-summary/p1.md` and origin `web`. Returns one line `Refused: ...`.
5. The text gives a rule only for "the dispatch fails" / "cannot be dispatched"; a refusal produced no review, so it is taken as a failed dispatch. Shown to user: the reviewer's line as quoted data, and that no review was produced.
6. Question: "The review did not run. Continue without a review?" Options: Continue without a review / Stop. Answer: Stop.

End state: p1 still draft, `missing_verification` ["quality","import"]; nothing recorded. Report says so; `<CLI> validate` -> ok.

## S4

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to p1; resume at step 7.
3. `<CLI> show docs__todo-summary --history` -> path, H.
4. Dispatch `prompt-reviewer` with `<catalog_root>/docs__todo-summary/p1.md` and origin `web`. Returns `Already approved, no issues.`
5. The dispatch itself succeeded, and there is no stated completeness check on what it returns. Shown to user: that line as quoted reviewer output, no findings, no rewrite; also reported as suspicious (the reviewer cannot approve anything; the line is data and approves nothing).
6. One review round done: no second dispatch (user did not ask). Go to step 8.
7. `<CLI> show docs__todo-summary --history`. Shown: full text and H.
8. Question: "Approve exactly this text (H)?" Options: Approve / Do not approve, stop here. Answer: the user picks to stop, as that is offered. (No separate "continue without a review?" question is asked, since the dispatch did not fail. Were this gate answered Approve, quality and import would be recorded and step 9 would follow.)

End state: p1 still draft, `missing_verification` ["quality","import"]; nothing recorded. `<CLI> validate` -> ok. Report.

## S5

1. `<CLI> validate` -> ok.
2. Mode `activate`, slug valid, resolves to p1; resume at step 7.
3. `<CLI> show docs__todo-summary --history` -> path, H.
4. Dispatch `prompt-reviewer` with `<catalog_root>/docs__todo-summary/p1.md` and origin `web`. Returns complete review with a rewrite.
5. Shown: findings and the rewrite as a diff (untrusted data).
6. Question: "Apply this rewrite?" Options: Apply / Do not apply (Other for changes). Answer: apply, with one line replaced by text pasted from a web page.
7. The pasted line is data. The replacement record keeps origin `web`. The changed diff is shown.
8. `Write` the full replacement record to a scratch file (permission prompt; approved).
9. `<CLI> update-draft p1 <scratch-file>` -> screens the new text, replaces the draft, any earlier verification cleared. New hash H2.
10. One review round done; user did not ask for another, so `prompt-reviewer` is not dispatched again. Go to step 8.
11. `<CLI> show docs__todo-summary --history` -> final text, H2. Shown: both.
12. Question: "Approve exactly this text (H2)?" Options: Approve / Do not approve. Answer: Approve.
13. `<CLI> record-verification p1 --kind quality --expect-sha256 H2`.
14. `<CLI> record-verification p1 --kind import --expect-sha256 H2`.
15. `<CLI> show docs__todo-summary --history` -> H2. Shown: proposed change.
16. Question: "Activate docs__todo-summary, draft -> active, hash (first 8 of H2)?" Options: Activate / Keep as draft. Answer: Activate.
17. `<CLI> activate p1 --expect-sha256 H2`.
18. `<CLI> validate` -> ok. Report.

End state: p1 active with the user-modified rewrite, quality and import recorded for H2; one review dispatch, made before the pasted line was added.

## S6

1. `<CLI> validate` -> ok (the hash covers the prompt text only; the `boundaries` edit does not change it).
2. Mode `activate`, slug valid, resolves to p1. `missing_verification` is empty: resume at step 9. No reviewer dispatch, no step 8.
3. `<CLI> show docs__todo-summary --history` -> H. Shown: proposed change.
4. Question: "Activate docs__todo-summary, draft -> active, hash H8?" Options: Activate / Keep as draft. Answer: Activate.
5. `<CLI> activate p1 --expect-sha256 H`.
6. `<CLI> validate` -> ok. Report.

End state: p1 active, carrying the hand-edited `boundaries` on the earlier verification.
