# Iteration 22

New eval 19, after CodeRabbit's first review round on PR #733 found two gaps in the review-finding stop: it read
`comments` only, so a finding left only in a review body was never seen, and the re-read before a real close or
`ignore` run asked again only if `unresolved_count` rose, so a resolved thread replaced by a new one went through.
The fix reads `pr-view <n> --fields comments,reviews` and gives the final re-read the same stop as the first check.
One simulated answer from a general-purpose subagent that read the fixed skill, graded by the author. A baseline
answer from the pre-fix skill (`72b25c95`, its SKILL.md only) was also graded.

| Eval | with_skill | baseline |
|---|---|---|
| 19: a review-body-only finding stops the merge, and a swapped unresolved thread stops the real close | 5 of 5 | 1 of 5 |

The baseline merged PR #401 without reading the review body and ran the real close of PR #402 because the count did
not rise (failed assertions 1 to 4). It named both as gaps in the skill.
