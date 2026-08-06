# Comparing and Merging Changes Between Worktrees

Since all worktrees share the same Git repository, you can compare files, cherry-pick commits, and selectively merge changes between them.

## Compare and Review File Changes

Since worktrees are just directories, you can compare files directly:

```bash
# Compare specific file between worktrees
diff ../project-main/src/app.js ../project-feature/src/app.js

# Use git diff to compare branches (works from any worktree)
git diff main..feature-branch -- src/app.js

# Visual diff with your preferred tool
code --diff ../project-main/src/app.js ../project-feature/src/app.js

# Compare entire directories
diff -r ../project-v1/src ../project-v2/src
```

## Merge Only One File from a Worktree

You can selectively bring a single file from another branch using `git checkout`:

```bash
# In your current branch, get a specific file from another branch
git checkout feature-branch -- path/to/file.js

# Or get it from a specific commit
git checkout abc1234 -- path/to/file.js

# Get multiple specific files
git checkout feature-branch -- src/module.js src/utils.js
```

For **partial file changes** (specific hunks/lines only):

```bash
# Interactive patch mode - select which changes to take
git checkout -p feature-branch -- path/to/file.js
```

This prompts you to accept/reject each change hunk individually with options:
- `y` - apply this hunk
- `n` - skip this hunk
- `s` - split into smaller hunks
- `e` - manually edit the hunk

## Cherry-Pick Commits from Worktrees

Cherry-picking works at the commit level. Since all worktrees share the same repository, you can cherry-pick any commit:

```bash
# Find the commit hash (from any worktree or git log)
git log feature-branch --oneline

# Cherry-pick specific commit into your current branch
git cherry-pick abc1234

# Cherry-pick multiple commits
git cherry-pick abc1234 def5678

# Cherry-pick a range of commits
git cherry-pick abc1234^..def5678

# Cherry-pick without committing (stage changes only)
git cherry-pick --no-commit abc1234
```

## Merge Changes from Multiple Worktrees

You can merge or cherry-pick from multiple branches:

```bash
# Merge multiple branches sequentially
git merge feature-1
git merge feature-2

# Or use octopus merge for multiple branches at once
git merge feature-1 feature-2 feature-3

# Cherry-pick commits from multiple branches
git cherry-pick abc1234  # from feature-1
git cherry-pick def5678  # from feature-2
```

## Selective Merging - Pick Which Changes to Include

### Option 1: Selective File Checkout

```bash
# Get specific files from different branches
git checkout feature-1 -- src/moduleA.js
git checkout feature-2 -- src/moduleB.js
git commit -m "Merge selected files from feature branches"
```

### Option 2: Interactive Patch Selection

```bash
# Select specific hunks from a file
git checkout -p feature-1 -- src/shared.js
```

### Option 3: Cherry-Pick with Selective Staging

```bash
# Apply changes without committing
git cherry-pick --no-commit abc1234

# Unstage what you don't want
git reset HEAD -- unwanted-file.js
git checkout -- unwanted-file.js

# Commit only what you kept
git commit -m "Selected changes from feature-1"
```

### Option 4: Merge with Manual Selection

```bash
# Start merge but don't auto-commit
git merge --no-commit feature-1

# Review and modify staged changes
git status
git reset HEAD -- file-to-exclude.js
git checkout -- file-to-exclude.js

# Commit your selection
git commit -m "Merge selected changes from feature-1"
```

### Option 5: Using git restore (Git 2.23+)

```bash
# Restore specific file from another branch
git restore --source=feature-branch -- path/to/file.js

# Interactive restore with patch selection
git restore -p --source=feature-branch -- path/to/file.js
```
