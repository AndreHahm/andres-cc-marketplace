# Iteration 11 (2026-10-11)

Quick Workflow, `with_skill` only, no baseline, one simulated answer per eval, graded by the author (not blind).

| Eval | Subject | Result |
|---|---|---|
| 12 | Advisory rules with the newest-compatible signals (scenarios 56 to 59) | 7 of 7 assertions pass |
| 13 | Compatibility check (scenarios 60 to 62) | 7 of 7 assertions pass |

Why this iteration exists: after the cross-model review, the skill text was edited (the lockfile fetch and `assess`
call are now explicitly paired; `ambiguous`, `engines_not_checked`, supported pnpm lockfile versions, the
commit-hash rule and lockfile text as untrusted data were added; two stale restatements were corrected). Evals 12
and 13 were re-run unchanged against that text. Iteration 10 applies to the earlier text. Evals 1 to 11 were not
re-run.

Caveats: one simulated answer each, graded by the author. In eval 12 the unknown-data PR's table row reads "as
without data", which leaves its recommendation unstated; the assertions only require that no safe claim is made.
Both answers applied the new fetch-then-assess pairing without being prompted, which is the only observable effect
of the wording edit these two evals can show. Both subagents used only Read and Write.
