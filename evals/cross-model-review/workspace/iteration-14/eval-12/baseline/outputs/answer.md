# cross-model-review: what happens before Codex dispatch when packing yields 9 batches

> **Baseline answer.** I was told not to read the skill files (`SKILL.md`, `references/scoped-review.md`) or run anything, so this answer comes from general reasoning about how such a planner usually works. The only repo evidence I used is the recent commit subjects on this branch: "count only Codex-eligible batches in the batch-limit question" and "report batch-limit omissions in the scope report". Check the exact formula and wording against `references/scoped-review.md` before relying on them.

## 1. Which limit applies and how it is computed

- The planner's manifest gives two numbers. `budget_bytes = 250000` is the total review payload allowed for one round. `max_slice_bytes = 80000` is the largest slice that can go into one batch.
- The batch limit most likely comes from these two numbers rather than being a fixed constant: `floor(budget_bytes / max_slice_bytes) = floor(250000 / 80000) = floor(3.125) = 3` batches per round. A ceiling-based reading would give 4, so this is the point to check in the reference. Either way the limit is well under 9.
- Only **Codex-eligible** batches count against the limit. This follows from the commit "count only Codex-eligible batches". Batches that Codex will not review are left out of the count, for example ones handled only by Claude or excluded by policy. Protected slices that do go to Codex count normally. Because they are large, each one tends to fill a whole batch, which is why packing ended at 9.
- Codex-eligible batches (9, or slightly fewer if some are ineligible) exceed the limit (3), so the skill stops before any Codex dispatch.

## 2. Whether the user is asked, and what

Yes. The skill does not silently truncate, and it does not silently send all 9 batches. It asks one `AskUserQuestion` before Codex runs. The question states:

- the number of Codex-eligible batches (e.g. 9) against the computed limit (e.g. 3), along with the formula,
- that some large protected slices caused the overflow,
- which slices would fall outside the limit if the review were capped.

The likely options are:

1. **Review within the limit (cap).** Dispatch only the first N eligible batches, in the planner's priority order, so protected or high-risk slices go first.
2. **Review all batches (override).** Accept the extra cost and time, and dispatch all eligible batches this round.
3. **Cancel / narrow scope.** Stop before dispatch so the user can shrink the diff or pass an explicit path scope, then re-run.

## 3. What happens under each answer

- **Cap.** Codex gets only the batches within the limit. The rest are not reviewed by Codex this round. Claude's native review still covers the full diff, but cross-examination of the omitted slices is one-sided. The omission is recorded, as described in section 4.
- **Review all.** All Codex-eligible batches are dispatched, sequentially or in the skill's normal parallelism. No omission is recorded, and the round's coverage is complete.
- **Cancel / narrow.** No Codex call is made. Nothing is reviewed or recorded as reviewed. The user re-invokes with a smaller scope, and the planner recomputes the manifest and batches.

## 4. How unreviewed slices are reported and treated in a later round

- **Reporting.** The final output's scope or coverage report lists every slice that was not sent to Codex. This follows from the commit "report batch-limit omissions in the scope report". For each slice it gives the path or range, its size, whether it is protected, and the reason (batch limit, chosen by the user). The ranked findings table therefore cannot be read as covering the whole diff. The report says plainly that those slices had Claude-only review, or no Codex review.
- **Later rounds.** Omitted slices are treated as **not reviewed**, not as clean. A missing finding on an omitted slice is not evidence that the slice is fine. On the next round the slices are still pending, either carried over through the run record or picked up again because the diff still contains them, and the skill should rank them ahead of slices that were already reviewed. If they still do not fit, the same limit question is asked again rather than dropping them silently. The user is never told the diff was "fully cross-model reviewed" while omissions remain.
