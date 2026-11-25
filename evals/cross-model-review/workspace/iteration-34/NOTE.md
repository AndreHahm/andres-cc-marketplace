# Iteration 34 (2026-11-25): evals 20 and 31 after the re-check gained `identity`

`with_skill` only, no baseline arm, one plan-only run per eval, nothing dispatched, agents dispatched with the `opus`
model alias, graded by the authoring session from the agents' returned summaries. Eval 31 gained Case E before the run.

| Eval | Result |
|---|---|
| 20 egress question and re-check | 4/4 |
| 31 node shim, resolved node path, disclosed limits, identity | 7/7 |

Evals 19, 21-24, 26 and 28 were not run again. The locator's checks are covered by
`tests/marketplace_ci/test_git_review_locate_rva.py`, not by these runs.
