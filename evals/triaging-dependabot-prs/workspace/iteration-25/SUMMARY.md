# Iteration 25

New eval 22, for issues #739 and #740: step 6.4 now reads `head-runs` (the workflow runs on the PR's branch that
have not completed) before `pr-checks`, and does not treat CI as done while a run on the current head is unfinished.
`gh pr checks` shows one row per check name, so a passed run hides a queued rerun of the same workflow (#739), and a
run still `pending` has no check rows at all (#740). One simulated answer from a general-purpose subagent that read
the updated skill, graded by the author. A baseline answer from the pre-change skill (`1ffee03c`, its SKILL.md and
references only) was also graded.

| Eval | with_skill | baseline |
|---|---|---|
| 22: An unfinished run on the head blocks the CI gate even when every listed check passes | 5 of 5 | 1 of 5 |

The baseline read only `pr-checks`, found no blocker on either PR, asked nothing at 6.4 and sent both PRs to
`merge-pr`, relying on its branch-protection check; it said the skill has no read for the head's workflow runs.
Only assertion 5 (no raw `gh` call) passed.
