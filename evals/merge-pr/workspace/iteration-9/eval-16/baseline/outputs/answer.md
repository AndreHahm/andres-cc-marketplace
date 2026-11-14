# merge-pr 812 --stop-on-review-findings: step 7 onward (baseline skill)

**The flag:** the skill defines only `--bypass-codex-review "<reason>"` and `--expected-head-sha <sha>`. It does not define `--stop-on-review-findings` and says nothing about unknown flags. Step 1 validates only the PR-reference part (`812`, digits only, so it is valid). I treat the unknown flag as having no effect and tell the user it was ignored, the same way the skill handles `--expected-head-sha` given without the bypass. Nothing in the skill gives this flag any behavior, so it does not change anything below.

**Step 6:** read `pr_merge_type` (`MERGE`) and `merge_auto_delete_branch` (default `true`).

**Step 7(a):** skipped. The rebase pre-check runs only for `REBASE`.

**Step 7(b), final recheck.** Step 2 runs again in full, without the bypass exception:
- `gh pr view 812 --json isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid`, then the ref names are re-validated.
- `gh api repos/{owner}/{repo}/branches/<base>/protection` for the required-check list. Every required check is still passing.
- `reviews`: no latest review is `CHANGES_REQUESTED`. The reviewer's "please hold" is a conversation comment, not a review, so this check does not see it.
- `mergeable` and the `compare/...behind_by` call both pass.
- Advisory: the `reviewThreads` GraphQL count, with a `gh-pr-review` marker written before each page. It is still 0, because no thread was opened.
- The skill never reads PR conversation comments (issue comments) or review bodies. None of its fetches includes them, and `allowed-tools` has no grant for `issues/*/comments`. The hold request is never read.

The recheck passes, so I take its `headRefOid` as the verified SHA, which is unchanged.

**The marker is written:** `bash .../git-write-marker.sh gh-pr-merge merge-pr`.

**The merge runs:** `gh pr merge 812 --merge --match-head-commit <headRefOid> --delete-branch`. The squash disclosure in 7(c) does not apply.

**Step 7(e):** `gh pr view 812 --json state,mergeCommit` returns `MERGED`. The PR is same-repo and auto-delete is on, so I run `git ls-remote --heads origin <headRefName>`. If the branch is still there, I delete it with `gh api -X DELETE .../git/refs/heads/<branch>`.

**Report:** the merge commit and method (`MERGE`, as configured), the branch-deletion result, and that `--stop-on-review-findings` was not recognized and was ignored. **Step 8:** `AskUserQuestion` offers `finishing-work`.

**Gap:** under this skill, PR #812 is merged even though the reviewer asked to hold it. The skill has no step that reads conversation comments and nothing that stops on a finding posted there, with or without the flag.
