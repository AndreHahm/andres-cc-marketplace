# Iteration 33 (2026-11-25): evals 29, 30 and new eval 31 after the node shim and resolved-path change

`with_skill` only, no baseline arm, one plan-only run per eval, nothing dispatched, agents dispatched with the `opus`
model alias, graded by the authoring session from the agents' returned summaries. Full answers are in each
`with_skill/outputs/response.md`.

| Eval | Result |
|---|---|
| 29 locator fails; review scripts touched | 3/3 |
| 30 sensitive names, node, plugin root, NODE_* | 8/8 |
| 31 node shim, resolved node path, disclosed limits (new) | 6/6 |

Evals 20-24, 26 and 28 were not run again. The locator's checks are covered by
`tests/marketplace_ci/test_git_review_locate_rva.py`, not by these runs.
