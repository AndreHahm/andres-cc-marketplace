# merge-pr 903 (simulated, no flags): step-by-step

Scope: simulated exercise. No `gh`/`git` calls were made and no repository file was edited. The skill text was read from `plugins/git-kit/skills/merge-pr/SKILL.md` (and searched across its `references/`).

## Finding that decides the outcome

`merge-pr`'s SKILL.md and its `references/` (`merge-rights-check.md`, `development-history.md`, `test-scenarios.md`) contain no reference to `.claude/review-outcomes/` or `pr-903.json`. The skill has no gate that requires a review-outcomes record in the PR's changed-file list. The base branch's `.claude/review-outcomes/` directory and the PR's missing `pr-903.json` therefore do not block any step of this skill. The skill's own gates are the five readiness checks in step 2, plus merge rights in step 3.

Limitation: I was told not to read anything under `.claude/`. If the repository has a separate rule that requires a review-outcomes record, it lives outside this skill and I did not check it. That rule would need its own check; this skill does not perform it.

## Steps

1. **Resolve the PR (step 1).** Argument is `903` (digits only), so it passes validation. Run `gh pr view 903 --json ...`. The data is given as valid. Derive `{owner}/{repo}` from the `url` field. Because the argument was explicit, skip the `origin` identity comparison. Validate `headRefName` and `baseRefName` against `^[A-Za-z0-9._/@+=-]+$`. No `--expected-head-sha` was given, so no pin check.

2. **Session open-issues check (step 1.5).** Verify the checkout matches the PR: `isCrossRepository` false, `origin` identity matches, branch matches `headRefName`, `HEAD` equals `headRefOid`. Then scan this session for unaddressed findings or deferred items. None are supplied, so report "nothing found." Changed-file list comes from `gh api repos/{owner}/{repo}/pulls/903/files --paginate`. Not a gate here, since nothing was flagged. Any fix would be pushed, and step 2 would re-fetch.

3. **Readiness checks (step 2), all five must pass.**
   - Not draft: passes (given).
   - Required status checks: resolve the required list from `gh api repos/{owner}/{repo}/branches/<base>/protection`. Every context must be passing. Given that every other check passes, this is satisfied. If the protection call failed, I would stop rather than fall back to `gh pr checks`.
   - No `CHANGES_REQUESTED` in each reviewer's latest review: passes (given).
   - Mergeable is `MERGEABLE`: passes (given). Not `UNKNOWN`, which would need bounded polling.
   - Not behind base: for a same-repo PR, `gh api repos/{owner}/{repo}/compare/<base>...<head> --jq '.behind_by'` must be `0`. Given as passing.

4. **Advisory disclosures (step 2, non-blocking).**
   - `mergeStateStatus`: disclose the raw value even if `CLEAN`.
   - Unresolved review threads: the GraphQL `reviewThreads` query, paginated, with a fresh `gh-pr-review` marker before each call. Given count is 0 across all 4 threads (all resolved). Disclose "0 unresolved."
   - Review findings stop: applies only with `--stop-on-review-findings`. Not passed, so no comment or review-body read is required. The resolved threads do not by themselves stop the run.

5. **Merge rights (step 3).** Follow `references/merge-rights-check.md`'s three tiers in order, passing `{owner}/{repo}` from step 1. Stop at the first tier that decides. Not supplied, so this is an open assumption: the skill requires a `MERGE ALLOWED` result before continuing. If it is `MERGE NOT ALLOWED` because CODEOWNERS is missing, ask via `AskUserQuestion` about `manage-codeowners`. Any other failure stops the run.

6. **Bypass path (step 4).** Not entered. No `--bypass-codex-review` flag, and `Publish Codex policy result` is not the sole failing check.

7. **Confirm (step 5).** Use `AskUserQuestion` to show PR 903, its title, the readiness summary, `mergeStateStatus`, and the thread count of 0 (stated explicitly, not omitted). Note that branch deletion may print a local worktree error even when the merge succeeds. Proceed only on explicit yes.

8. **Settings (step 6).** Read `pr_merge_type` (default `REBASE`) and `merge_auto_delete_branch` (default `true`) from `.claude/git-kit.local.json` if present, else from the plugin's `git-kit.settings.json`.

9. **Rebase pre-check and final recheck (step 7a, 7b).**
   - If the strategy is `REBASE`, count merge commits in `pulls/903/commits`. If any, ask which alternate strategy to use before trying `--rebase`.
   - Immediately before the marker write, re-run the full step-2 readiness check without the bypass exception, re-fetching `headRefOid`. Write the marker with `git-write-marker.sh gh-pr-merge merge-pr` immediately before the merge, not earlier.
   - Run `gh pr merge 903 --<strategy> --match-head-commit <verified SHA>` and add `--delete-branch` if configured.
   - For `--squash`, disclose how many commits will collapse.

10. **Post-merge verification (step 7e).** Regardless of exit code, check `gh pr view 903 --json state,mergeCommit`. If `MERGED` and not from a fork, verify the remote branch with `git ls-remote --heads origin <headRefName>`, and clean up with the guarded `gh api -X DELETE` path only if the branch remains. Then offer the post-merge sync (step 8).

## Can the merge proceed?

Yes, provided the remaining gates resolve as assumed: merge rights (step 3) return `MERGE ALLOWED`, the step-7b recheck passes, and the user confirms at step 5. The missing `.claude/review-outcomes/pr-903.json` is not a blocker under this skill, and the empty unresolved-thread count is disclosed, not treated as a stop. The review-outcomes directory on the base branch is not part of any step here, so this skill neither requires nor checks it.
