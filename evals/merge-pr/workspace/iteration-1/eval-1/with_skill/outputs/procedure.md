# Step 7 Procedure: Merge Command Non-Zero Exit with Successful Remote Merge

## Scenario
- Command: `gh pr merge 142 --rebase --delete-branch`
- Exit code: non-zero
- stderr: `fatal: 'main' is already used by worktree '/repo'`
- State verified: `MERGED` (remote merge succeeded)
- headRefName: `feat/some-feature`
- merge_auto_delete_branch: `true`

## Procedure (Step-by-Step)

### Step 1: Verify Remote Branch Status
Since `merge_auto_delete_branch` is `true`, the `--delete-branch` flag was passed. The local worktree conflict error prevented the local half of `gh pr merge` from completing, but we must verify whether the remote deletion actually succeeded or was skipped by the GitHub API.

**Run:** `git ls-remote --heads origin feat/some-feature`

### Step 2a: If Remote Branch Already Deleted (empty output)
- No further action needed
- Report: "Merge succeeded (rebase method). Remote branch feat/some-feature was deleted (despite the local worktree error)."
- Proceed to Step 8 (post-merge sync offer)

### Step 2b: If Remote Branch Still Exists (non-empty output)
The local worktree-conflict error stopped `gh pr merge`'s local half, which silently skipped the remote deletion. Complete the deletion manually via API.

### Step 3: Validate headRefName Against Safe Pattern
Before constructing an API call, validate `headRefName` to prevent injection.

**Check:** Does `feat/some-feature` match `^[A-Za-z0-9._/-]+$`?
- `feat/some-feature` contains: letters (f, e, a, t, s, o, m, e, t, u, r), forward slash, hyphen
- Result: **MATCHES** — all characters are safe

### Step 4: Delete Remote Branch via API Fallback
**Run:** `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/feat/some-feature`

(Substitute actual repo owner and name; for example, in the andres-cc-marketplace repo with owner, the full path would be `repos/andres-cc/andres-cc-marketplace/git/refs/heads/feat/some-feature` or equivalent with the actual org/user.)

### Step 5: Report Result
- Report: "Merge succeeded (rebase method). Local `--delete-branch` failed due to worktree conflict (`fatal: 'main' is already used by worktree`), but remote branch still existed. Completed deletion via API fallback. Branch feat/some-feature is now deleted."

---

## If headRefName Validation Failed

If headRefName contained unsafe characters (e.g., `feat/some-feature;&rm -rf /`, backticks, pipes, `$`), the validation in Step 3 would fail:

**Action:** Stop immediately. Do not attempt the API call.

**Report:** "Cannot delete remote branch: headRefName `feat/some-feature` contains unsafe characters that could reach a shell context. Manual deletion required via GitHub UI or by a human reviewing the ref name directly."

---

## Summary

When `merge_auto_delete_branch` is `true` and `gh pr merge --delete-branch` fails with a non-zero exit but the state is already `MERGED`:

1. **Re-check remote branch existence** — do not assume deletion succeeded just because the merge did
2. **Validate the ref name** — only characters matching `^[A-Za-z0-9._/-]+$` are safe
3. **Use API fallback if needed** — if the branch still exists remotely, complete the deletion via `gh api -X DELETE`
4. **Report both the merge success and the deletion method used** — clearly distinguish between "branch already deleted" and "API fallback completed deletion"
