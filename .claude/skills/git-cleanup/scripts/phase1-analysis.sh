#!/usr/bin/env bash
# Phase 1 comprehensive analysis for git-cleanup.
# Gather ALL information upfront before any categorization.

# Get default branch name. Not `... || echo "main"` -- `sed` exits 0 even on
# empty stdin (no origin/HEAD symref set), so the `||` fallback never fires
# and default_branch silently resolves to an empty string, corrupting every
# later git call that takes it as a revision argument (found by Devin's
# review of PR #262, live-verified against a repo with no origin remote).
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD \
  2>/dev/null | sed 's@^refs/remotes/origin/@@')
default_branch="${default_branch:-main}"

# Disables pathspec glob/wildcard magic for every git call this process makes
# -- matches delete-rebase-backup-tags.sh's own identical fix; see that
# script's comment for the live-verified detail (cross-model-review finding).
export GIT_LITERAL_PATHSPECS=1

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
  git log --oneline "origin/$branch..$branch" 2>/dev/null \
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

# Per-path, per-blob content-reachability check -- mirrors
# delete-rebase-backup-tags.sh's own is_path_blob_reachable/
# check_diff_records/is_tag_content_reachable EXACTLY (same functions, same
# logic, kept in sync deliberately -- this script's report must agree with
# what that script would actually delete, per plugin-rulebook's R20
# duplicate-fact-sweep). See that script's own comments for the full
# rationale, live-verification detail, and security-reviewer findings this
# implementation already incorporates (C1: a parentless/root commit's
# content must be checked via `--root`, not silently skipped; M1: a
# `git diff-tree` failure on a non-merge commit must fail closed, not be
# misread as an empty diff; M2: a non-ASCII/quoted path must be parsed via
# `-z`, not the tab-delimited default, or a deletion check can silently pass
# on a mis-parsed literal string) -- not restated here to avoid a second
# copy of the same rationale drifting out of sync with the code itself.
is_path_blob_reachable() {
  local path="$1" wanted_blob="$2" wanted_mode="$3"
  local commit mode blob
  while IFS= read -r commit; do
    [ -z "$commit" ] && continue
    read -r mode _ blob _ < <(git ls-tree "$commit" -- "$path" 2>/dev/null)
    [ -z "$blob" ] && continue
    [ "$blob" = "$wanted_blob" ] && [ "$mode" = "$wanted_mode" ] && return 0
  done < <(git rev-list "$default_branch" -- "$path")
  return 1
}

check_diff_records() {
  local file="$1"
  local meta path new_mode new_blob status del_out del_rc
  while IFS= read -r -d '' meta && IFS= read -r -d '' path; do
    read -r _ new_mode _ new_blob status <<< "${meta#:}"
    if [ "$status" = "D" ]; then
      # `git ls-tree`, not `git cat-file -e` -- see
      # delete-rebase-backup-tags.sh's identical comment for the live-verified
      # detail (cross-model-review finding, round 2): `cat-file -e` fails
      # indistinguishably whether the path is genuinely absent or merely has
      # an unreadable blob object, while `ls-tree` never needs to open the
      # blob to answer "does this path exist in the tree."
      del_out=$(git ls-tree "$default_branch" -- "$path" 2>/dev/null)
      del_rc=$?
      [ "$del_rc" -ne 0 ] && return 1
      [ -n "$del_out" ] && return 1
    else
      [ -z "$new_blob" ] && return 1
      is_path_blob_reachable "$path" "$new_blob" "$new_mode" || return 1
    fi
  done < "$file"
  return 0
}

is_tag_content_reachable() {
  local tag="$1"
  local mb
  mb=$(git merge-base -- "$tag" "$default_branch" 2>/dev/null) || return 1
  local tag_commits
  tag_commits=$(git rev-list "$mb..$tag" 2>/dev/null)
  [ -z "$tag_commits" ] && return 1
  local commit cc_diff cc_rc diff_file diff_rc
  while IFS= read -r commit; do
    [ -z "$commit" ] && continue
    if git rev-parse --verify --quiet "$commit^2" >/dev/null 2>&1; then
      cc_diff=$(git diff-tree --cc -p --no-commit-id -r --no-ext-diff --no-textconv "$commit" 2>/dev/null)
      cc_rc=$?
      [ "$cc_rc" -ne 0 ] && return 1
      if [ -z "$cc_diff" ]; then
        continue
      fi
      return 1
    fi
    diff_file=$(mktemp) || return 1
    git diff-tree -r -z --no-commit-id --no-ext-diff --no-textconv --root "$commit" > "$diff_file"
    diff_rc=$?
    if [ "$diff_rc" -ne 0 ]; then
      rm -f "$diff_file"
      return 1
    fi
    if ! check_diff_records "$diff_file"; then
      rm -f "$diff_file"
      return 1
    fi
    rm -f "$diff_file"
  done <<< "$tag_commits"
  return 0
}

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
      elif is_tag_content_reachable "$tag"; then
        echo "reachable from $default_branch: yes (content match after rebase -- commit SHA differs, diff content identical)"
      else
        echo "reachable from $default_branch: NO -- this tag may be the only remaining copy of its commits"
      fi
    fi
  fi
done
