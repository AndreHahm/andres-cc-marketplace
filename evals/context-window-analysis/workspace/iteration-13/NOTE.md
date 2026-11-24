# Iteration 13 (2026-11-24): the WARNING evals require the 80% threshold

`skill-tester` Quick Workflow, `with_skill` only, plan-only, against branch `docs/context-kit-rulebook-gaps`
(issue #461, PR #883). Review round 1 found that "if the measured percentage confirms it" also accepted advice
that excluded a measured 90% or more, and that the WARNING example told the user to act immediately on further
slowdown. Both assertions are tightened, and a third one checks the slowdown advice. Grading was done by the
session that dispatched the agents, not blind to the scenario; no baseline arm.

- **Eval 4:** 3/3.
- **Eval 7:** 3/3.

Earlier iterations keep the assertions they were graded with.
