---
name: git-worktrees
description: >-
  Use when working on multiple branches simultaneously, context switching without stashing, reviewing PRs while developing, testing in isolation, or comparing implementations across branches - provides git worktree commands and workflow patterns for parallel development with multiple working directories. For creating the first worktree/branch to begin a new piece of work (main-sync, branch-naming validation, worktree-vs-branch choice), see `starting-work` instead — this skill is reference material for ongoing multi-worktree management, not the entry point for starting new work.
allowed-tools: Bash(git worktree:*), Bash(git status:*), Bash(git diff:*), Bash(git checkout:*), Bash(git cherry-pick:*), Bash(git merge:*), Bash(git reset:*), Bash(git log:*), Bash(git fetch:*), Bash(git restore:*), Bash(git stash:*), Bash(git branch:*), Bash(git add:*), Bash(diff:*), Bash(npm install:*), Bash(yarn install:*), Bash(pnpm install:*), Bash(bun install:*), AskUserQuestion
---

# Git Worktrees

## Overview

Git worktrees enable checking out multiple branches simultaneously in separate directories, all sharing the same repository. Create a worktree instead of stashing changes or cloning separately.

**Core principle:** One worktree per active branch. Switch contexts by changing directories, not branches.

**Two different defaults, intentionally:** this skill's own examples below use sibling directories
(`../project-feature`) for manual, ad-hoc worktree management — that default still applies here.
`starting-work`'s *automated* flow uses a different default, `.claude/worktrees/<description>` (or
`.codex/worktrees/` for a Codex CLI session), locked to the creating session — see that skill for why.
Neither supersedes the other; they're two different use cases (manual vs. session-lifecycle-managed).

## When NOT to Use

- **Starting a brand-new piece of work** (syncing main, validating a branch name, choosing worktree vs.
  plain branch before the first commit) — that's `starting-work`'s job.
- **Resolving the actual content of a merge/cherry-pick conflict** — `references/merge-worktree.md`'s
  Strategy D covers running `git merge --no-commit`/handling a full branch merge between worktrees, but
  its own conflict-resolution step is just "resolve conflicts if any," with no per-type strategy. Once a
  conflict needs that (imports/tests/config merging, generated-file regeneration, deleted-modified
  backups, or the ambiguity-clarification loop), hand off to `resolving-merge-conflicts` for the actual
  resolution — this skill still owns everything else about the worktree merge (strategy selection,
  staging, cleanup).

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Main worktree** | Original working directory from `git clone` or `git init` |
| **Linked worktree** | Additional directories created with `git worktree add` |
| **Shared `.git`** | All worktrees share same Git object database (no duplication) |
| **Branch lock** | Each branch can only be checked out in ONE worktree at a time |
| **Worktree metadata** | Administrative files in `.git/worktrees/` tracking linked worktrees |

## Quick Reference

**Guarded actions, not this skill's job:** git-kit's guard hooks block raw `git worktree add -b`/`-B`
(new-branch creation — that's `starting-work`'s job), raw `git worktree remove --force`/`-f` (discarding
uncommitted work — that's `git-cleanup`'s job), and raw `git commit` (always `commit`'s job) unless run by
one of those allowlisted skills. This skill's own commands below are the ones that stay ungated: worktrees
for an *existing* branch, and a plain (non-force) `git worktree remove`, which git itself already refuses
on a dirty or locked worktree.

| Task | Command |
|------|---------|
| Create worktree (existing branch) | `git worktree add <path> <branch>` |
| Create worktree (new branch) | Not this skill's job — see `starting-work` |
| Create detached worktree | `git worktree add --detach <path> <commit>` |
| List all worktrees | `git worktree list` |
| Remove worktree (clean state) | `git worktree remove <path>` |
| Force remove worktree (discards uncommitted changes) | Not this skill's job — see `git-cleanup` |
| Move worktree | `git worktree move <old> <new>` |
| Lock worktree | `git worktree lock <path>` |
| Unlock worktree | `git worktree unlock <path>` |
| Prune stale worktrees | `git worktree prune` |
| Repair worktree links | `git worktree repair` |
| Compare files between worktrees | `diff ../worktree-a/file ../worktree-b/file` |
| Get one file from another branch | `git checkout <branch> -- <path>` |
| Get partial file changes | `git checkout -p <branch> -- <path>` |
| Cherry-pick a commit | `git cherry-pick <commit>` |
| Cherry-pick without committing | `git cherry-pick --no-commit <commit>` |
| Merge without auto-commit | `git merge --no-commit <branch>` |

## Essential Commands

### Create a Worktree

```bash
# Create worktree with existing branch
git worktree add ../feature-x feature-x

# Create worktree with detached HEAD (for experiments)
git worktree add --detach ../experiment HEAD~5
```

**Need a worktree for a branch that doesn't exist yet** (new feature, hotfix, tracking a remote branch
for the first time)? That's `starting-work`'s job — it also syncs `main`, validates the branch name, and
asks worktree-vs-plain-branch. git-kit's `guard-raw-branch-create.sh` hook hard-blocks a raw
`git worktree add -b`/`-B` from any skill not on its allowlist, this skill included.

### List Worktrees

```bash
# Simple list
git worktree list

# Verbose output with additional details
git worktree list -v

# Machine-readable format (for scripting)
git worktree list --porcelain
```

**Example output:**

```
/home/user/project           abc1234 [main]
/home/user/project-feature   def5678 [feature-x]
/home/user/project-hotfix    ghi9012 [hotfix-123]
```

### Remove a Worktree

```bash
# Remove worktree (working directory must be clean -- git itself refuses otherwise)
git worktree remove ../feature-x
```

**Need to discard uncommitted changes to force a removal?** Not this skill's job — `git-cleanup` has
`disable-model-invocation: true`, so it can't be invoked here even indirectly; tell the user to run
`/git-cleanup` themselves. It gates `git worktree remove --force`/`-f` behind explicit user confirmation
before running it. git-kit's `guard-raw-destructive-cleanup.sh` hook hard-blocks the raw forced form from
any skill not on its allowlist, this skill included.

### Move a Worktree

```bash
# Relocate worktree to new path
git worktree move ../old-path ../new-path
```

### Lock/Unlock Worktrees

```bash
# Lock worktree (prevents pruning if on removable storage)
git worktree lock ../feature-x
git worktree lock --reason "On USB drive" ../feature-x

# Unlock worktree
git worktree unlock ../feature-x
```

### Prune Stale Worktrees

```bash
# Remove stale worktree metadata (after manual directory deletion)
git worktree prune

# Dry-run to see what would be pruned
git worktree prune --dry-run

# Verbose output
git worktree prune -v
```

### Repair Worktrees

```bash
# Repair worktree links after moving directories manually
git worktree repair

# Repair specific worktree
git worktree repair ../feature-x
```

## Workflow Patterns

### Pattern 1: Feature + Hotfix in Parallel

To fix a bug while feature work is in progress:

1. Use `starting-work` to create the hotfix worktree (new branch from `main`, e.g. `hotfix-456`) — this
   is new work, not this skill's job.
2. `cd` into the hotfix worktree, make the fix.
3. Use the `commit` skill to commit — raw `git commit` is guarded.
4. `git push origin hotfix-456`, then return to the feature worktree (`cd ../project`).
5. Clean up the hotfix worktree when done: `git worktree remove ../project-hotfix` (plain removal, no
   force needed once the fix is committed and pushed).

### Pattern 2: PR Review While Working

To review a PR without affecting current work:

```bash
# Fetch PR branch and create worktree
git fetch origin pull/123/head:pr-123
git worktree add ../project-review pr-123

# Review: run tests, inspect code
cd ../project-review

# Return to work, then clean up
cd ../project
git worktree remove ../project-review
git branch -d pr-123
```

### Pattern 3: Compare Implementations

To compare code across branches side-by-side:

```bash
# Create worktrees for different versions
git worktree add ../project-v1 v1.0.0
git worktree add ../project-v2 v2.0.0

# Diff, compare, or run both simultaneously
diff ../project-v1/src/module.js ../project-v2/src/module.js

# Clean up
git worktree remove ../project-v1
git worktree remove ../project-v2
```

### Pattern 4: Long-Running Tasks

To run tests/builds in isolation while continuing development:

```bash
# Create worktree for CI-like testing
git worktree add ../project-test main

# Start long-running tests in background
cd ../project-test && npm test &

# Continue development in main worktree
cd ../project
```

### Pattern 5: Stable Reference

To maintain a clean main checkout for reference:

```bash
# Create permanent worktree for main branch
git worktree add ../project-main main

# Lock to prevent accidental removal
git worktree lock --reason "Reference checkout" ../project-main
```

### Pattern 6: Selective Merging from Multiple Features

To combine specific changes from multiple feature branches:

```bash
# Create worktrees for each feature to review, then diff against main
git worktree add ../project-feature-1 feature-1
git worktree add ../project-feature-2 feature-2
diff ../project/src/module.js ../project-feature-1/src/module.js
diff ../project/src/module.js ../project-feature-2/src/module.js
```

```bash
# From main worktree, selectively take changes (or cherry-pick specific commits instead)
cd ../project
git checkout feature-1 -- src/moduleA.js src/utils.js
git checkout feature-2 -- src/moduleB.js
git cherry-pick abc1234  # from feature-1, if cherry-picking instead
# Then use the `commit` skill to commit the combined result -- raw `git commit` is guarded.

# Clean up
git worktree remove ../project-feature-1
git worktree remove ../project-feature-2
```

## Comparing and Merging Changes Between Worktrees

See `references/compare-worktrees.md` for file-level comparison and `references/merge-worktree.md` for single-file merge, cherry-picking, and selective multi-worktree merge techniques.

## Directory Structure Conventions

Organize worktrees predictably:

```
~/projects/
  myproject/              # Main worktree (main/master branch)
  myproject-feature-x/    # Feature branch worktree
  myproject-hotfix/       # Hotfix worktree
  myproject-review/       # Temporary PR review worktree
```

**Naming convention:** `<project>-<purpose>` or `<project>-<branch>`

## Best Practices

| Practice | Rationale |
|----------|-----------|
| **Use sibling directories** | Keep worktrees at same level as main project for easy navigation |
| **Name by purpose** | `project-review` is clearer than `project-pr-123` |
| **Clean up promptly** | Remove worktrees when done to avoid confusion |
| **Lock remote worktrees** | Prevent pruning if worktree is on network/USB storage |
| **Use `--detach` for experiments** | Avoid creating throwaway branches |
| **Commit before removing** | Always commit or stash before `git worktree remove` |

## Common Issues and Solutions

### Issue: "Branch is already checked out"

**Cause:** Attempting to checkout a branch that's active in another worktree.

**Solution:**

```bash
# Find where the branch is checked out
git worktree list

# Either work in that worktree or remove it first
git worktree remove ../other-worktree
```

### Issue: Stale worktree after manual deletion

**Cause:** Deleted worktree directory without using `git worktree remove`.

**Solution:**

```bash
# Clean up stale metadata
git worktree prune
```

### Issue: Worktree moved manually

**Cause:** Moved worktree directory without using `git worktree move`.

**Solution:**

```bash
# Repair the worktree links
git worktree repair
# Or specify the new path
git worktree repair /new/path/to/worktree
```

### Issue: Worktree on removed drive

**Cause:** Worktree was on removable storage that's no longer connected.

**Solution:**

```bash
# If temporary, lock it to prevent pruning
git worktree lock ../usb-worktree

# If permanent, prune it
git worktree prune
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `rm -rf` to delete worktree | Always use `git worktree remove`, then `git worktree prune` if needed |
| Forgetting branch is locked to worktree | Run `git worktree list` before checkout errors |
| Not cleaning up temporary worktrees | Remove worktrees immediately after task completion |
| Creating worktrees in nested locations | Use sibling directories (`../project-feature`) not subdirs |
| Moving worktree directory manually | Use `git worktree move` or run `git worktree repair` after |

## Agent Workflow Integration

To isolate parallel agent tasks: use `starting-work` to create the isolated task's worktree (new branch,
e.g. `task-123`) — new-branch worktree creation is guarded and isn't this skill's job. `cd` into it, make
changes, run tests, `cd ../project` to return.

To experiment safely with detached HEAD:

```bash
# Create detached worktree (no branch to clean up)
git worktree add --detach ../project-experiment
cd ../project-experiment
# Experiment, then discard or commit to a new branch (via starting-work + commit)
```

If the experiment is discarded and the worktree is clean, `git worktree remove ../project-experiment`
(plain removal) is enough. If it needs to be discarded with uncommitted changes still present, that's a
forced removal — tell the user to run `/git-cleanup` themselves (it has `disable-model-invocation: true`,
so it can't be invoked here even indirectly), which gates `--force` behind explicit confirmation; the raw
form is guarded and isn't this skill's job.

## Verification Checklist

Before using worktrees:

- [ ] Understand that branches can only be checked out in one worktree
- [ ] Know where worktrees will be created (use sibling directories)
- [ ] Plan cleanup strategy for temporary worktrees

When creating worktrees:

- [ ] Use descriptive directory names
- [ ] Verify branch is not already checked out elsewhere
- [ ] Consider using `--detach` for experiments

When removing worktrees:

- [ ] Commit or stash any uncommitted changes
- [ ] Use `git worktree remove`, not `rm -rf`
- [ ] Run `git worktree prune` if directory was deleted manually

## Testing & Validation

**Verify this skill activates on:**
- "compare files between my worktrees"
- "merge changes from the feature worktree into main"
- "set up a worktree so I can review this PR without stashing"
- "cherry-pick this commit from another worktree"

**Verify it does NOT activate on:**
- "start a new branch for the auth refactor" → `starting-work`
- "sync my current branch with main" → `/sync-branch`
- "I just merged, clean this up" → `finishing-work`

**Quality gates:**
- [ ] Creating a worktree never runs the detected install command without an `AskUserQuestion`
      confirmation first (`references/create-worktree.md` step 5e)
- [ ] Merge strategies never execute without the user having chosen one — either through the guided
      flow or an explicit request naming the strategy
- [ ] Cleanup always uses plain `git worktree remove`, never `rm -rf` — a forced removal (discarding
      uncommitted changes) always routes through `git-cleanup`, never a raw `--force`/`-f` from this skill
- [ ] New-branch worktree creation always routes through `starting-work`, never a raw `git worktree add -b`
- [ ] Combining/merging changes into a final commit always routes through the `commit` skill, never a raw
      `git commit` from this skill
- [ ] Comparisons stay read-only — `diff`/`git diff` only, no file writes

## Related Workflows

Detailed step-by-step procedures for specific worktree operations are in `references/`:

- `references/create-worktree.md` — create and set up a worktree, with automatic dependency detection and confirmed (not automatic) installation
- `references/compare-worktrees.md` — compare files/directories between worktrees or branches
- `references/merge-worktree.md` — merge or selectively cherry-pick changes from a worktree into the current branch
