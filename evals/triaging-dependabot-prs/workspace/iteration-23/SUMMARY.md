# Iteration 23

New eval 20, after the Codex delta review on PR #733 (head `f8d5626e`) found that the review-finding stop offered
to "triage with `handling-review-findings`" although the skill grants no `Skill(handling-review-findings)`. The
fix makes the hand-off a separate user step: the stop asks whether to hold the PR for triage or leave it out of
the batch, the skill never invokes `handling-review-findings`, and a held PR is recorded as pending triage with
the user told to check it out and run that skill there. One simulated answer from a general-purpose subagent that
read the fixed skill, graded by the author. A baseline answer from the pre-fix skill (`f8d5626e`, its SKILL.md
only) was also graded.

| Eval | with_skill | baseline |
|---|---|---|
| 20: holding a PR for triage never dispatches handling-review-findings | 5 of 5 | 4 of 5 |

The baseline reached the same outcome by inferring it from `allowed-tools`, and said the skill text does not
state what happens after the triage answer; it did not tell the user to check out the PR (assertion 4). The
measured difference is small: the fix mainly makes stated what the baseline had to infer.
