#!/usr/bin/env bash
# Phase 1 comprehensive analysis for git-cleanup.
# Gather ALL information upfront before any categorization.

# Get default branch name
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD \
  2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# Protected branches - never analyze or delete
protected='^(main|master|develop|release/.*)$'

# List all local branches with tracking info
git branch -vv

# List all worktrees
git worktree list

# Fetch and prune to sync remote state
git fetch --prune

# Get merged branches (into default branch)
git branch --merged "$default_branch"

# Get recent PR merge history (squash-merge detection)
git log --oneline "$default_branch" | grep -iE "#[0-9]+" | head -30

# For EACH non-protected branch, get unique commits and sync status
for branch in $(git branch --format='%(refname:short)' \
  | grep -vE "$protected"); do
  echo "=== $branch ==="
  echo "Commits not in $default_branch:"
  git log --oneline "$default_branch".."$branch" 2>/dev/null \
    | head -5
  echo "Commits not pushed to remote:"
  git log --oneline "origin/$branch".."$branch" 2>/dev/null \
    | head -5 || echo "(no remote tracking)"
  echo "Remote counterpart (origin/$branch):"
  git rev-parse --verify --quiet "origin/$branch" >/dev/null \
    && echo "still exists on origin" \
    || echo "gone (or never pushed)"
done

# Remote-only branches with no local counterpart at all -- candidates for the
# gh --delete-branch-during-worktree-merge failure mode (see finishing-work's
# own step 1.5 for the primary fix; this is the fallback safety net for a
# branch whose local copy is already gone, e.g. deleted by a prior git-cleanup
# run, but whose remote copy survived that same merge). Listed here only as
# candidates -- confirming each one's PR is actually merged (not just "no
# local branch") is a live gh check done in the skill's own Phase 3, never
# assumed from this list alone.
echo "=== Remote-only branches (no local counterpart) ==="
# origin/HEAD's %(refname:short) can render as bare "origin" (this git
# version) or "origin/HEAD" (others) -- exclude both forms before stripping
# the "origin/" prefix, or the symbolic-ref pointer itself leaks through as
# a spurious "candidate branch" (it never strips, since it has no "origin/"
# prefix to remove).
comm -23 \
  <(git branch -r --format='%(refname:short)' \
    | grep -vE '^origin$|^origin/HEAD$' \
    | sed 's@^origin/@@' | grep -vE "^HEAD$|$protected" | sort -u) \
  <(git branch --format='%(refname:short)' | sort -u)
