#!/usr/bin/env bash
# Lists (--list) or deletes (by index) leftover git-rebase-sync rebase-backup
# tags git-cleanup's Phase 3.6 has verified safe to delete. A tag name is
# untrusted content -- git's own ref-name rules permit almost every shell
# metacharacter (`$(cmd)`, backticks, `;`, `&`, `|`, etc. are all legal in a
# tag name; live-verified), so no character-class check on a value the agent
# then types into a command is ever fully safe, and no such check can also
# stay complete against every legal name. This script never receives a tag
# name as an argument or on stdin: `--list` re-derives the deletable-tag list
# itself and persists it to a snapshot file (NUL-delimited, raw bytes); the
# delete mode reads that exact snapshot back rather than recomputing it --
# closing a race where repo state changes between the two calls could
# otherwise resolve the same index to a different tag the second time,
# mirroring stage-selected-files.sh's own snapshot rationale. The model only
# ever has to pass back plain digit indices, never a single character of
# untrusted tag-name content.
#
# Called by the git-cleanup skill's Phase 5: run `--list` first (this is also
# safe to run standalone for Gate 1's own candidate list), present the
# numbered output to the user, then re-invoke with the chosen indices once
# the user confirms at Gate 2.
set -euo pipefail

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Error: not inside a git repository" >&2; exit 1; }
cd "$(git rev-parse --show-toplevel)"

SNAPSHOT="$(git rev-parse --git-dir)/delete-rebase-backup-tags.snapshot"

# Get default branch name. Not `... || echo "main"` -- `sed` exits 0 even on
# empty stdin (no origin/HEAD symref set), so the `||` fallback never fires
# and default_branch would silently resolve to an empty string. Same fix as
# phase1-analysis.sh's own default-branch resolution (PR #262 review).
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD \
  2>/dev/null | sed 's@^refs/remotes/origin/@@')
default_branch="${default_branch:-main}"

# Patch-id (content) index of every commit on $default_branch, built lazily
# on first use and cached for the rest of this script run (a fresh process
# per invocation, so this never crosses the --list / delete TOCTOU boundary
# described below). A rebase-then-merge sequence rewrites every commit's SHA
# but preserves each commit's own diff content, so `git merge-base
# --is-ancestor` (object-identity based) alone reports "not reachable" even
# when a tag's entire history genuinely landed on $default_branch via
# rebase -- live-verified against this repo's own PR #269
# (feat/merge-pr-conflict-checks-rebase-backup-20260901-064237): all 6
# commits unique to the tag had an exact patch-id match on main, despite
# every one having a different SHA post-rebase. Same two-signal approach
# (identity first, content fallback) already reviewed and shipped in
# remap-handoff-shas.py's own patch-id index.
#
# `default_branch_patchids` must be called bare (never as `$(...)`) --
# command substitution forks a subshell, and an assignment to
# $main_patchid_index made inside that subshell is discarded when it exits,
# silently defeating the cache on every call (found by security-reviewer,
# PR #269 follow-up; live-verified: this bug alone took the 22-tag --list
# run from an expected ~2s to 80s, rebuilding the full-history index once
# per tag instead of once per script run).
#
# `--no-ext-diff --no-textconv` on both the index build and the per-commit
# check below: without them, a repo-configured `diff.external` driver or a
# `.gitattributes` textconv filter could substitute a lossy rendering for
# real content on either side of a comparison, letting two genuinely
# different blobs render identically and falsely match (security-reviewer,
# M2).
#
# This index build keeps `git log -p`'s default pretty format (commit
# header + full message + diff) rather than a message-suppressed one --
# `--format=''` was tried and reverted: `git patch-id` splits a multi-commit
# stream into per-commit patches using the "commit <sha>" header line that
# format produces, and suppressing it collapses the entire branch history
# into one giant patch-id instead of one per commit (live-verified: the
# 667-commit index came back as a single id). The commit-message content
# this format includes is not a live risk here regardless -- see the
# per-commit check below, which avoids it by construction.
#
# `main_patchid_log` keeps the full `git patch-id` output ("<patch-id>
# <commit-sha>" per line), not just a deduped set of ids -- patch-id alone
# is a pre-filter, not the final verdict. `git patch-id` is documented to
# ignore whitespace when hashing, so two commits whose diffs differ ONLY in
# whitespace can share a patch-id (live-verified: adding 2 vs. 4 leading
# spaces to the same line produced identical patch-ids for genuinely
# different diff bytes -- Codex fresh-eyes finding F1, cross-model-review,
# PR #269 follow-up). Trusting patch-id equality alone would let a tag
# whose real content differs from $default_branch only by whitespace be
# misclassified as safe to delete. `is_tag_content_reachable` below uses
# this log to narrow candidates by patch-id cheaply, then requires an exact
# byte-for-byte diff-text match against at least one candidate before
# accepting -- confirmed this doesn't reject the genuine rebase-merge case:
# a rebase preserves file content, and git blob hashes are purely
# content-addressed, so the "index <old>..<new>" line inside a rebased
# commit's diff text stays byte-identical too (live-verified against this
# repo's real PR #269 commit pair).
main_patchid_log=""

default_branch_patchids() {
  if [ -z "$main_patchid_log" ]; then
    main_patchid_log=$(git log -p --no-ext-diff --no-textconv \
      "$default_branch" -- 2>/dev/null \
      | git patch-id --stable)
  fi
}

# Content-based fallback for is_tag_safe_to_delete below. Requires every
# commit unique to the tag (since its own merge-base with $default_branch)
# to have an exact, byte-for-byte diff-text match against some commit on
# $default_branch's full history -- a single unmatched commit keeps the tag
# flagged unsafe, since it may be the only remaining copy of that one
# commit's changes. Patch-id narrows the candidate set cheaply (typically to
# zero or one commit); it is never the acceptance criterion by itself -- see
# the comment above default_branch_patchids for why.
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

# Single source of truth for the safe-to-delete predicate (branch gone or
# merged AND the tag's own commit reachable from the default branch, by
# identity or -- per is_tag_content_reachable above -- by content) -- used
# both by --list (to build the candidate snapshot) and, separately, by the
# delete loop below (to re-verify each tag immediately before deleting it).
# Re-checking here rather than trusting the snapshot's mere presence closes a
# TOCTOU gap found by cross-model-review (round 5, PR #262): between --list
# and the actual delete call, the tag could be force-moved to a different
# commit, or $default_branch itself could advance -- per
# .claude/rules/recheck-state-before-side-effecting-action.md, a stale read
# must never feed directly into a destructive action.
is_tag_safe_to_delete() {
  local tag="$1"
  if [[ "$tag" =~ ^(.+)-rebase-backup-[0-9]{8}-[0-9]{6}$ ]]; then
    local branch="${BASH_REMATCH[1]}"
    local branch_gone=false
    local branch_merged=false
    if git show-ref --verify --quiet "refs/heads/$branch"; then
      if git branch --merged "$default_branch" --format='%(refname:short)' \
        | grep -qxF "$branch"; then
        branch_merged=true
      fi
    else
      branch_gone=true
    fi
    if $branch_gone || $branch_merged; then
      if git merge-base --is-ancestor "$tag" "$default_branch" 2>/dev/null; then
        return 0
      fi
      is_tag_content_reachable "$tag"
      return $?
    fi
  fi
  return 1
}

list_deletable() {
  for tag in $(git tag -l '*-rebase-backup-*'); do
    if is_tag_safe_to_delete "$tag"; then
      printf '%s\0' "$tag"
    fi
  done
}

if [ "${1:-}" = "--list" ]; then
  list_deletable > "$SNAPSHOT"
  i=0
  while IFS= read -r -d '' tag; do
    i=$((i + 1))
    # %q (display only): a tag name can contain characters that would make
    # the numbered listing itself misleading -- the snapshot file and the
    # `git tag -d` argument below both keep the raw, unescaped bytes; only
    # this printed line is quoted for safe, unambiguous display.
    printf '%d\t%q\n' "$i" "$tag"
  done < "$SNAPSHOT"
  exit 0
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 --list | <index> [index...]" >&2
  exit 2
fi

if [ ! -f "$SNAPSHOT" ]; then
  echo "Error: no candidate list found -- run --list first" >&2
  exit 2
fi

declare -A wanted
for arg in "$@"; do
  if ! [[ "$arg" =~ ^[0-9]+$ ]]; then
    echo "Error: index '$arg' is not a positive integer" >&2
    exit 2
  fi
  wanted["$arg"]=1
done

matched=()
i=0
while IFS= read -r -d '' tag; do
  i=$((i + 1))
  if [ -n "${wanted[$i]:-}" ]; then
    matched+=("$tag")
  fi
done < "$SNAPSHOT"

if [ "${#matched[@]}" -ne "${#wanted[@]}" ]; then
  echo "Error: one or more requested indices are out of range -- run --list again and retry" >&2
  exit 1
fi

# Each deletion is a separate `git tag -d` call so one failure doesn't block
# the rest -- same partial-failure principle Phase 5 already documents for
# branch deletions. `$tag` here is a shell variable holding raw bytes read
# from the snapshot file, never text the model composed into this command.
failed=0
for tag in "${matched[@]}"; do
  # Re-verify immediately before deleting, not just at --list time -- the
  # tag could have been force-moved, or $default_branch could have advanced,
  # in the time since --list ran (see the predicate's own comment above).
  if ! is_tag_safe_to_delete "$tag"; then
    echo "Skipped '$tag': no longer verified safe to delete -- repo state changed since --list (the tag may have moved, been removed, or $default_branch advanced); run --list again and retry" >&2
    failed=1
    continue
  fi
  if git tag -d -- "$tag"; then
    :
  else
    echo "Error: failed to delete tag '$tag'" >&2
    failed=1
  fi
done

rm -f "$SNAPSHOT"
exit "$failed"
