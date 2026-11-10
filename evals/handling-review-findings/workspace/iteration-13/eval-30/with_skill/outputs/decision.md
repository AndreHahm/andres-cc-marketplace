# Step 4c decision: PR #614, finding 9002

## Outcome

**Do not push, reply or resolve yet.** The fix fails step 4c because its new sentence contradicts the source it cites. Run one more self-review iteration (4d, iteration 2) after correcting the sentence. Do not treat 4a's exit 0 or the smoke test as evidence for the claim.

## Why 4c blocks

`fix-self-review.md` 4c says a prose fix is checked by its claims: "compare every statement the fix adds about another file, section, command or behavior with that source... A claim the source does not support is a defect in the fix, like a code bug."

- The fix's sentence: "Section 3 of `references/scoped-review.md` asks the batch-limit question **after** the First-Send Confirmation."
- The cited section 3 says the batch-limit question is asked **before** the First-Send Confirmation ("do not dispatch yet. Ask via AskUserQuestion, before the First-Send Confirmation").

The fix states the reverse of the source's ordering. That is a blocking defect.

## Why 4a's pass does not cover it

4a only runs the structural verifiers (`run_verifiers`) and the smoke test. Neither reads the prose claim against `scoped-review.md`. The "verification passed" result is true for the structure but says nothing about whether the sentence is correct.

## Next steps, in order

1. Correct the sentence in `SKILL.md` so its ordering matches section 3, for example: "Section 3 of `references/scoped-review.md` asks the batch-limit question **before** the First-Send Confirmation." Read section 3 directly before finalizing the wording, so the new text matches the source exactly.
2. Re-run 4a (the verifier re-run is per fix; the ask-once prompt is already answered for this run). Re-run 4b (sweep `SKILL.md` and its references for other statements about the batch-limit/First-Send ordering). Re-run 4c against the corrected sentence.
3. Check the smoke test still passes after the edit.
4. If iteration 2 is clean: commit via `Skill(commit)` with `--push`, after the push-destination check (`git-review-api.py push-destinations` against PR #614's head repository). Only after the push lands: reply to finding 9002's thread with the fixing SHA and a one-line verification summary. Name the claim check (4c) in that summary. Then resolve the thread and record the disposition in the ledger (4e) as `fixed`.
5. If iteration 2 still shows a blocking defect, stop (4d). Do not push, reply or resolve. Report the remaining item to the user and leave finding 9002 open or record it as `accepted`, as the user directs.

## Not done here

No commit, push, reply, resolve or ledger write was made. This was a review of the fix as described in the task, with no GitHub calls. The text of section 3 was taken from the task's quotation, not from a fresh read of `scoped-review.md`, because the task limited reads to the two skill files.
