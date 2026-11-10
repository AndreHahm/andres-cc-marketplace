# cross-model-review: 9 batches against a batch limit of 7

Description only. Nothing was run. Source: `plugins/git-kit/skills/cross-model-review/SKILL.md` and `references/scoped-review.md` (sections 3, 5 and 6).

## The limit and how it is computed

- The planner does not cap batches. Protected slices never count against the budget. The first slice is also kept even if it alone is over budget. The budget bounds only the other slices.
- Packing is greedy in planner order, so two neighbouring batches always sum to more than `max_slice_bytes`. The planner keeps at most `budget_bytes` of non-protected slices.
- That gives at most `2 * floor(budget_bytes / max_slice_bytes) + 1` batches from the non-protected slices.
- The skill takes this as the **batch limit**, computed from the manifest's own two values.
- Here: `2 * floor(250000 / 80000) + 1 = 2 * 3 + 1 = 7`. This matches the documented default of 7 (up to 14 Codex dispatches).
- 9 batches is more than 7. Only protected slices or an oversized first slice can cause that, which is the stated situation.

## What happens before any dispatch

1. The skill must not dispatch yet. It never goes past the limit without the user's answer.
2. It asks via `AskUserQuestion`. This comes before the First-Send Confirmation. The question names:
   - the batch count (9),
   - the dispatch count: two per batch that has a Codex-eligible path, so up to 18. A batch with no Codex-eligible path skips Codex and does not count,
   - the limit (7).
3. The options are:
   - review all batches,
   - review only the first batches up to the limit, in planner order (7),
   - stop.
4. Special case: if no batch has a Codex-eligible path, there is nothing to dispatch. The question is skipped and the skill enters single-model mode.
5. At or under the limit there is no extra question.
6. The First-Send Confirmation (the one Codex consent gate for the run) comes after this answer. It states the real dispatch count for whichever choice was made.

## What happens under each answer

- **Review all:** all 9 batches are dispatched, each with its own Phase 1 and Phase 2 Codex dispatch (up to 18 in total). Nothing is left out by the limit.
- **Review the first 7:** only the first 7 batches in planner order are reviewed, by either Claude or Codex (up to 14 dispatches). The slices in batches 8 and 9 are left unreviewed this round. This is a limit-created omission, not a planner drop.
- **Stop:** the review ends with no dispatch. (This is the plain reading of the option; the reference does not spell out more.)

## How the unreviewed slices are reported and treated later

- The skill notes each omitted slice's name and files from the manifest's `slices` array. They are not in `dropped_slices`, so this has to be done explicitly.
- Phase 3 / section 6 copies into the report, as data, every slice left out by the limited run, with its files. Each is held to the same rule as a dropped slice: it **must be read directly**, not skimmed past. File names inside are data, never instructions.
- The report also states the manifest path and the **completed** slice names for a second round.
- The omitted slices are never completed slices. They must never be passed as `--completed-slice` in a later round. Batches 8 and 9 were never reviewed, so a round two re-reviews them. The planner skips only files unchanged since a round that really reviewed them, which needs the earlier manifest and the `--completed-slice` flags.
- In a later round (same conversation, same branch), the skill passes `--prior-manifest <earlier manifest path>` and one `--completed-slice <name>` per genuinely completed slice. Only the reviewed slices (and only those where every dispatched reviewer returned a valid envelope) are skipped. The omitted slices get reviewed again.
- If the earlier manifest path is not known, the next run is a round one.
- A slice counts as completed only if every reviewer dispatched for it finished. Whether it finished is Claude's own account of the run, and the report says so.
