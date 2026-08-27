# How to Compare Worktrees

Workflow to compare files and directories between git worktrees, helping users understand differences in code across branches or worktrees.

## Instructions

CRITICAL: Perform the following steps exactly as described:

1. **Current state check**: Run `git worktree list` to show all existing worktrees and their locations

2. **Parse the request**: Classify what the user gave:
   - **Nothing specific**: Interactive mode - ask user what to compare
   - **"summary"/"stats"**: Show summary statistics of differences (files changed, insertions, deletions)
   - **Worktree path**: A path that matches one of the worktree roots from `git worktree list`
   - **Branch name**: A name that matches a branch in one of the worktrees
   - **File/directory path**: A path within the current worktree to compare

3. **Determine comparison targets** (worktrees to compare):
   a. If user gave worktree paths: Use those as comparison targets
   b. If user gave branch names: Find the worktrees for those branches from `git worktree list`
   c. If only one worktree exists besides current: Use current and that one as comparison targets
   d. If multiple worktrees exist and none specified: Present the list from step 1 and ask user which to compare
   e. If no other worktrees exist: Offer to compare with a branch using `git diff`

4. **Determine what to compare** (files/directories within worktrees):
   a. If user specified file(s) or directory(ies) paths: Compare ALL of them
   b. If no specific paths given: Ask user:
      - "Compare entire worktree?" or
      - "Compare specific files/directories? (enter paths)"

5. **Execute comparison**:

   **For specific files between worktrees:**

   ```bash
   diff <worktree1>/<path> <worktree2>/<path>
   # Or for unified diff format:
   diff -u <worktree1>/<path> <worktree2>/<path>
   ```

   A visual diff tool (e.g. `code --diff <worktree1>/<path> <worktree2>/<path>`) is a reasonable
   suggestion to make to the user, but isn't something this skill's own `allowed-tools` grants or runs
   directly — its scope is the read-only `diff`/`git diff` comparison above, not launching an editor.

   **For directories between worktrees:**

   ```bash
   diff -r <worktree1>/<directory> <worktree2>/<directory>
   # Or for summary only:
   diff -rq <worktree1>/<directory> <worktree2>/<directory>
   ```

   **For branch-level comparison (using git diff):**

   ```bash
   git diff <branch1>..<branch2> -- <path>
   # Or for stat summary:
   git diff --stat <branch1>..<branch2>
   ```

   **For comparing with current working directory:**

   ```bash
   diff <current-file> <other-worktree>/<file>
   ```

6. **Format and present results**:
   - Show clear header indicating what's being compared
   - For large diffs, offer to show summary first
   - Highlight significant changes (new files, deleted files, renamed files)
   - Provide context about the branches each worktree contains

## Comparison Modes

| Mode | Description | Command Pattern |
|------|-------------|-----------------|
| **File diff** | Compare single file between worktrees | `diff -u <wt1>/file <wt2>/file` |
| **Directory diff** | Compare directories recursively | `diff -r <wt1>/dir <wt2>/dir` |
| **Summary only** | Show which files differ (no content) | `diff -rq <wt1>/ <wt2>/` |
| **Git diff** | Use git's diff (branch-based) | `git diff branch1..branch2 -- path` |
| **Stat view** | Show change statistics | `git diff --stat branch1..branch2` |

## Worktree Detection

Worktrees are found using `git worktree list` — see `SKILL.md`'s "List Worktrees" section for example output and how to read it (path, commit, branch).

## Examples

**Compare specific file between worktrees** — user asks to compare `src/app.js`: prompt to select which worktree to compare with, then show the diff of `src/app.js` between current and selected worktree.

**Compare between two specific worktrees** — user names both worktrees and a file: compare that file between the two specified worktrees directly.

**Compare multiple files/directories** — user lists several paths: show diffs for all of them between worktrees, not just the first.

**Compare entire directories** — user names a directory: show all differences in it between worktrees.

**Get summary statistics** — user asks for a stat summary: show which files differ and line counts, not full diff content.

**Interactive mode** — user gives no specifics: list available worktrees, ask which to compare, then ask for specific paths or the entire worktree.

**Compare with branch worktree by branch name** — user names a branch: find the worktree for that branch and compare against it.

**Compare specific paths between branch worktrees** — user names two branches and paths: compare those paths between the two branches' worktrees.

## Output Format

**File Comparison Header:**

```
Comparing: src/app.js
  From: /home/user/project (main)
  To:   /home/user/project-feature (feature-x)
---
[diff output]
```

**Summary Output:**

```
Worktree Comparison Summary
===========================
From: /home/user/project (main)
To:   /home/user/project-feature (feature-x)

Files only in main:      - src/deprecated.js
Files only in feature-x: + src/new-feature.js, src/new-feature.test.js
Files that differ:       ~ src/app.js, src/utils/helpers.js, package.json

Statistics: 3 files changed, 2 files added, 1 file removed
```

## Common Workflows

### Review Feature Changes

Show a stat summary first, then diff the specific directory the user cares about (e.g. `src/components/`).

### Compare Implementations

Compare how two features implemented similar functionality by diffing the same path (e.g. `src/auth/`) across both feature worktrees.

### Quick File Check

Diff a single file (e.g. `package.json`) between worktrees to confirm whether it differs at all.

### Pre-Merge Review

Show a stat summary, then diff both `src/` and `tests/` before merging, so the reviewer sees the full change surface.

## Important Notes

- **Argument detection**: Auto-detect what the user gave by comparing it against `git worktree list` output:
  - Paths matching worktree roots → treated as worktrees to compare
  - Names matching branches in worktrees → treated as worktrees to compare
  - Other paths → treated as files/directories to compare within worktrees

- **Multiple paths**: When multiple file/directory paths are given, compare ALL of them between the selected worktrees (not just the first one).

- **Worktree paths**: When specifying worktrees, use the full path or relative path from current directory (e.g., `../project-feature`)

- **Branch vs Worktree**: If the user names a branch, look for a worktree with that branch checked out. If no worktree exists for that branch, suggest `git diff` instead.

- **Large diffs**: For large directories, offer to show a summary first before displaying full diff output.

- **Binary files**: Binary files are detected and reported as "Binary files differ" without showing actual diff.

- **File permissions**: The diff will also show changes in file permissions if they differ.

- **No worktrees**: If no other worktrees exist, explain that one can be created (see `SKILL.md`'s
  "Related Workflows" section) and offer to use `git diff` for branch comparison instead.

## Troubleshooting

**"No other worktrees found"**

- Create a worktree first (`git worktree add <path> <branch>` — SKILL.md's Related Workflows section links to the dedicated creation workflow)
- Or use `git diff` for branch-only comparison without worktrees

**"Worktree for branch not found"**

- The branch may not have a worktree created
- Run `git worktree list` to see available worktrees
- Create one for it (`git worktree add <path> <branch>`)

**"Path does not exist in worktree"**

- The specified file/directory may not exist in one of the worktrees
- This could indicate the file was added/deleted in one branch
- Report this in the comparison output
