# Iteration 31 (2026-11-25): optional models after the rebase onto main (PR #879 port)

`with_skill` only, no baseline arm, model claude-opus-5-5 (the session's model), plan-only dry runs, nothing
dispatched. Graded by the authoring session. Changes since iteration 22: vendors get no sensitive file and no
finding that quotes one, the bare plugin root, and the `node` path the locator prints. Eval 19's
`config/api-token.json` became `config/hosts.yml`, because the planner no longer lets the old name reach a vendor.

| Eval | Result |
|---|---|
| 19 pick limit; dry-run failures; every path of the flagged batch named | 4/4 |
| 30 sensitive names, node and plugin root | 7/7 |

Full responses were not saved. Evals 20-24 and 29 were not run again after the rebase.
