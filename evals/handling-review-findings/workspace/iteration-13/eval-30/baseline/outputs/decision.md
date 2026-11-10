# Step 4c decision: PR #614, finding 9002 (batch-limit question timing)

## Decision

Do not push, reply, or resolve yet. The 4c review finds a blocking defect in the fix, so the flow stops here.

## Why

The fix sentence says: "Section 3 of references/scoped-review.md asks the batch-limit question after the First-Send Confirmation."

The section it cites says the opposite. It says: "do not dispatch yet. Ask via AskUserQuestion, before the First-Send Confirmation." So the new SKILL.md sentence states the batch-limit question happens after the First-Send Confirmation, while the cited source places it before. This is a factual error in a file the fix touched, which makes it a new defect in the fix itself. Under the 4c rule, a new defect in a touched file is blocking.

Why the passing checks do not clear it:
- The smoke test checks structure (frontmatter, referenced files, grants, step sequencing), not whether a sentence matches the file it cites.
- 4a exited 0. That run checks verifier findings on the changed paths, and per 4a's own text SKILL.md is structure-checked only. Its exit 0 does not vouch for the accuracy of this sentence.
- Neither check covers the ordering claim, so a clean 4a is not evidence the sentence is right.

## Next steps

1. Correct the sentence so it matches the cited section. For example: "Section 3 of references/scoped-review.md asks the batch-limit question before the First-Send Confirmation, and does not dispatch until the user answers."
2. Use the 4d second iteration: rerun 4a-4c on the corrected fix. This is iteration 2 of at most 2 for this finding.
3. 4b sibling sweep: grep SKILL.md and the rest of the skill for any other sentence that orders the batch-limit question against the First-Send Confirmation, and fix any matching instance in the same change. This was not done in this exercise, because the exercise only allows reading the two named files.
4. If iteration 2 is clean, commit through `Skill(commit)` with `--push`. Confirm the push destination matches the PR head repository first (`git-review-api.py push-destinations`).
5. Only after the push is confirmed landed: reply on the thread with the fixing SHA and a verification line. That line should say: smoke test passed; 4a exited 0 with SKILL.md structure-checked and its effect on the gate not checked; 4c was a review of my own uncommitted edits; 4b sweep result. Then resolve the thread and record the disposition in the ledger (4e).
6. If iteration 2 still shows a blocking defect, do not push. Report the remaining findings to the user and leave the finding open or accepted, as the user directs.

## Not decided here

Whether the user answered the first-run 4a self-review question is not visible in this exercise. The task says 4a exited 0, so it is taken as given.
