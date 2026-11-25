Next:
1. Read ENG-230's current status through `Skill(linear-work-management)`.
2. If native automation has already moved it, preserve that state and report it as drift for the user to take to `linear-github-reconciliation`. I don't dispatch that skill.
3. Otherwise, ask via `AskUserQuestion` whether to move ENG-230 to In Review. If yes, do it through `Skill(linear-work-management)` and read the status back. On no or no answer, leave it unchanged.

Why: step 10 allows the move because the approved workflow calls for it as a deliberate step. But the skill exempts only summaries that don't change workflow status from approval, and step 7's confirmation covered readiness. It doesn't explicitly list step 10 as approval-required, so asking is my inference.
