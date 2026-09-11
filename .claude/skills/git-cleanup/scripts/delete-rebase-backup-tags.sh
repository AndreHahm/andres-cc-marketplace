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

# Disables pathspec glob/wildcard magic for every git call this process makes
# (never touches ref-name matching -- only the `-- <path>` argument commands
# like `rev-list`/`ls-tree` accept). Without it, a real path containing a
# pathspec metacharacter (`*`, `?`, `[`) is glob-interpreted rather than
# matched literally -- live-verified: an unquoted `release*txt.txt` pathspec
# matched an unrelated `releaseXtxt.txt` file in a scratch repo, and
# `GIT_LITERAL_PATHSPECS=1` correctly found nothing once no file was
# literally named that. Safe-direction only regardless: is_path_blob_reachable's
# actual acceptance test below is an exact blob (and, since the
# security-reviewer/cross-model-review mode-tracking fix, mode) comparison at
# a specific commit, so a broadened or narrowed candidate set from pathspec
# matching can never turn a real content mismatch into a false "reachable" --
# without this, it could only ever cause a spurious "needs manual review"
# (cross-model-review finding, Codex fresh-eyes + Claude fresh-eyes
# independently, both confirmed by the other side's Phase 2 pass).
export GIT_LITERAL_PATHSPECS=1

SNAPSHOT="$(git rev-parse --git-dir)/delete-rebase-backup-tags.snapshot"

# Get default branch name. Not `... || echo "main"` -- `sed` exits 0 even on
# empty stdin (no origin/HEAD symref set), so the `||` fallback never fires
# and default_branch would silently resolve to an empty string. Same fix as
# phase1-analysis.sh's own default-branch resolution (PR #262 review).
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD \
  2>/dev/null | sed 's@^refs/remotes/origin/@@')
default_branch="${default_branch:-main}"

# Content-based fallback for is_tag_safe_to_delete below. Requires every
# commit unique to the tag (since its own merge-base with $default_branch)
# to have every path it changed reachable on $default_branch -- but
# "reachable" is checked per (path, post-image blob) pair against that
# path's own history on $default_branch, not as one whole-commit diff that
# has to match a single commit there byte-for-byte. Since git blobs are
# purely content-addressed, this also makes patch-id unnecessary as a
# pre-filter: blob-id equality already IS exact byte-for-byte equality, with
# none of patch-id's own whitespace-insensitivity to work around (see
# is_path_blob_reachable below).
#
# This replaces PR #275's exact-diff-text approach specifically to close its
# disclosed, accepted limitation: if $default_branch's own history
# reorganizes a tag commit's changes differently than the tag recorded them
# -- e.g. one file the tag added in a single commit lands on $default_branch
# via a LATER, separate commit instead of the same one -- a whole-commit
# diff-text comparison never finds a match, even though every changed path's
# content is genuinely present. Per-path blob-history search finds it
# regardless of which commit(s) $default_branch's own history split it
# across (live-verified against this repo's real
# feat/pr-ci-governance-rebase-backup-20260907-210042 tag: its one commit
# added 13 files in a single diff, but main's matching commit only carried
# 12 of them -- the 13th, .github/actions/fork-safety/action.yml, landed via
# a wholly separate later commit; a whole-commit diff match could never see
# this, per-path blob search finds the exact blob at that later commit).
#
# `--no-ext-diff --no-textconv` on the raw diff below: without them, a
# repo-configured `diff.external` driver or a `.gitattributes` textconv
# filter could substitute a lossy rendering for real content on either side
# of a comparison, letting two genuinely different blobs render identically
# and falsely match (security-reviewer, M2 -- same concern PR #275 raised
# against the diff-text approach this replaces, still applicable to the raw
# diff-tree output used here).
#
# Known, accepted limitation (still safe-direction-only -- a false negative,
# never a false positive): a deleted path is only checked against
# $default_branch's CURRENT tip, not its full history -- if the path was
# deleted on $default_branch at some point but has since been re-added
# (unusual, but possible), this reports "not reachable" even though the
# original deletion did land at some point. Content additions/modifications
# don't share this limitation the same way -- see the $mb parameter below.
#
# Requires BOTH blob and mode to match at the same historical commit, not
# blob alone -- a mode-only change (chmod +x, or a regular-file/symlink swap
# whose content happens to be byte-identical) is content the tag captured,
# and blob equality alone can't tell "this exact change landed" apart from
# "an unrelated commit happens to have the same bytes at this path but a
# different mode" (cross-model-review finding: Codex fresh-eyes found this
# independently, Claude's Phase 2 pass confirmed it and corrected the
# severity upward from this session's earlier security-reviewer pass, which
# had filed the identical gap as merely informational). `git ls-tree` returns
# mode and blob together in one call rather than needing a second lookup.
#
# `$mb` (the tag's own merge-base with $default_branch, passed down from
# is_tag_content_reachable) bounds the history search to commits AT OR AFTER
# the point the branches actually diverged -- searching $default_branch's
# FULL history without this bound is a real false-positive, not just a
# theoretical one: a path added then deleted from $default_branch entirely
# BEFORE $mb, then re-added with byte-identical content on the tag's own
# branch, would otherwise match that stale pre-divergence blob and be
# reported "reachable" even though the content was never restored to
# $default_branch after the branches diverged -- live-verified (GitHub
# automated review, PR #315, Codex connector P1): built exactly this
# scenario in a scratch repo (add data.txt, delete it, branch off, re-add
# identical data.txt on the branch, delete the branch) and confirmed the
# unbounded search reported "reachable" while `main` never actually
# contained the file post-divergence. Checking `$mb`'s own tree first (not
# just `$mb..$default_branch` history, which excludes `$mb` itself) also
# matters for correctness in the other direction: content already present
# AT the shared ancestor is inherited by $default_branch automatically
# (every commit on $default_branch descends from $mb by construction), even
# if no commit strictly after $mb ever touches that path again -- live
# -verified separately with a tag that modifies a path then reverts it back
# to $mb's own original content, confirming this still correctly reports
# reachable rather than a new false negative from excluding $mb.
is_path_blob_reachable() {
  local path="$1" wanted_blob="$2" wanted_mode="$3" mb="$4"
  local commit mode blob
  read -r mode _ blob _ < <(git ls-tree "$mb" -- "$path" 2>/dev/null)
  if [ -n "$blob" ] && [ "$blob" = "$wanted_blob" ] && [ "$mode" = "$wanted_mode" ]; then
    return 0
  fi
  while IFS= read -r commit; do
    [ -z "$commit" ] && continue
    read -r mode _ blob _ < <(git ls-tree "$commit" -- "$path" 2>/dev/null)
    [ -z "$blob" ] && continue
    [ "$blob" = "$wanted_blob" ] && [ "$mode" = "$wanted_mode" ] && return 0
  done < <(git rev-list "${mb}..${default_branch}" -- "$path")
  return 1
}

# Checks every raw NUL-delimited diff-tree record in file $1 (a real file,
# never a `$(...)`-captured variable -- NUL bytes silently truncate a bash
# string, so `-z` output can only be read back from a file or an open fd)
# against $default_branch. Caller owns creating/removing $1; this function
# never touches it. Split out from is_tag_content_reachable purely so every
# early-return path here can't leak the caller's temp file -- the caller
# does its own single `rm -f` after this returns, on every path, rather
# than repeating cleanup before each of this function's several `return`
# points (security-reviewer finding M1/C1 follow-up: a `trap ... RETURN`
# was considered instead and rejected -- bash's RETURN trap is process-wide,
# not scoped to one function invocation, so it would also fire when this
# very function returns while the caller's `while read -d ''` is still
# reading the same file, unlinking it mid-read; harmless on Linux (unlink
# doesn't invalidate an already-open fd) but not guaranteed on the Windows/
# Git-Bash environment this script actually runs in).
check_diff_records() {
  local file="$1" mb="$2"
  local meta path new_mode new_blob status del_out del_rc
  while IFS= read -r -d '' meta && IFS= read -r -d '' path; do
    # meta: ":<old_mode> <new_mode> <old_blob> <new_blob> <status>" -- old
    # mode/blob aren't needed here, only the post-image
    read -r _ new_mode _ new_blob status <<< "${meta#:}"
    if [ "$status" = "D" ]; then
      # Deletion: satisfied only if $default_branch's CURRENT tree also no
      # longer has this path -- if it does, the tag's removal was never
      # reflected there (see is_path_blob_reachable's own "known, accepted
      # limitation" comment above). `git ls-tree`, not `git cat-file -e`: the
      # latter also fails (nonzero exit) when the path exists but its BLOB
      # object is unreadable/corrupted, which is indistinguishable from "path
      # absent" by exit code alone -- live-verified: deleting a blob object
      # out from under an otherwise-intact tree entry makes `cat-file -e`
      # fail with the path still genuinely present, which the old `&&`
      # silently misread as "deletion satisfied" (cross-model-review finding,
      # round 2, Codex fresh-eyes). `ls-tree` never needs to open the blob at
      # all to answer "does this path exist in the tree" -- live-verified:
      # it returns exit 0 with the entry listed even when that same blob is
      # deleted, and exit 0 with empty output only when the path is
      # genuinely absent; a nonzero exit here means $default_branch itself
      # couldn't be read (a bad ref, or a corrupted root tree), which fails
      # closed the same way the non-merge diff-tree call above already does.
      del_out=$(git ls-tree "$default_branch" -- "$path" 2>/dev/null)
      del_rc=$?
      [ "$del_rc" -ne 0 ] && return 1
      [ -n "$del_out" ] && return 1
    else
      [ -z "$new_blob" ] && return 1
      is_path_blob_reachable "$path" "$new_blob" "$new_mode" "$mb" || return 1
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
      # Merge commit: unchanged from PR #275 -- plain `-p` (used below for
      # every other commit) always shows no diff for a merge, which would
      # otherwise fail the whole tag closed regardless of whether the merge
      # actually introduced any unique content -- each parent's own changes
      # are already walked separately as their own entries in this same
      # rev-list. `--cc` shows only lines that differ from every parent (a
      # real conflict-resolution edit); an empty `--cc` diff means this
      # merge contributes nothing new beyond its parents, so skip it rather
      # than treating it as unverifiable.
      #
      # Capture the exit status separately from stdout -- a `git diff-tree`
      # failure (bad object, corrupted ref) also produces empty stdout
      # (live-verified: exit 128, nothing on stdout, error on stderr), and
      # `[ -z "$cc_diff" ]` alone can't tell that apart from a genuinely
      # trivial merge. Every other empty-result check in this function
      # already fails closed on empty data; this is the one place empty was
      # instead read as a meaningful "safe to skip" signal, so it's the one
      # place a failed command could get silently misread as that signal
      # too (Codex fresh-eyes finding F1, cross-model-review round 3).
      cc_diff=$(git diff-tree --cc -p --no-commit-id -r --no-ext-diff --no-textconv "$commit" 2>/dev/null)
      cc_rc=$?
      [ "$cc_rc" -ne 0 ] && return 1
      if [ -z "$cc_diff" ]; then
        continue
      fi
      # A merge with real conflict-resolution content has no single path's
      # "before" state to diff against -- fail closed rather than accepting
      # unverified content, same as PR #275's original merge-commit handling.
      return 1
    fi
    # Non-merge commit: check every changed path's post-image blob against
    # $default_branch's own history at that path -- not against one
    # commit's whole diff.
    #
    # `--root`: without it, a PARENTLESS commit (a `git subtree --squash`
    # import, a `merge --allow-unrelated-histories` root, a grafted/shallow
    # boundary commit) produces NO diff-tree output at all and would
    # silently pass unverified, since the inner loop below then never runs
    # -- exactly the same "empty output" ambiguity `cc_rc` above already
    # guards against for merge commits, just on the non-merge path instead
    # (security-reviewer finding C1). `--root` makes such a commit show its
    # whole tree as a set of `A` (add) entries instead, which the existing
    # per-path check already handles correctly.
    #
    # `-z` (NUL-delimited, unquoted) instead of the default tab-delimited
    # format: without it, git C-quotes any path containing non-ASCII bytes
    # (under the default `core.quotePath=true`) or a literal quote/
    # backslash/control character, and that quoted string is not the real
    # path -- handing it to `git cat-file -e` below in the deletion branch
    # makes that command fail as a bad revision spec, which the `&&` there
    # would otherwise misread as "path absent from $default_branch",
    # silently treating a genuinely-not-reflected deletion as satisfied
    # (security-reviewer finding M2, live-verified against a real `café.txt`
    # path). `-r` still recurses into subtrees; no `-M`/`-C` (no rename
    # detection) so a rename is reported as a plain delete of the old path
    # plus an add of the new one, which this loop already handles without
    # any special-casing -- enabling rename detection here would also
    # actively break the NUL-delimited parsing below, since a `-z` rename
    # record carries two paths per entry instead of one.
    #
    # `-z` output can't be captured into a `$(...)` variable (a NUL byte
    # truncates a bash string), so this reads into a temp file instead --
    # which is also the only way to check the exit status separately from
    # "produced no records", the same gap `cc_rc` above closes for the
    # merge branch (security-reviewer finding M1: an object read failure on
    # this path previously produced empty stdout, indistinguishable from a
    # genuinely empty/no-op commit, and was silently treated as satisfied).
    diff_file=$(mktemp) || return 1
    git diff-tree -r -z --no-commit-id --no-ext-diff --no-textconv --root "$commit" > "$diff_file"
    diff_rc=$?
    if [ "$diff_rc" -ne 0 ]; then
      rm -f "$diff_file"
      return 1
    fi
    if ! check_diff_records "$diff_file" "$mb"; then
      rm -f "$diff_file"
      return 1
    fi
    rm -f "$diff_file"
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
    # `git update-ref -d` deletion below both keep the raw, unescaped bytes;
    # only this printed line is quoted for safe, unambiguous display.
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

# Each deletion is a separate compare-and-delete call so one failure doesn't
# block the rest -- same partial-failure principle Phase 5 already documents
# for branch deletions. `$tag` here is a shell variable holding raw bytes
# read from the snapshot file, never text the model composed into this
# command.
failed=0
for tag in "${matched[@]}"; do
  # Resolve the object BEFORE running the safety check, not after -- via the
  # fully-qualified refs/tags/<name> form -- never bare "$tag" (which could
  # start with a dash and be misparsed as an option). Prefixing with
  # refs/tags/ rules that out unconditionally, with no need for a
  # stop-parsing flag: `--end-of-options` was tried first and doesn't
  # actually work as one for `git rev-parse` in the git version this was
  # verified against -- live-verified, it gets echoed back as a literal
  # token on its own output line instead of suppressing option parsing.
  #
  # Ordering matters: resolving this AFTER is_tag_safe_to_delete (the
  # original shape of this fix) leaves a gap of its own -- if the tag is
  # force-moved in the window between the safety check's own internal,
  # by-name resolution and this assignment, $verified_oid captures the NEW,
  # never-actually-checked object, and the compare-and-delete below then
  # "verifies" trivially against itself, deleting an object the safety
  # check never examined (Codex automated PR review finding, PR #275
  # round 2). Resolving first closes this: is_tag_safe_to_delete may still
  # end up checking a later-moved state, but the delete below can only ever
  # succeed against $pre_check_oid specifically -- if the ref no longer
  # points there by the time of the actual delete (moved during or after
  # the check, for any reason), the compare-and-delete correctly refuses,
  # regardless of what the safety check itself returned. Residual, not
  # fully closed: if the tag moves away from $pre_check_oid and then back
  # to the exact same object before the delete runs, this can't distinguish
  # that from never having moved at all -- an intentionally accepted,
  # vanishingly narrow race for a manually-run, interactive cleanup tool,
  # not something a background/automated process would trigger.
  pre_check_oid=$(git rev-parse "refs/tags/$tag" 2>/dev/null)
  if [ -z "$pre_check_oid" ]; then
    echo "Skipped '$tag': could not resolve its current object id" >&2
    failed=1
    continue
  fi
  # Re-verify immediately before deleting, not just at --list time -- the
  # tag could have been force-moved, or $default_branch could have advanced,
  # in the time since --list ran (see the predicate's own comment above).
  if ! is_tag_safe_to_delete "$tag"; then
    echo "Skipped '$tag': no longer verified safe to delete -- repo state changed since --list (the tag may have moved, been removed, or $default_branch advanced); run --list again and retry" >&2
    failed=1
    continue
  fi
  verified_oid="$pre_check_oid"
  # Atomic compare-and-delete: `git update-ref -d <ref> <old-oid>` only
  # deletes when the ref's CURRENT value still matches $verified_oid,
  # closing the remaining race between this verification and the actual
  # delete -- a name-based `git tag -d` has no such guarantee, since it
  # deletes whatever the ref currently points to even if a concurrent
  # process force-moved it after verification but before this exact command
  # runs (the window `is_tag_safe_to_delete`'s own content-reachability path
  # widened, by taking real wall-clock time to run, compared to the
  # near-instant raw-SHA-ancestry check it used to be the only path through).
  # Live-verified in an isolated scratch repo: deleting with the correct,
  # just-resolved oid succeeds; deleting after force-moving the tag with a
  # now-stale oid is correctly refused (`error: cannot lock ref ...: is at
  # <new> but expected <old>`, exit 1), leaving the moved (unverified) tag
  # intact rather than deleting it (Devin automated PR review finding,
  # PR #275, cited against this repo's own
  # .claude/rules/recheck-state-before-side-effecting-action.md).
  if git update-ref -d "refs/tags/$tag" "$verified_oid"; then
    :
  else
    echo "Error: failed to delete tag '$tag' (may have moved since verification, or another error occurred)" >&2
    failed=1
  fi
done

rm -f "$SNAPSHOT"
exit "$failed"
