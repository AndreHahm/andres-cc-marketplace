# Critical Implementation Notes

### Squash-Merged Branches Require Force Delete

**IMPORTANT:** `git branch -d` will ALWAYS fail for squash-merged branches because git cannot detect that the work was incorporated. This is expected behavior, not an error.

When you identify a branch as squash-merged:
- Plan to use `git branch -D` (force delete) from the start
- Do NOT try `git branch -d` first and then ask again for `-D` - this wastes user confirmations
- In the confirmation step, show `git branch -D` for squash-merged branches

### Thorough PR History Investigation

Don't rely on simple keyword matching. For `[gone]` branches:

```bash
# 1. Get the branch's commits that aren't in default branch
git log --oneline "$default_branch".."$branch"

# 2. Search default branch for PRs that incorporated this work
# Search by: branch name, commit message keywords, PR numbers
git log --oneline "$default_branch" | grep -iE "(branch-name|keyword|#[0-9]+)"

# 3. For related branch groups, trace which PRs merged which work
git log --oneline "$default_branch" | grep -iE "(#[0-9]+)" | head -20
```
