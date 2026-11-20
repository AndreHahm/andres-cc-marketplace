# Iteration 18 (2026-11-20): re-run of evals 20-22 after the iteration-17 fixes

Renumbered since: this note's eval 18 is eval 29 and its scenarios 39-48 are 41-50 (rebase onto main).

Quick Workflow, `with_skill` only, no baseline arm, model claude-opus-5-5, plan-only dry runs (Read
only, nothing dispatched). Fixes since iteration 17: one `AskUserQuestion` call with one question per
vendor for egress; Claude's Phase 2 reads every confirmed optional model's envelopes; a Phase 1 typed
failure also skips that vendor's Phase 2 for the batch.

| Eval | Result |
|---|---|
| 20 egress question; re-check | 4/4 (was 3/4) |
| 21 per-batch failure; Codex unavailable | 3/3 |
| 22 N-model confidence | 4/4 |

Total: 11/11. With iteration 17's unchanged evals 18 and 19 (6/6), evals 18-22 stand at 17/17.

## Fixed after this run, not re-run

- Eval 21: resolver step 3's sub-bullet said "take the full single-model path" with no exception for
  a confirmed optional model, and did not say to ask once. Reworded so the single-model paths apply
  only when no optional model returned a valid envelope, and the question is asked once after every
  Phase 1 call has returned. The eval already passed on `optional-models.md` section 5.
- Eval 22: `optional-models.md` labeled its sections "Preflight step 8" and "9"; all three now say
  step 7, matching `SKILL.md`.
