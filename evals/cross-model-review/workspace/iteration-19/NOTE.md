# Iteration 19 (2026-11-20): evals 19-21 after the pre-PR cross-model-review fixes

Quick Workflow, `with_skill` only, no baseline arm, model claude-opus-5-5, plan-only dry runs (Read
only, nothing dispatched). Fixes since iteration 18, from the pre-PR `cross-model-review` run (Claude +
Codex): every batch is dry-run; the caller names secret-like hits per batch itself, since the
dispatcher reports only a count; `--secret-paths-confirmed` goes only on the confirmed batches, in
Phase 1 and Phase 2; declining Codex is single-model mode only when no optional model returned a valid
Phase 1 envelope. Eval 19's prompt was rewritten (two batches, a count-only dispatcher message) and gained
a fourth assertion; evals 18-22 now use relative `plugins/` paths.

| Eval | Result |
|---|---|
| 19 pick limit; dry-run failures; per-batch secret hits | 4/4 |
| 20 egress question; re-check | 4/4 |
| 21 per-batch failure; Codex unavailable | 3/3 |

Total: 11/11.

## Fixed after this run, not re-run

- Eval 21: `references/resolver-failure-handling.md` still described the full single-model path with no
  optional-model exception, and resolver step 3's question said "confirmed" where its sub-bullet says
  "returned a valid Phase 1 envelope". Both now match `optional-models.md` section 5.
- Eval 19: section 3 now says the flagged batch's dry run is re-run before the egress confirmation.

## Gaps surfaced, not changed (pre-existing re-check text)

- Eval 20: whether the pre-dispatch re-check compares against the original `$RVA`, and whether one
  vendor's changed dispatcher also drops the others.
- Eval 19: which `--model` to use if two batches' dry runs report different models.
