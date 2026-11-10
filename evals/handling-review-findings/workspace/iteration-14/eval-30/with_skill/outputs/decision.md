# PR #614, finding 9002: step 4c review of the fix

## The fix under review (uncommitted, simulated)

Added to `plugins/git-kit/skills/cross-model-review/SKILL.md`:

> Section 3 of references/scoped-review.md asks the batch-limit question after the First-Send Confirmation.

Checks so far: verification (smoke test) passed, 4a exited 0. 4b sibling sweep: nothing else in the fix to sweep.

## 4c: the prose fix checked by its claims

`references/fix-self-review.md` 4c says a prose fix is checked by its claims: every statement the fix makes
about another file or section is compared with that source, and a claim the source does not support is a
defect in the fix, like a code bug.

I read the cited source, `plugins/git-kit/skills/cross-model-review/references/scoped-review.md`, section 3
("Dispatch batches"). It says:

> **If packing produces more batches than the batch limit** ... do not dispatch yet. Ask via
> `AskUserQuestion`, **before the First-Send Confirmation**, naming the batch count, the dispatch count ...
> and the limit ... At or under the limit there is no extra question. If no batch has a Codex-eligible
> path ... skip the question ... The First-Send Confirmation then states the real dispatch count either way.

The fix's sentence is wrong in two ways:

1. **Wrong order (blocking).** The fix says "after" the First-Send Confirmation. The source says
   "before". The order matters: the First-Send Confirmation has to state the real dispatch count, and it
   can only do that once the batch-limit answer is known.
2. **Missing condition (blocking: it is an unsupported claim too).** The fix says the question is asked
   without condition. The source asks it only when packing produces more batches than the batch limit. At
   or under the limit, or when no batch has a Codex-eligible path, there is no question.

The fix adds the very defect finding 9002 was about: wrong documentation of when the question is asked.
4a's exit 0 does not cover this, because the verifiers check structure, not whether the prose is true.
The smoke test passing does not cover it either.

**4c result: blocking defect in a file the fix touched. Iteration 1 fails.**

## What happens next

- **No push, no reply, no resolve.** `fix-self-review.md` says a reply and a resolve never happen while 4b/4c
  show a defect in the fix, and SKILL.md Workflow step 4 says a defect found in 4b/4c stops the push, reply
  and resolve. The 4a exit 0 does not change this.
- **No ledger `record` yet.** The finding is not settled, so 4e is not run yet.
- **Iteration 2 (4d budget: at most 2 iterations).** Correct the sentence to match the source, for example:

  > When packing produces more batches than the batch limit, section 3 of `references/scoped-review.md`
  > asks the batch-limit question via `AskUserQuestion` before the First-Send Confirmation. At or under the
  > limit, or when no batch has a Codex-eligible path, it asks nothing.

  Then re-run the verification and 4a-4c once more on the corrected fix: re-read section 3 against every
  claim in the new sentence (order, condition, the single-model exception).
- **If iteration 2 is clean:** go on with Workflow step 4: check every push destination of `origin`, then
  `Skill(commit) --push`, then reply to 9002 and resolve it. The reply's verification line should say:
  smoke test passed; 4a re-run on the corrected diff (with its result, and the `ungraded` disclosure if
  SKILL.md comes back under `ungraded`); 4c was a review of my own edits, because the fix was uncommitted;
  iteration 1 found a wrong claim ("after" instead of "before", no condition), fixed in iteration 2. Then
  record `--disposition fixed` for finding 9002 in the ledger.
- **If iteration 2 still shows a blocking finding:** stop. Do not push, reply or resolve. Report the
  remaining finding to the user, and record 9002 as `accepted` or leave it open, as the user decides.
  No third iteration.

Nothing was executed (simulated exercise): no `gh`/API call, no script, no edit to the real SKILL.md.
