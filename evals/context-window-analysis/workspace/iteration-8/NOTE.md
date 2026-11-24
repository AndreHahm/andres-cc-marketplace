# Iteration 8 (2026-11-24): very slow responses and the Notes line

`skill-tester` Quick Workflow, `with_skill` only, plan-only, against branch `docs/context-kit-rulebook-gaps`
(issue #461). Round 3 of the cross-model review found that very slow responses had no status in Step 2 when
they were the only sign, and that the Notes line "When in doubt, /compact is safer than continuing"
contradicted Step 2. Step 2 now counts very slow responses as one Warning indicator, and the Notes line asks
for `/context` first. Eval 6 is new; evals 1, 3, 4 and 5 were re-run with their assertions unchanged. Grading
was done by the session that dispatched the agents, not blind to the scenario. With no baseline arm this
shows the text produces the intended status, not that it changed the outcome.

- **Evals 1 and 3:** 3/3 each (HEALTHY, MONITOR).
- **Evals 4 and 5:** 2/2 each (WARNING, MONITOR).
- **Eval 6** (very slow responses only, short session): 3/3. MONITOR estimate, no compact now.

Total: 13/13. Eval 2 (footprint audit) was not re-run; the changes do not touch its scope.
