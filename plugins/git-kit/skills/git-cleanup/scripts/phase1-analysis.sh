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
# Enumerate refs/remotes/origin directly (not `git branch -r`, which lists
# every configured remote) -- a repo with a second remote (e.g. `upstream`)
# would otherwise leak that remote's branches in as false candidates here.
# %(refname:strip=3) strips "refs/remotes/origin/" to the bare branch name in
# one step, so origin/HEAD's symbolic-ref pointer (which has no such prefix
# once already scoped to this one remote) still needs its own exclusion, but
# nothing from another remote can appear at all.
comm -23 \
  <(git for-each-ref --format='%(refname:strip=3)' refs/remotes/origin \
    | grep -vE "^HEAD$|$protected" | sort -u) \
  <(git branch --format='%(refname:short)' | sort -u)
