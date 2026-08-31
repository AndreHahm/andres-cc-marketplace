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

# Leftover git-rebase-sync pre-rebase safety tags (local-only, never pushed --
# see that skill's own Step 3: `git tag -a {branch}-rebase-backup-{timestamp}
# -m "pre-rebase backup" HEAD`). Nothing ever deletes these afterward, so they
# accumulate indefinitely. Only a tag matching the exact naming convention --
# a branch name, then "-rebase-backup-", then the literal
# `date +%Y%m%d-%H%M%S` shape (8-digit date, 6-digit time) -- is treated as
# one of these, so an unrelated tag that merely contains that substring isn't
# swept in by accident. For each match, report the derived branch name and
# its current status so the skill's own Phase 3.6 can decide whether the tag
# is safe to delete -- this script only gathers facts, it never categorizes.
echo "=== Rebase-backup tags ==="
for tag in $(git tag -l '*-rebase-backup-*'); do
  if [[ "$tag" =~ ^(.+)-rebase-backup-[0-9]{8}-[0-9]{6}$ ]]; then
    branch="${BASH_REMATCH[1]}"
    echo "--- $tag (branch: $branch) ---"
    branch_gone=false
    branch_merged=false
    if git show-ref --verify --quiet "refs/heads/$branch"; then
      if git branch --merged "$default_branch" --format='%(refname:short)' \
        | grep -qxF "$branch"; then
        echo "branch status: exists, merged into $default_branch"
        branch_merged=true
      else
        echo "branch status: exists, not merged into $default_branch"
      fi
    else
      echo "branch status: no longer exists locally"
      branch_gone=true
    fi
    # Reachability is checked whenever the branch is gone OR merged -- never
    # skipped for the merged case. Rebasing rewrites commit SHAs, so a merged
    # POST-rebase branch tip being an ancestor of $default_branch says nothing
    # about whether the tag's own PRE-rebase commit is: live-verified, a
    # rebase-then-merge sequence leaves `git branch --merged` reporting the
    # branch as merged while `git merge-base --is-ancestor <pre-rebase-sha>
    # $default_branch` still fails, since the tag's commit and the merged
    # commit are different objects with different parent chains. Skipped only
    # when the branch still exists and is NOT merged -- that's the one case
    # already left alone regardless of reachability, so the extra git call
    # would be wasted.
    if $branch_gone || $branch_merged; then
      if git merge-base --is-ancestor "$tag" "$default_branch" 2>/dev/null; then
        echo "reachable from $default_branch: yes"
      else
        echo "reachable from $default_branch: NO -- this tag may be the only remaining copy of its commits"
      fi
    fi
  fi
done
