# merge-pr iteration 28 (2026-11-26, PR #922 review fixes)

Eval 52: step 1.5 runs the review-finding stop against step 1's head before pushing, and a reviewer's
latest `CHANGES_REQUESTED` review on an earlier head stays live.

| Arm | Skill text | Assertions |
|---|---|---|
| with_skill | worktree text with the review-round fixes | 4 of 4 |
| baseline | the skill at b8072bfa | 1 of 4 |

Both arms: claude-opus-5-5, one simulated answer each, graded by the author against
`eval-52/eval_metadata.json`. The baseline committed and pushed at step 1.5 before any review read, and
skipped the earlier-head `CHANGES_REQUESTED` review as not live (its change-requests gate still stopped
that variant). No `timing.json` was written; from the run notifications: with_skill about 160.7k tokens,
24 s; baseline about 143.6k tokens, 34 s. `benchmark.json`'s zero token and duration figures reflect the
missing timing files, not the cost.
