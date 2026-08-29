## Summary
A tree-hash-equality dedup heuristic classified two commits as redundant duplicates whenever they produced the same resulting tree — but a commit that reverts an intermediate change back to an earlier tree is tree-identical to that earlier commit while still being required to replay correctly, so the heuristic could silently drop a necessary commit.

## Environment
- **Product/Service**: `git-kit` plugin — `git-worktrees`/`merge-pr`'s Strategy C cherry-pick path
- **Region/Version**: this repo, found during PR #148 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Construct a 3-commit sequence: commit A establishes a tree, commit B changes it, commit C reverts B back to A's original tree.
2. A's tree and C's tree are identical (same tree hash), even though C is a distinct, necessary commit — omitting it while replaying A→B leaves B's change applied when it shouldn't be.
3. A tree-hash-equality check treats A and C as "duplicate, safe to drop one" and removes C from the resolved cherry-pick list.
4. Replaying the resulting list leaves B's change in place, producing an incorrect result — the revert never happened in the target.

## Expected Behavior
Tree-hash equality between two commits should trigger history-aware investigation (or a user-facing confirmation), never automatic removal from a resolved commit list — content equality doesn't imply the commit is redundant.

## Actual Behavior
The strategy classified the revert commit as a safe-to-drop duplicate purely on tree-hash equality, which would silently produce an incorrect cherry-picked result for this common revert shape.

## Impact
[Severity: High] A dedup heuristic silently corrupting the result of a cherry-pick operation is a serious, hard-to-notice correctness bug — the resulting branch would look successfully cherry-picked while missing a real change. Fixed in `git-kit`'s PR #148 (commit `d9bfdc1`): the tree-hash-match check no longer concludes one commit is automatically a safe-to-drop duplicate — it now flags the match for history-aware investigation, explicitly naming the legitimate-revert case. Verified: re-ran `evals/git-worktrees` eval 3 against the fixed skill — the agent correctly reasoned through the revert scenario and deferred to user confirmation rather than auto-dropping either commit (re-graded 4/4 pass).

## Additional Context
Mined from PR #148's own review history (`chatgpt-codex-connector[bot]`; 12 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #148` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/148#discussion_r3872420069
