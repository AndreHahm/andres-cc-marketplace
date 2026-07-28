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
done
