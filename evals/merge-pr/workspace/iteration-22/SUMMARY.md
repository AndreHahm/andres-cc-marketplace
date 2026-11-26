# Iteration 22

New eval 47 for the second cross-model-review round's fixes to step 2's coverage-tier disclosure: a fork PR in a
repository that copied quality-kit's workflow template, so the check is named `coverage-tier` and no tier
comment exists.

One simulated answer per configuration from a general-purpose subagent (claude-opus-5-5), graded by the author.
`with_skill` read the worktree's files after the fixes; `baseline` read SKILL.md and
`references/advisory-disclosures.md` as committed at `0f443961`, before them.

| Eval | with_skill | baseline |
|---|---|---|
| 47: fork PR, `coverage-tier` check, no tier comment | 4 of 4 | 4 of 4 |

No measured separation. The baseline reached the same outcome only by departing from its own text: it noted
that, read literally, its exact-name rule would miss the `coverage-tier` check and report "no coverage tier
was reported", called that a gap in the skill, and reported the check anyway. The fixed text makes that the
instructed behavior instead of a judgment call.
