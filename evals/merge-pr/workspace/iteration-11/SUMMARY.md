# Iteration 11

New eval 18, for issue #741: `--expected-head-sha` is no longer bypass-only. Step 1 stops when the PR's head differs
from it and step 7(b) merges only that SHA, so `triaging-dependabot-prs` can pin the merge to the head its step 6.4
checked. One simulated answer from a general-purpose subagent that read the updated skill, graded by the author, and
a baseline answer from the pre-change skill (`bcf620a4`, its SKILL.md and references only).

| Eval | with_skill | baseline |
|---|---|---|
| 18: --expected-head-sha without the bypass pins the merge | 4 of 4 | 1 of 4 |

The baseline ignored the flag, as the pre-change skill says: in Case A it carried on and would merge the moved head
`dddd` after the user's confirmation, and in Case B it re-asked and would merge `eeee` on a yes. Only Case C, where
the head never moved, passed.
