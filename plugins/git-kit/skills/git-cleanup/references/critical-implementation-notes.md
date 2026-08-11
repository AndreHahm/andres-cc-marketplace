# Critical Implementation Notes

### Squash-Merged Branches Require Force Delete

**IMPORTANT:** `git branch -d` will ALWAYS fail for squash-merged branches because git cannot detect that the work was incorporated. This is expected behavior, not an error.

When you identify a branch as squash-merged:
- Plan to use `git branch -D` (force delete) from the start
- Do NOT try `git branch -d` first and then ask again for `-D` - this wastes user confirmations
- In the confirmation step, show `git branch -D` for squash-merged branches

### Group Related Branches BEFORE Categorization

**MANDATORY:** Before categorizing individual branches, group them by name prefix:

```bash
# Extract common prefixes from branch names
# e.g., feat/auth-*, feat/api-*, fix/login-*
```

Branches sharing a prefix (e.g., `feat/api`, `feat/api-v2`, `feat/api-refactor`) are almost certainly related iterations. Analyze them as a group:

1. Find the oldest and newest by commit date
2. Check if newer branches contain commits from older ones
3. Check which PRs merged work from each
4. Determine if older branches are superseded

Present related branches together with a clear recommendation, not scattered across categories.

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
