# merge-pr Conflict Reproduction Guidance

## Answer: No, use the GitHub synthetic ref, not `git fetch origin contributor-branch`

When `isCrossRepository` is `true` (this PR comes from a fork), the `headRefName` (`contributor-branch`) is **not** a branch on the local repository's `origin` remote. Attempting to fetch it directly would fail.

## Correct Instructions to Tell the User

Since this is a fork PR (cross-repository), tell the user to reproduce the conflict locally by:

1. **Fetch the PR's synthetic GitHub ref** (not the branch name directly):
   ```bash
   git fetch origin pull/88/head:pr-88
   ```
   - `origin pull/88/head` is GitHub's synthetic ref for PR #88
   - `pr-88` is a convenient local branch name to receive it
   - This matches git-worktrees' documented convention for fork PR commits

2. **Check out the fetched PR branch**:
   ```bash
   git checkout pr-88
   ```

3. **Attempt the merge to see the actual conflicts**:
   ```bash
   git merge origin/main
   ```
   - At this point, `git status` will show unmerged paths
   - The user can then run `resolving-merge-conflicts` skill to resolve them

## Why Not `git fetch origin contributor-branch`?

The contributor's `contributor-branch` exists on **their fork's repository**, not on `origin` (this repository). Attempting `git fetch origin contributor-branch` would fail with an error like "couldn't find remote-tracking branch 'contributor-branch'" because that branch doesn't exist on this repo's origin remote.

The GitHub synthetic ref `pull/88/head` is the correct way to fetch a fork PR's commits into a local working tree.
