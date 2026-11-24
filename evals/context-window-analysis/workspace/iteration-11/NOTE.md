# Iteration 11 (2026-11-24): CRITICAL example names its Critical sign

`skill-tester` Quick Workflow, `with_skill` only, plan-only, against branch `docs/context-kit-rulebook-gaps`
(issue #461). Round 6 of the cross-model review found that the CRITICAL worked example in
`references/context-window-examples.md` showed repeated auto-compactions and no Critical sign, while Step 2
maps auto-compact messages alone to WARNING. The example now names a truncated conversation as its Critical
sign. Grading was done by the session that dispatched the agent, not blind to the scenario; there is no
baseline arm, and the old example was not run against this eval.

- **Eval 7** (three auto-compact messages, no Critical sign): 2/2. WARNING estimate, measure before compacting.

The other evals were not re-run; none reaches the CRITICAL example.
