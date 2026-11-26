# Iteration 21

New eval 46 for the cross-model-review fixes to step 2's coverage-tier disclosure: a green comment next to a
COMPLETED/FAILURE check is flagged as possibly from an earlier head, a FAILURE reads as orange, red or not
computed, and with `--stop-on-review-findings` the `github-actions` coverage comment is a status while a
look-alike comment from another author is classified like any other body.

One simulated answer per configuration from a general-purpose subagent (claude-opus-5-5), graded by the author.
`with_skill` read the worktree's files after the fixes; `baseline` read SKILL.md and
`references/advisory-disclosures.md` as committed at `2c807e39`, before them.

| Eval | with_skill | baseline |
|---|---|---|
| 46: stale green comment next to a failed check, and a look-alike comment under the flag | 4 of 4 | 3 of 4 |

The eval separates the arms only weakly: the baseline inferred the stale caveat on its own, from "the job fails
on an orange or red tier", which is the wrong reason (it omits a tier that could not be computed), and it also
treated the coverage comment as a status without being told.
