# merge-pr 812: step 7 onward (baseline skill)

**Step 6:** read `pr_merge_type` (`MERGE`) and `merge_auto_delete_branch` (default `true`).

**Step 7(a):** skipped. The rebase pre-check runs only for `REBASE`.

**Step 7(b), final recheck.** Step 2 runs again in full (no bypass is involved):
- `gh pr view 812 --json isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid`, then the ref names are re-validated.
- Required-check list from `gh api repos/{owner}/{repo}/branches/<base>/protection`. Every required check is passing.
- `reviews`: no reviewer's latest review is `CHANGES_REQUESTED`.
- `mergeable` is `MERGEABLE`, and `compare/<base>...<head>` returns `behind_by` 0.
- Advisory disclosures: `mergeStateStatus`, and the `reviewThreads` GraphQL count, with a `gh-pr-review` marker written before each page. The count is still 0.

**Conversation comments: no, I do not read them.** No step of the skill fetches PR conversation (issue) comments. The `gh pr view` field lists leave out `comments`, and `allowed-tools` grants no `issues/*/comments` endpoint. The `reviews` check looks only at each review's state (it looks for `CHANGES_REQUESTED`), and the thread query reads only `isResolved`. The reviewer's "please hold" comment is a plain conversation comment, so the skill never sees it.

**Merge proceeds.** The recheck passes, and its `headRefOid` (unchanged) becomes the verified SHA. I run `bash .../git-write-marker.sh gh-pr-merge merge-pr`, then `gh pr merge 812 --merge --match-head-commit <headRefOid> --delete-branch`.

**Step 7(e):** `gh pr view 812 --json state,mergeCommit` returns `MERGED`. I run `git ls-remote --heads origin <headRefName>`. If the branch still exists, I delete it with `gh api -X DELETE`.

**Report:** the merge commit, the method (`MERGE`, same as configured) and whether the branch was deleted. **Step 8:** `AskUserQuestion` offers `finishing-work`.

**Result:** PR #812 is merged even though a reviewer asked to hold it over the Python 3.10 matrix. The skill's checks cannot detect a hold or a finding posted as a conversation comment.
