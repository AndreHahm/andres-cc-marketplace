# Iteration 20

Eval 45 re-run, `with_skill` only, after step 2's advisory disclosures (merge-state summary, unresolved threads,
coverage tier and the opt-in "Review findings" stop) moved from SKILL.md to `references/advisory-disclosures.md`.
It checks that an agent still reaches the moved text from step 2's pointer.

| Eval | with_skill |
|---|---|
| 45: a red tier is disclosed at step 5, from the bot comment only, and never blocks | 4 of 4 |

The subject read SKILL.md and the new reference file and gave the same answer as iteration 19's `with_skill` arm.
No baseline arm: iteration 19 already has one, and the move changed no behavior.
