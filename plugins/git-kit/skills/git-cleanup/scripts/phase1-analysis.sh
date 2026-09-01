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

# Patch-id (content) index of every commit on $default_branch, built lazily
# on first use and cached for the rest of this script run. A rebase-then-
# merge sequence rewrites every commit's SHA but preserves each commit's own
# diff content, so `git merge-base --is-ancestor` (object-identity based)
# alone reports "not reachable" even when a tag's entire history genuinely
# landed on $default_branch via rebase -- live-verified against this repo's
# own PR #269 (feat/merge-pr-conflict-checks-rebase-backup-20260901-064237):
# all 6 commits unique to the tag had an exact patch-id match on main,
# despite every one having a different SHA post-rebase. Same two-signal
# approach (identity first, content fallback) already reviewed and shipped
# in remap-handoff-shas.py's own patch-id index, and mirrored in
# delete-rebase-backup-tags.sh's own is_tag_content_reachable -- this
# script's report must agree with what that script would actually delete.
#
# `default_branch_patchids` must be called bare (never as `$(...)`) --
# command substitution forks a subshell, and an assignment to
# $main_patchid_index made inside that subshell is discarded when it exits,
# silently defeating the cache on every call (found by security-reviewer,
# PR #269 follow-up; live-verified: this bug alone took a 22-tag sweep from
# an expected ~2s to 80s, rebuilding the full-history index once per tag).
#
# `--no-ext-diff --no-textconv` here and on the per-commit check below
# match delete-rebase-backup-tags.sh's own hardening -- see that script's
# identical comment for the finding this addresses (M2) and for why the
# index build keeps `git log -p`'s default pretty format rather than a
# message-suppressed one (`--format=''` breaks patch-id's per-commit
# boundary detection), while the per-commit check below still avoids
# piping the commit message into patch-id at all, by construction.
#
# `main_patchid_log` keeps the full `git patch-id` output, not just a
# deduped set of ids -- patch-id alone is a pre-filter, not the final
# verdict, since it's documented to ignore whitespace (Codex fresh-eyes
# finding F1, cross-model-review, PR #269 follow-up; see
# delete-rebase-backup-tags.sh's identical comment for the live-verified
# detail and why the exact-match fallback below doesn't reject the genuine
# rebase-merge case).
main_patchid_log=""

default_branch_patchids() {
  if [ -z "$main_patchid_log" ]; then
    main_patchid_log=$(git log -p --no-ext-diff --no-textconv \
      "$default_branch" -- 2>/dev/null \
      | git patch-id --stable)
  fi
}

# Requires every commit unique to the tag (since its own merge-base with
# $default_branch) to have an exact, byte-for-byte diff-text match against
# some commit on $default_branch's full history -- a single unmatched
# commit keeps the tag flagged unreachable, since it may be the only
# remaining copy of that one commit's changes. Patch-id narrows the
# candidate set cheaply; it is never the acceptance criterion by itself.
is_tag_content_reachable() {
  local tag="$1"
  local mb
  mb=$(git merge-base -- "$tag" "$default_branch" 2>/dev/null) || return 1
  local tag_commits
  tag_commits=$(git rev-list "$mb..$tag" 2>/dev/null)
  [ -z "$tag_commits" ] && return 1
  default_branch_patchids
  [ -z "$main_patchid_log" ] && return 1
  local commit tag_diff pid candidates cand exact_match
  while IFS= read -r commit; do
    [ -z "$commit" ] && continue
    if git rev-parse --verify --quiet "$commit^2" >/dev/null 2>&1; then
      # Merge commit: plain `-p` (used below for every other commit) always
      # shows no diff for a merge, which would otherwise fail the whole tag
      # closed regardless of whether the merge actually introduced any
      # unique content -- each parent's own changes are already walked
      # separately as their own entries in this same rev-list. `--cc` shows
      # only lines that differ from every parent (a real conflict-resolution
      # edit); an empty `--cc` diff means this merge contributes nothing new
      # beyond its parents, so skip it rather than treating it as
      # unverifiable.
      if [ -z "$(git diff-tree --cc -p --no-commit-id -r --no-ext-diff --no-textconv "$commit")" ]; then
        continue
      fi
      # A merge with real conflict-resolution content has no comparable
      # entry in $main_patchid_log -- that index is built from plain
      # `git log -p`, which equally skips merge diffs, so there is nothing
      # to match this content against. Fail closed rather than accepting
      # unverified content.
      return 1
    fi
    tag_diff=$(git diff-tree -p --no-commit-id -r --no-ext-diff --no-textconv "$commit")
    pid=$(printf '%s\n' "$tag_diff" | git patch-id --stable | awk '{print $1}')
    [ -z "$pid" ] && return 1
    candidates=$(printf '%s\n' "$main_patchid_log" | awk -v p="$pid" '$1 == p {print $2}')
    [ -z "$candidates" ] && return 1
    exact_match=false
    while IFS= read -r cand; do
      [ -z "$cand" ] && continue
      if [ "$(git diff-tree -p --no-commit-id -r --no-ext-diff --no-textconv "$cand")" = "$tag_diff" ]; then
        exact_match=true
        break
      fi
    done <<< "$candidates"
    $exact_match || return 1
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
