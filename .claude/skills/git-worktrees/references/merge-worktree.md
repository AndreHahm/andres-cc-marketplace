# How to Merge Worktree

Workflow to help users merge changes from git worktrees into their current branch, supporting multiple merge strategies from simple file checkout to selective cherry-picking.

## Instructions

CRITICAL: Perform the following steps exactly as described:

1. **Current state check**: Run `git worktree list` to show all existing worktrees and `git status` to verify working directory state

2. **Parse the request**: Determine what merge operation the user wants:
   - **No specifics / "guide me"**: Guided interactive mode
   - **File/directory path**: Merge specific file(s) or directory from a worktree
   - **A single, already-known commit SHA**: Cherry-pick that specific commit (Strategy C below)
   - **A feature name, a PR number, or a SHA range** (e.g. "cherry-pick the feature XY", "...shipped
     with PR #N", "commit-SHAs abcdefg..hijklmn"): first resolve the actual commit list via
     `cherry-pick-resolution.md` — never assume a single commit or a
     hand-typed list is already correct — then apply Strategy C to each resolved commit
   - **Branch name**: Merge from that branch's worktree
   - **A named source worktree**: Use that worktree as the merge source
   - **"select changes"/"patch"**: Use interactive patch selection mode

3. **Determine source worktree/branch**:
   a. If user named a source worktree: Use that worktree path directly
   b. If user named a branch: Find worktree for that branch from `git worktree list`
   c. If only one other worktree exists: Ask to confirm using it as source
   d. If multiple worktrees exist: Present list and ask user which to merge from
   e. If no other worktrees exist: Explain and offer to use branch-based merge instead

4. **Determine merge strategy**: Present options based on user's needs:

   **Strategy A: Selective File Checkout** (for specific files/directories)
   - Best for: Getting complete file(s) from another branch
   - Command: `git checkout <branch> -- <path>`

   **Strategy B: Interactive Patch Selection** (for partial file changes)
   - Best for: Selecting specific hunks/lines from a file
   - Command: `git checkout -p <branch> -- <path>`
   - Prompts user for each hunk: y (apply), n (skip), s (split), e (edit)

   **Strategy C: Cherry-Pick with Selective Staging** (for specific commits)
   - Best for: Applying a commit but excluding some changes
   - Assumes the commit(s) to apply are already resolved and verified — for a feature/PR/SHA-range
     request, run `cherry-pick-resolution.md` first
   - Commands: `git cherry-pick --no-commit <commit>` → review staged changes → `git reset HEAD -- <unwanted>` and `git checkout -- <unwanted>` to drop what you don't want → hand off to the `commit` skill (raw `git commit` is guarded)

   **Strategy D: Manual Merge with Conflicts** (for complex merges)
   - Best for: Full branch merge with control over resolution
   - Commands: `git merge --no-commit <branch>` → review and selectively stage/unstage → resolve conflicts if any → hand off to the `commit` skill (raw `git commit` is guarded)

   **Strategy E: Multi-Worktree Selective Merge** (combining from multiple sources)
   - Best for: Taking different files from different worktrees
   - Commands: `git checkout <branch1> -- <path1>`, `git checkout <branch2> -- <path2>`, then hand off to the `commit` skill for the combined result (raw `git commit` is guarded)

   **Strategy F: git restore** (Git 2.23+, alternative to `git checkout` for file restoration)
   - Best for: Restoring specific files from another branch without touching the branch pointer, using the newer `git restore` command
   - Commands: `git restore --source=<branch> -- <path>` for a complete file, or `git restore -p --source=<branch> -- <path>` for interactive hunk selection

5. **Execute the selected strategy**:
   - If the user wants to review changes first, use the comparison techniques from `SKILL.md`'s own worktree-comparison guidance before merging
   - Execute git commands for the chosen strategy
   - Handle any conflicts that arise
   - Once the working tree/staging area has what the user wants, hand off to the `commit` skill for the final commit — raw `git commit` is guarded and isn't this workflow's job

6. **Post-merge summary**: Display what was merged:
   - Files changed/added/removed
   - Source worktree/branch
   - Merge strategy used

7. **Cleanup prompt**: After successful merge, ask:
   - "Would you like to remove any worktrees to clean up local state?"
   - If yes: List worktrees and ask which to remove
   - Execute `git worktree remove <path>` for selected worktrees
   - Remind about `git worktree prune` if needed

## Merge Strategies Reference

| Strategy | Use When | Command Pattern |
|----------|----------|-----------------|
| **Selective File** | Need complete file(s) from another branch | `git checkout <branch> -- <path>` |
| **Interactive Patch** | Need specific changes within a file | `git checkout -p <branch> -- <path>` |
| **Cherry-Pick Selective** | Need a commit but not all its changes | `git cherry-pick --no-commit` + selective staging |
| **Manual Merge** | Full branch merge with control | `git merge --no-commit` + selective staging |
| **Multi-Source** | Combining files from multiple branches | Multiple `git checkout <branch> -- <path>` |
| **git restore** | Same as Selective File/Interactive Patch, via the newer command (Git 2.23+) | `git restore --source=<branch> -- <path>` |

## Examples

**Merge single file from worktree** — user names a file and source worktree: prompt for merge strategy, then run `git checkout <branch> -- <file>`.

**Interactive patch selection** — user asks to select specific changes from a file: list available worktrees, then run `git checkout -p <branch> -- <file>`, letting the user select hunks interactively (y/n/s/e).

**Cherry-pick specific commit** — user names a commit hash: ask whether to apply the entire commit or selectively; if selective, `git cherry-pick --no-commit <commit>` then guide through unstaging unwanted changes.

**Full guided mode** — user gives no specifics: list all worktrees, ask what to merge (files, commits, or branches), guide through the appropriate strategy, offer cleanup at the end.

**Directory merge with conflicts** — user names a directory and source worktree: use Strategy D (`git merge --no-commit <branch>`), help resolve any conflicts, review and commit the selected changes.

## Interactive Patch Mode Guide

When using Strategy B, the user sees prompts for each change hunk:

```
@@ -10,6 +10,8 @@ function processData(input) {
   const result = transform(input);
+  // Added validation
+  if (!isValid(result)) throw new Error('Invalid');
   return result;
 }
Apply this hunk? [y,n,q,a,d,s,e,?]
```

| Key | Action |
|-----|--------|
| `y` | Apply this hunk |
| `n` | Skip this hunk |
| `q` | Quit (don't apply this or remaining hunks) |
| `a` | Apply this and all remaining hunks |
| `d` | Don't apply this or remaining hunks in this file |
| `s` | Split into smaller hunks |
| `e` | Manually edit the hunk |
| `?` | Show help |

## Common Workflows

### Take a Feature File Without Full Merge

Get just one file from a feature worktree (Strategy A), not the entire branch.

### Partial Bugfix from Hotfix Branch

Use interactive patch selection (Strategy B) against a hotfix worktree to take only the specific bug-fix hunks, not all its changes.

### Combine Multiple PRs' Changes

Guided mode: select specific files from one PR's worktree, other files from another's, combine into a single coherent commit.

## Important Notes

- **Working directory state**: Always ensure the working directory is clean before merging. Uncommitted changes can cause conflicts.

- **Pre-merge review**: Consider reviewing changes before merging to understand what will be applied — see `SKILL.md`'s worktree-comparison guidance.

- **Conflict resolution**: If conflicts occur during merge, help identify and resolve them before committing.

- **No-commit flag**: Most strategies use `--no-commit` to give the user control over the final commit message and what gets included.

- **Shared repository**: All worktrees share the same Git object database, so commits made in any worktree are immediately visible to cherry-pick from any other.

- **Branch locks**: Branches can only be checked out in one worktree at a time. Use branch names for merge operations rather than creating duplicate worktrees.

## Cleanup After Merge

After merging, consider cleaning up worktrees that are no longer needed:

```bash
# List worktrees
git worktree list

# Remove specific worktree (clean state required)
git worktree remove ../project-feature

# Clean up stale worktree references
git worktree prune
```

For a worktree with uncommitted changes still in it, that's a forced removal — tell the user to run
`/git-cleanup` themselves (it has `disable-model-invocation: true`, so it can't be invoked here even
indirectly), which gates `--force`/`-f` behind explicit user confirmation; the raw form is guarded and
isn't this workflow's job.

Ask about cleanup after each successful merge to help maintain a tidy workspace.

## Troubleshooting

**"Cannot merge: working directory has uncommitted changes"**
- Commit or stash current changes first
- Or use `git stash` before merge, `git stash pop` after

**"Merge conflict in <file>"**
- Show the conflicted files
- Open files and resolve conflicts (look for `<<<<<<<` markers)
- Stage resolved files with `git add <file>`
- Hand off to the `commit` skill to finish (raw `git commit` is guarded)

**"Commit not found" when cherry-picking**
- Ensure the commit hash is correct
- Run `git log <branch>` in any worktree to find commits
- Commits are shared across all worktrees

**"Cannot checkout: file exists in working tree"**
- File has local modifications
- Either commit, stash, or discard local changes first
- Then retry the merge operation

**"Branch not found for worktree"**
- The specified worktree may have been removed
- Run `git worktree list` to see current worktrees
- Use `git worktree prune` to clean up stale references
