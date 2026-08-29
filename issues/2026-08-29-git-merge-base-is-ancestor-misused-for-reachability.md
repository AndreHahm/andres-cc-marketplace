## Summary
`git merge-base --is-ancestor <sha> HEAD` was used to validate that a cherry-pick candidate commit exists and is reachable — but a normal cherry-pick candidate living only on a feature branch is *intentionally* not an ancestor of the target, so this check rejected precisely the commits that needed the operation, inverting its own purpose.

## Environment
- **Product/Service**: `git-kit` plugin — `git-worktrees`/`merge-pr`'s Strategy C cherry-pick path
- **Region/Version**: this repo, found during PR #148 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Identify a commit that exists only on a feature branch and hasn't been merged to the target branch — a completely normal, valid cherry-pick candidate.
2. Run `git merge-base --is-ancestor <sha> HEAD` against the target branch.
3. Observe the command exits non-zero (false) — Git's own `git merge-base -h` describes `--is-ancestor` as "is the first one ancestor of the other?", not an object-existence or general reachability check.
4. A validation step using this exit code to mean "commit doesn't exist / isn't valid" incorrectly rejects the commit.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| `git merge-base --is-ancestor <sha> HEAD` can confirm a commit exists/is reachable | It answers a narrower question — "is the first ref an ancestor of the second" — which a legitimate not-yet-merged commit fails by design |

## Expected Behavior
Verify a commit's existence with `git cat-file -e <sha>^{commit}` and its reachability with `git branch --all --contains <sha>`; reserve `--is-ancestor` for its actual purpose (checking whether one ref is already integrated into another).

## Actual Behavior
The strategy rejected exactly the commits it needed to cherry-pick, since a legitimate not-yet-merged commit fails the ancestry check by design.

## Impact
[Severity: High] This broke the core cherry-pick strategy for its most common case — a commit not yet merged into the target. Fixed in `git-kit`'s PR #148 (commit `d9bfdc1`): replaced `git merge-base --is-ancestor <sha> HEAD` with `git cat-file -e <sha>^{commit}` plus `git branch --all --contains <sha>`. Live-verified before the fix: an unmerged commit correctly fails `--is-ancestor` against a target branch even though it's a valid cherry-pick candidate, and `git branch --all --contains` still finds it. Re-verified after: `evals/git-worktrees` eval 3 re-graded 4/4 pass.

## Additional Context
Mined from PR #148's own review history (`chatgpt-codex-connector[bot]`; 12 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #148` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This extends the repo-wide "verify tool/API/language behavior before instructing" theme already tracked in `.claude/rules/verify-tool-behavior-before-instructing.md` with a new concrete Git-semantics instance.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/148#discussion_r3872420061
