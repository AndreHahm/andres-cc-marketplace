# Iteration 17 (2026-11-20): optional models, issue #541 Part B

Quick Workflow, `with_skill` only, no baseline arm, model claude-opus-5-5. Plan-only dry runs: each
agent read the worktree's unmerged `SKILL.md` and `references/optional-models.md` with Read only and
dispatched nothing. Evals 18-22 cover scenarios 39-48 of `references/testing-scenarios.md`.

| Eval | Scenarios | Result |
|---|---|---|
| 18 locator fails; PLANNER_TOUCHED | 39, 47 | 3/3 |
| 19 three picks; vendor_not_allowed; secret_paths_unconfirmed | 40, 41, 42 | 3/3 |
| 20 egress question; re-check | 43, 48 | 3/4 |
| 21 per-batch failure; Codex unavailable | 44, 45 | 3/3 |
| 22 N-model confidence | 46 | 4/4 |

Total: 16/17 assertions.

## Gaps the agents surfaced

1. Eval 20 (failed assertion): the agent asked one `AskUserQuestion` per vendor, not one call with
   one question each. Section 3's bold lead ("one egress confirmation per remaining vendor") invites
   that reading.
2. Eval 22: `SKILL.md` Phase 2, "Claude's native pass", still names only the Codex envelopes, while
   `optional-models.md` section 4 widens it to every other model's findings.
3. Eval 21: whether "skipped for that batch" after a Phase 1 typed failure also skips that vendor's
   Phase 2 for the batch is ambiguous.
