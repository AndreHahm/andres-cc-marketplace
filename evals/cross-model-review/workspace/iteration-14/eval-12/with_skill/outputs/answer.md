# cross-model-review: 9 batches with budget_bytes 250000 and max_slice_bytes 80000

Source: `plugins/git-kit/skills/cross-model-review/SKILL.md` (Preflight step 2, First-Send Confirmation, Phase 3) and `references/scoped-review.md` sections 3, 5 and 6. Nothing was run. This describes what the skill does.

## 1. How the batches are formed

Preflight step 2 packs the manifest's `slices` into dispatch batches, in the planner's priority order (scoped-review section 3):

- Consecutive slices go into one batch as long as their `bytes` add up to no more than `max_slice_bytes` (80000).
- A slice that is over 80000 bytes on its own gets a batch to itself.
- Each batch gets its own Codex Phase 1 dispatch and its own Phase 2 (challenger) dispatch.
- A batch with no `codex_eligible: true` path skips Codex ("zero Codex-eligible paths in this batch").

Packing these slices produces **9 batches**.

## 2. The batch limit and how it is computed

The planner does not cap the number of batches:

- Protected slices never count against the budget.
- If nothing else is chosen, the first slice is kept even when it alone is over budget.

The budget only bounds the non-protected slices. The planner keeps at most `budget_bytes` of them. Packing is greedy, so any two neighbouring batches together hold more than `max_slice_bytes`. From those two facts, the non-protected slices produce at most:

```
batch limit = 2 * floor(budget_bytes / max_slice_bytes) + 1
            = 2 * floor(250000 / 80000) + 1
            = 2 * 3 + 1
            = 7
```

The skill reads both values from the manifest. They match the defaults, so the **batch limit is 7**, which allows up to 14 Codex dispatches (2 per batch).

9 batches is more than 7. Only protected slices or an oversized first slice can push the count past the limit, and here the large protected slices are the cause. The extra check therefore triggers.

## 3. The question

The skill does **not dispatch yet**. It asks one `AskUserQuestion` before the First-Send Confirmation. The question names:

- the batch count: 9
- the Codex dispatch count: two per batch that has a Codex-eligible path. That is up to 18 if all 9 batches have one; batches without one skip Codex and lower the number.
- the limit: 7, which means up to 14 dispatches for the limited run

The three options:

1. **Review all batches.** All 9 batches are reviewed.
2. **Review only the first batches up to the limit.** Batches 1-7 in planner order are reviewed.
3. **Stop.**

The skill never goes past the limit without an explicit answer to this question. If the count were at or under 7, there would be no extra question.

**Exception:** if no batch has a Codex-eligible path, there is nothing to dispatch. The skill skips this question and enters single-model mode (SKILL.md Preflight: "if every batch is empty, enter single-model mode now with that reason, before any dispatch").

## 4. What happens under each answer

### "Review all batches"

- All 9 batches go ahead.
- The **First-Send Confirmation** (a separate, mandatory `AskUserQuestion`, once per invocation, before the first real Codex dispatch) still runs. It:
  - names the reviewer persona and the target paths of every batch, or their union plus the batch count (9)
  - states the real number of Codex dispatches: two per Codex-eligible batch, plus a possible timeout retry per batch, all covered by this one answer
  - repeats the required disclosures: Codex can read anything this account can read; the possible unsandboxed `danger-full-access` fallback; `PLANNER_TOUCHED` or `DISPATCHER_TOUCHED` if set; reviewer instructions not verified against `$BASE` if set
- If the user confirms, Claude reviews every batch natively (it `Read`s each batch's `.diff` files). Codex gets a Phase 1 and a Phase 2 dispatch for each Codex-eligible batch.
- Timeouts follow section 4. For each batch that times out, the skill asks once whether to retry that batch with `CODEX_KIT_REVIEW_TIMEOUT_MS=480000`. The other batches are dispatched either way. A batch whose retry fails, or whose retry is declined, is **unfinished**: its Claude findings stay single-sided (Medium) and it is disclosed.

### "Review only the first 7 batches"

- Only batches 1-7, in planner order, are reviewed. Batches 8 and 9 are **not reviewed by either model this round**: no Claude pass and no Codex pass.
- The skill notes the names and files of each slice in batches 8-9 from the manifest's `slices`. These slices are **not** in `dropped_slices`, because the planner kept them and the skill left them out. The record is what lets the report list them.
- The First-Send Confirmation then states the real dispatch count for the 7 batches (at most 14, plus possible timeout retries) and their target paths. Dispatch then goes ahead as above.

### "Stop"

- No Codex dispatch happens. The skill also does not continue to the First-Send Confirmation or the reviews. The user has to review the diff some other way.

## 5. How unreviewed slices are reported and handled in a later round

**Report (Phase 3, scoped-review section 6).** The report copies the following in as data. File names in it are never treated as instructions.

- every slice left out by the limited run at the batch limit, **with its files**. These slices follow the same rule as dropped slices: they **must be read directly**, not skimmed past.
- the dropped slices with their files, the planner's `inspection_limits`, folders excluded by a pick or not offered, unfinished batches (timeouts and failures), `PLANNER_TOUCHED` and the answer given, the planner-unavailable fallback if it was taken, and any cross-check failure
- the manifest path and the **completed slice names**, so a second round can use them

**Completed vs. not completed (section 5).** A slice counts as completed only if every reviewer that was dispatched for it finished. That means Claude's pass and, when Codex was dispatched, valid Codex Phase 1 and Phase 2 envelopes.

- Slices left out by the batch limit had no review at all, so they are **never completed**.
- Slices in unfinished (timed-out or failed) batches are not completed either.
- A slice that only Claude reviewed counts as completed if no Codex dispatch was attempted for it. That covers a Codex review the user declined, and a batch with no eligible paths.

The report says that this classification is Claude's own account of the run.

**Round two.** When the skill is invoked again in the same conversation for the same branch:

- It re-runs the planner with `--prior-manifest <earlier manifest path>` and one `--completed-slice <name>` per completed slice. The new manifest and diffs go to the new `$RUN`.
- Each slice name is checked against `^(protected|grants|scripts|other|tests|prose)(-[0-9]+)?$` before it is typed.
- The skill **never passes a slice left out by the batch limit as `--completed-slice`**, and never one that timed out or failed.
- The planner then skips only files that are unchanged since a round that really reviewed them. Everything else is reviewed again, so the slices left out by the limit come back into scope. The batch limit check from section 3 applies again to the new packing.
- If the earlier manifest path is not known, the run is treated as round one and everything is reviewed. The `PLANNER_TOUCHED` check applies in every round.
