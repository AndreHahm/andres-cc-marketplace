# Step 4c review: PR #614, finding 9002 (self-review iteration 1)

## What was reviewed

The fix is uncommitted, so 4c reviews my own edit (old and new text) and the changed file, not a `git diff`:
one added sentence in `plugins/git-kit/skills/cross-model-review/SKILL.md`:

> Section 3 of references/scoped-review.md asks the batch-limit question after the First-Send Confirmation.

No new or deleted files are part of this fix (`git ls-files --others --exclude-standard` / `--deleted` would be
checked in a live run; nothing simulated here adds one).

## Finding: the fix introduces a new defect (blocking)

The sentence states the wrong order. `plugins/git-kit/skills/cross-model-review/references/scoped-review.md`
section 3 ("Dispatch batches", lines 129-138) says the opposite:

- "do not dispatch yet. Ask via `AskUserQuestion`, **before the First-Send Confirmation**, naming the batch
  count, the dispatch count ... and the limit"
- "The First-Send Confirmation then states the real dispatch count either way."

The ordering is load-bearing, not cosmetic: the batch-limit answer decides how many batches (and so how many
Codex dispatches) run, and the First-Send Confirmation must state that real dispatch count. An agent that
follows the new sentence would confirm a send before the dispatch count is known. The fix documents the timing
the finding asked about, but documents it wrongly, so it creates a fresh correctness defect in a file the fix
touched, which 4c treats as blocking. The passing smoke test and 4a exit 0 do not cover this: 4a checks
structure/verifier rules, not whether prose agrees with the reference.

4b sibling sweep: no other sentence in `cross-model-review/SKILL.md` states the batch-limit question's
timing (lines 329 and 427 mention the batch limit only for skipped files/report), so there is no second
instance to fix.

## What happens next

1. **No push, no reply, no resolve** for finding 9002 now (4a exit 0 is not enough; a 4c defect stops all three).
2. Fix the sentence (this is still iteration 1 -> iteration 2 per 4d), e.g.:
   > Section 3 of references/scoped-review.md asks the batch-limit question before the First-Send
   > Confirmation, only when packing yields more batches than the batch limit, so the confirmation can state
   > the real dispatch count.
3. Run iteration 2 of 4a-4c on the corrected fix: re-run the verifier launcher on the worktree (4a), repeat
   the sibling sweep (4b), and re-read the edited sentence against `scoped-review.md` section 3 (4c).
4. If iteration 2 is clean: run the push-destination check, then `Skill(commit) --push`, then reply on the
   9002 thread (verification line: smoke test passed, verifier self-review exit 0, and that 4c was a review of
   my own edits, with iteration 1 having caught and corrected a wrong before/after order), then resolve the
   thread, and record `--disposition fixed` for 9002 in the ledger (4e).
5. If iteration 2 still shows a blocking finding: stop (2-iteration budget reached), do not push/reply/resolve,
   report to the user and record `accepted` or leave it open as the user directs.
