# Iteration 20 (2026-11-20): evals 19-21 and new eval 23 after PR #804's round-1 review fixes

Quick Workflow, `with_skill` only, no baseline arm, model claude-opus-5-5, plan-only dry runs (Read
only, nothing dispatched). Fixes since iteration 19, from PR #804's CI review round (Devin, Codex,
CodeRabbit, Claude):

- A changed `dispatcher` at the re-check drops every optional vendor still to dispatch, not only the one
  being re-checked (eval 20's fourth assertion and expected output changed to match).
- Every batch's dry run must report the same `model`; a different one drops the vendor (new eval 23).
- `resolver-failure-handling.md`: with Codex failed on every batch, Phase 2 runs between Claude and the
  optional model only for batches with that model's valid envelope (eval 21 gained a fourth assertion).
- Also re-run here: iteration 19's two post-run edits (resolver step 3 wording, the flagged batch's
  dry-run re-run), which had not been re-run.

| Eval | Result |
|---|---|
| 19 pick limit; dry-run failures; per-batch secret hits | 4/4 |
| 20 egress question; changed dispatcher drops every vendor | 4/4 |
| 21 per-batch failure; Codex unavailable; per-batch Phase 2 | 4/4 |
| 23 model differs between batches | 3/3 |

Total: 15/15.

## Edited after this run, not re-run

- `optional-models.md` section 1: a note that a group-writable `installed_plugins.json` (outside the
  private-group exception) refuses the sibling lookup and the config path is the way around it. Locator
  wording only; no eval covers section 1's locator details.

## Gaps surfaced, not changed

- Eval 20: the wording of the `DISPATCHER_TOUCHED` disclosure for an optional vendor; re-check timing when
  vendors dispatch in parallel; whether the user is told of a re-check drop at once.
- Eval 23: which dry run is "the first" when they run in parallel (the outcome is the same); no
  `inspection_limits` category name for a model mismatch.
- Eval 19: whether a vendor's remaining dry runs still run once one batch dropped it.
- Eval 21: whether resolver step 3's "every dispatched Phase 1 call" includes the optional model's calls.
