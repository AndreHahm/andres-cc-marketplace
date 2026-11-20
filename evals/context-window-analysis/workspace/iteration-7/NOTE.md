# Iteration 7 (2026-11-20): Step 2 estimate paths after the second cross-model review

`skill-tester` Quick Workflow, `with_skill` only, plan-only, against branch `docs/context-kit-rulebook-gaps`
(issue #461). Round 2 of the cross-model review found that a single unrelated Critical sign gave a
CRITICAL estimate, and that no eval reached the Warning paths. Step 2 now counts a Critical sign only
when it is tied to the context itself, and evals 3-5 were added to cover the estimate mapping. Grading
was done by the session that dispatched the agents, not blind to the scenario.

- **Eval 3** (one Warning sign, long session): 3/3. MONITOR estimate, no `/compact` or `/clear` now,
  asks for `/context`.
- **Eval 4** (two Warning signs): 2/2. WARNING estimate, run `/context` and compact only if confirmed.
- **Eval 5** (unrelated failed command, short session): 2/2. MONITOR, not CRITICAL; no compact now.

Eval 4's agent noted that the WARNING worked example in `references/context-window-examples.md`
recommended "Run /compact" for an estimate, which contradicted the new rule; the example was changed in
the same commit to ask for `/context` first. The runs used the example before that change.
