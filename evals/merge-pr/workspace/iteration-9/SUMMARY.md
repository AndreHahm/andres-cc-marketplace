# Iteration 9

New evals 16 and 17 for issue #732: the opt-in `--stop-on-review-findings` flag. With it, every step-2 pass,
including step 7(b)'s final recheck before the merge write, also reads conversation comments and review bodies
and stops on an unresolved thread or a finding. Without it, behavior is unchanged (closed issue #160).

Each configuration was one simulated answer from a general-purpose subagent, graded by the author. `with_skill`
read the fixed SKILL.md from the worktree. `baseline` read `main`'s SKILL.md at `62c7c920`, before the fix.

| Eval | with_skill | baseline |
|---|---|---|
| 16: with the flag, a finding posted during step 5 stops the merge at 7(b), before the marker | 5 of 5 | 1 of 5 |
| 17: without the flag, the same late comment does not stop the merge | 4 of 4 | 4 of 4 |

On eval 16 the baseline has no such flag. It ignored the flag, never read the comment, and merged the PR. Its one
pass (no triage) is vacuous. Eval 17 is the control case: both configurations merge without reading comments, which
confirms that the default behavior is unchanged.
