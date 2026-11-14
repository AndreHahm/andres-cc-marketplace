# Iteration 19

New eval 17 for issue #730: on a request that names both the batch and the reviewer findings, the skill reads `pr-threads` and the PR's comments immediately before a close (6.2) or merge (6.6), and an unresolved inline thread stops for the `handling-review-findings` question. One simulated answer from a general-purpose subagent that read the edited skill, graded by the author. A baseline answer from the pre-change skill (`ccc79af7`) was also graded; its prompt gave the thread facts in prose, because that skill has no thread read.

| Eval | with_skill | baseline |
|---|---|---|
| 17: PR #201 (unresolved inline thread, no reviewer comment) stops before the close question; PR #202 (all threads resolved) is not stopped and its resolved count is reported | 5 of 5 | 2 of 5 |

The baseline disclosed that it could not see inline threads, but went on to the close question with only a caveat and could not report thread counts (failed assertions 1, 2 and 4).
