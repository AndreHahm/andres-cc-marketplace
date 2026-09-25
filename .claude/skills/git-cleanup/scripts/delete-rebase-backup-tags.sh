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
# mirroring git-stage-selected-files.sh's own snapshot rationale. The model only
# ever has to pass back plain digit indices, never a single character of
# untrusted tag-name content.
#
# Called by the git-cleanup skill's Phase 5: run `--list` first (this is also
# safe to run standalone for Gate 1's own candidate list), present the
# numbered output to the user, then re-invoke with the chosen indices once
# the user confirms at Gate 2.
#
# --list-review/--diff/--force/--keep (added for the guided-manual-review
# phase): the analogous index-only interface for the population --list
# deliberately EXCLUDES -- tags that failed the reachability check and would
# otherwise sit in "needs review" forever with no further help. --list-review
# snapshots that set the same way --list does (also recording $default_branch's
# own oid at that moment, and silently dropping any candidate with a still-
# valid "keep" decision already on file); --diff is read-only evidence (a
# full tree diff against $default_branch) for one candidate by index; --force
# is the actual bypass -- it deletes a review candidate WITHOUT re-checking
# reachability (it already failed that check, by construction), protected by
# an atomic compare-and-delete pinned to BOTH the tag's own recorded oid and
# $default_branch's recorded oid (not a freshly re-resolved one -- see
# --force's own comment for why); --keep records a "don't ask again until
# something changes" decision, using the identical index/oid-pinning
# discipline, entirely inside this script so the calling skill never needs a
# raw tag name in a composed command. --force/--keep are meant to be reached
# only after git-cleanup's own guided-review phase has shown the user
# --diff's output and (for --force) obtained a second separate confirmation
# -- this script has no way to enforce that from its own side, the same
# trust boundary the plain index-based delete mode above already has with
# Gate 2's confirmation.
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
# Separate snapshot for the manual-review candidate set (--list-review/--diff/
# --force below) -- deliberately never shares $SNAPSHOT with the normal
# deletable set. The two lists are mutually exclusive by construction (a tag
# is either automatically safe to delete, or a manual-review candidate, never
# both), but keeping the files separate means running --list (e.g. from a
# concurrent invocation) can never silently invalidate an in-progress
# --list-review/--diff/--force sequence, or vice versa.
REVIEW_SNAPSHOT="$(git rev-parse --git-dir)/delete-rebase-backup-tags.review-snapshot"
# Generation stamp for $REVIEW_SNAPSHOT (Codex/CodeRabbit cross-model-review
# finding, PR #322 round 1, Critical): --list-review's own index numbering
# only means anything relative to the EXACT snapshot content that produced
# it -- without a way to detect "the snapshot was regenerated since I last
# looked," a concurrent --list-review (another session, another process)
# between a human's --diff and their --force/--keep silently changes what a
# previously-shown index actually refers to, with nothing in the existing
# atomic-oid-compare protection able to catch it (that check validates the
# CURRENT snapshot's own row, which is self-consistent by construction --
# the race is about whether the human's own mental model of "index N" still
# matches the CURRENT snapshot's row N, not whether row N itself is stale).
# Live-verified: two orphan-tag candidates at indices 1/2, a third candidate
# added and a concurrent --list-review re-run, then the original index-1
# tag removed and --list-review re-run again -- index 1 silently resolved
# to a completely different tag than the one first shown. --diff/--force/
# --keep below all require the caller to pass back the exact token
# --list-review printed; a mismatch refuses outright rather than acting on
# an index whose meaning may have changed. Not a security boundary (a
# script-generated token, never derived from or composed with a raw tag
# name -- the untrusted-content risk this script's whole index-only design
# exists to avoid never applies to this token), just a staleness
# fingerprint: $RANDOM twice plus a timestamp and this process's own PID is
# far more than enough entropy to distinguish "the same listing" from "a
# different one," without needing /dev/urandom or any other
# environment-dependent source.
#
# The generation token is embedded as the FIRST NUL-terminated field
# WITHIN $REVIEW_SNAPSHOT itself (read by every consumer below before the
# tag/oid/dsha triples), not a second, separate file -- Codex cross-model-
# review finding (PR #322 round 2, Critical), live-verified: round 1's
# first version wrote $REVIEW_SNAPSHOT and a sibling `.generation` file as
# two SEPARATE writes. An interruption between them (a second --list-review
# that successfully overwrites the snapshot but never reaches its own
# generation-file write) leaves the OLD generation file's content matching
# an OLD token that a caller still holds, while the snapshot it now points
# at has already been replaced -- reproduced live by manually replaying
# exactly that interrupted-write sequence: the old token's `--diff` call
# succeeded (exit 0) against the REPLACED snapshot's own row 1, a
# completely different tag than the one the old token was originally
# issued for. A single file, updated via a single atomic `mv` (the same
# mktemp-then-mv pattern already used for $DECISIONS_FILE below), has no
# two-write window for this to happen in at all -- either the whole update
# lands, or none of it does.
# Decision file lives at the repo's WORKING TREE root (not $GIT_DIR like the
# snapshots above) -- it's a human-facing, persistent record meant to survive
# across script runs, not a same-invocation handoff file. Read/write for this
# stays entirely inside this script (--list-review/--keep below), never as
# ad hoc jq/mv commands the calling skill composes -- security-reviewer
# finding C3: those commands would have needed a raw tag name typed directly
# into command text (Bash has no persistent shell state across separate tool
# calls, and no prior mode of this script ever emitted a raw, unescaped tag
# name for a caller to capture into a variable), reintroducing exactly the
# untrusted-tag-name-in-a-command risk this script's whole index-only design
# exists to avoid. Keying by index below, not name, closes this the same way
# --diff/--force already do. Resolved via `git rev-parse --show-toplevel`
# (already the script's own cwd, set above) rather than a bare relative
# path, so this is never accidentally created wherever the caller's shell
# happened to be cwd'd (security-reviewer finding m4).
DECISIONS_FILE="$(git rev-parse --show-toplevel)/.claude/git-cleanup-review-decisions.local.json"

# Get default branch name. Not `... || echo "main"` -- `sed` exits 0 even on
# empty stdin (no origin/HEAD symref set), so the `||` fallback never fires
# and default_branch would silently resolve to an empty string. Same fix as
# phase1-analysis.sh's own default-branch resolution (PR #262 review).
#
# `{ ... || true; }` around the FIRST pipeline stage specifically (not a
# trailing `|| true` on the whole line, which would only ever apply to
# `sed`'s own exit status): without it, a repo with no origin/HEAD symref at
# all -- any fresh `git init` repo, or plenty of real ones that never ran
# `git remote set-head origin --auto` -- makes `git symbolic-ref` itself fail
# (exit 128), and under this script's own `set -euo pipefail`, `pipefail`
# propagates that as the WHOLE PIPELINE's exit status (since `sed` on empty
# stdin still exits 0, the pipeline's status becomes the one non-zero exit
# among its stages). Under `set -e`, that failing pipeline -- used here as
# the right-hand side of a plain assignment -- kills the entire script
# immediately, on this exact line, with NO output at all (not even a
# fatal message, since `2>/dev/null` swallows the one git itself would have
# printed) -- discovered live while writing this script's own regression
# tests (`test-content-reachable.sh` scenarios 23-26), whose scratch repos
# have no `origin` remote by construction and hit this every time. This is a
# strictly worse outcome than issue #263 originally described (default_branch
# silently resolving to a WRONG existing branch): here the script never
# reaches its own documented `${default_branch:-main}` fallback at all --
# every caller of this script (and phase1-analysis.sh's identical copy) saw a
# bare, unexplained exit 128 in any repo without an origin/HEAD symref,
# indistinguishable from "no rebase-backup tags to report" unless the exit
# code was specifically checked. `|| true` makes the first stage always
# exit 0, so the pipeline's status becomes `sed`'s own (0), letting the
# already-correct `${default_branch:-main}` fallback on the next line
# actually run as originally intended.
default_branch=$({ git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null || true; } \
  | sed 's@^refs/remotes/origin/@@')
default_branch="${default_branch:-main}"

# Fail loudly here, once, rather than letting an unresolvable $default_branch
# propagate silently into every downstream function's own fail-closed
# behavior -- security-reviewer finding C1 (guided-manual-review feature):
# --diff's two git calls below both swallow stderr and never check exit
# status, so a bad $default_branch previously produced the exact same empty
# output as a genuinely empty (safe-to-delete) diff, with no way for a human
# reviewer to tell the two apart.
if ! git rev-parse --verify --quiet "$default_branch" >/dev/null; then
  echo "Error: default branch '$default_branch' does not resolve to a valid ref -- refusing to run" >&2
  exit 2
fi

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
#
# One `git log --raw` pass per path replaces what used to be one `rev-list`
# plus one `ls-tree` subprocess PER commit touching that path -- on this
# repo's own real tag history, checking 5 tags this way took ~15-17s
# (CodeRabbit automated PR review, PR #315, live-verified: a recorded run
# over 5 tags with many changed paths each spawned a subprocess per
# (path, commit) pair). `-m` is required, not optional -- without it, `git
# log --raw` shows NOTHING for a merge commit with genuine hand-resolved
# conflict content (`git ls-tree`, used before this batching, never had this
# blind spot, since it reads the commit's final tree directly rather than
# diffing against a parent) -- live-verified in an isolated scratch repo:
# a merge commit with real conflict-resolution content produced zero raw
# records under plain `--raw`, but `-m` (diff against each parent
# separately) correctly surfaces the resolved blob+mode either way, since
# every parent-comparison's "new" side reflects the same final tree state
# regardless of which parent it's diffed against. `--format=` (empty)
# suppresses the commit header entirely -- deliberately: this function
# doesn't need to know WHICH commit a match came from, only whether any
# record anywhere in the whole flattened, NUL-delimited stream matches, so
# dropping the header avoids having to track commit boundaries across a
# multi-commit, multi-parent batch at all. No separate exit-status check
# here (unlike check_diff_records's own diff-tree call): empty output --
# whether from a genuine no-match or an underlying git failure -- already
# produces the correct fail-closed `return 1` either way, since there is no
# code path here where a failure could be misread as a positive "reachable"
# signal (`.claude/rules/require-tests-for-behavior-changes.md`'s own
# sibling-occurrence sweep was applied here and found no gap: every OTHER
# empty-means-safe-to-skip anti-pattern in this file involves treating
# emptiness as permission to CONTINUE past a check, which this function
# never does).
#
# `--no-abbrev`: `git log --raw`'s default raw-format hashes are
# ABBREVIATED (short, e.g. 7 chars) -- a real, verified difference from
# `git diff-tree`'s raw format used everywhere else in this file, which
# already defaults to full 40-char hashes with no extra flag needed.
# Without `--no-abbrev` here, every blob comparison below silently fails
# closed for the wrong reason (a 7-char prefix can never equal the full
# `$wanted_blob` this function receives), live-verified: this exact gap
# broke 7 of this file's own persisted regression scenarios the first time
# this batching was written, before `--no-abbrev` was added. `--full-index`
# alone -- the flag `git diff`/`git diff-tree` themselves document for this
# purpose -- was tried first and found NOT sufficient for `git log`
# specifically; `--no-abbrev` is the flag that actually works there,
# confirmed by testing each in isolation.
is_path_blob_reachable() {
  local path="$1" wanted_blob="$2" wanted_mode="$3" mb="$4"
  local mode blob
  read -r mode _ blob _ < <(git ls-tree "$mb" -- "$path" 2>/dev/null)
  if [ -n "$blob" ] && [ "$blob" = "$wanted_blob" ] && [ "$mode" = "$wanted_mode" ]; then
    return 0
  fi
  # A "final-state shortcut" was tried here for issue #317 (accepting a
  # commit's own blob as reachable whenever $tag's own FINAL content at
  # $path matched $default_branch's CURRENT content, reasoning that a
  # superseded-within-the-tag intermediate blob no longer mattered) and
  # REVERTED before ever shipping -- found unsafe by a pre-push
  # cross-model-review pass (Codex fresh-eyes, high confidence), live-
  # verified in an isolated scratch repo before reverting: a tag whose
  # unique history adds unique content to a path and then REVERTS that
  # same path back to $default_branch's own original content (never
  # touched on $default_branch at all) passed the shortcut and was reported
  # SAFE TO DELETE, even though the reverted-away content exists NOWHERE
  # else and would be permanently lost (eventually garbage-collected) once
  # the tag is gone -- a genuine false POSITIVE, strictly worse than #317's
  # own false-negative bug, since it would have caused confident, automated
  # data loss rather than an unnecessary manual-review prompt. No safe
  # narrowing of the shortcut was found that still resolves #317's own
  # scenario: restricting it to only fire when a commit's own blob equals
  # the tag's tip blob for that path (the only version that can't also be a
  # discarded intermediate) makes it fire exclusively for the LAST commit
  # touching a path -- which the existing mb-tree/history checks below
  # already cover on their own, so the narrowed shortcut adds no value for
  # #317's actual reordering case, which specifically requires validating
  # an EARLIER, non-final commit's blob. #317-shaped tags are instead left
  # to `--list-review`/`--diff`/`--force` (the guided-manual-review feature
  # shipped alongside this revert) -- a human reviewing the actual diff
  # evidence is the safe way to resolve this class of case; no blob-
  # identity-only shortcut can distinguish "converged via reordering" from
  # "converged via an unrelated revert that discarded unique content."
  local hist_file meta new_mode new_blob found
  hist_file=$(mktemp) || return 1
  git log --raw -m --root -z --no-abbrev --no-ext-diff --no-textconv --format= \
    "${mb}..${default_branch}" -- "$path" > "$hist_file" 2>/dev/null
  found=1
  while IFS= read -r -d '' meta && IFS= read -r -d ''; do
    read -r _ new_mode _ new_blob _ <<< "${meta#:}"
    if [ "$new_blob" = "$wanted_blob" ] && [ "$new_mode" = "$wanted_mode" ]; then
      found=0
      break
    fi
  done < "$hist_file"
  rm -f "$hist_file"
  return "$found"
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
      # `&& del_rc=0 || del_rc=$?`, not a bare assignment followed by
      # `del_rc=$?` on the next line -- security-reviewer/Codex cross-model-
      # review finding (F1, pre-existing sibling instance swept in after the
      # finding on --force/--keep/--diff): under this script's own
      # `set -euo pipefail`, a plain `del_out=$(git ls-tree ...)` with no
      # `||` fallback triggers immediate script exit the instant `git
      # ls-tree` fails, before the very next line (`del_rc=$?`) can ever
      # run -- the exact same root cause, just an older instance of it. The
      # `&&`/`||` compound's own exit status is always 0, so `set -e` never
      # fires here regardless of whether `git ls-tree` itself succeeded.
      del_out=$(git ls-tree "$default_branch" -- "$path" 2>/dev/null) && del_rc=0 || del_rc=$?
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
  # `|| return 1` -- security-reviewer/Codex cross-model-review finding
  # (F1, pre-existing sibling instance): under `set -euo pipefail`, a bare
  # `tag_commits=$(git rev-list ...)` with no `||` fallback triggers
  # immediate script exit if `$tag` or `$mb` somehow stop resolving (e.g.
  # concurrent force-deletion) between the merge-base call above and here,
  # instead of the graceful `return 1` (fail closed) this function's own
  # design already intends for exactly this kind of failure.
  tag_commits=$(git rev-list "$mb..$tag" 2>/dev/null) || return 1
  [ -z "$tag_commits" ] && return 1
  local commit diff_file diff_rc
  while IFS= read -r commit; do
    [ -z "$commit" ] && continue
    # One code path for merge AND non-merge commits -- `-m` is a no-op for a
    # non-merge commit (verified: identical output with or without it) and,
    # for a merge, makes `git diff-tree` show a full per-parent diff instead
    # of the default "no diff at all for a merge" behavior. This replaces an
    # earlier `--cc`-based merge-only branch that treated an empty `--cc`
    # diff as "this merge contributes nothing new, skip it" -- live-verified
    # to be a real false positive (GitHub automated review, PR #315, Codex
    # connector P1 on commit bd9ea5de4c): `--cc` only shows a path that
    # differs from EVERY parent, so a merge that force-resolves to exactly
    # ONE parent's state for a path is invisible to `--cc` even when that
    # represents real content loss relative to the OTHER parent -- built a
    # scratch-repo case where parent1 adds a file, parent2 is a divergent
    # branch with no changes to it at all, and the merge is forced to match
    # parent2 (dropping the file): `--cc` reported empty (correctly, by its
    # own definition) but `$default_branch` still had the file the tag's own
    # merge discarded, which the old `continue` on empty `cc_diff` silently
    # let through as "reachable". `-m` surfaces this: the diff against
    # parent1 shows the file as deleted, which flows through
    # `check_diff_records` exactly like any other deletion and correctly
    # fails closed since `$default_branch` still has it. A genuinely trivial
    # merge (no unique content vs. either parent) still produces zero
    # records against both parents and passes, unaffected
    # (`scenario_trivial_merge_skipped`). A merge with real hand-resolved
    # conflict content produces a record (against whichever parent's
    # pre-image differs from the resolution) that is checked the same way
    # any other path change is -- no more "no single path's before state to
    # diff against" special case; `-m`'s per-parent diff already resolves
    # unambiguously to a concrete pre-image per parent.
    #
    # `--root`: without it, a PARENTLESS commit (a `git subtree --squash`
    # import, a `merge --allow-unrelated-histories` root, a grafted/shallow
    # boundary commit) produces NO diff-tree output at all and would
    # silently pass unverified, since the inner loop below then never runs
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
    # "produced no records" (security-reviewer finding M1: an object read
    # failure on this path previously produced empty stdout,
    # indistinguishable from a genuinely empty/no-op commit, and was
    # silently treated as satisfied -- the same class of bug `--cc`'s empty
    # diff had for merges, now closed the same way on both paths since
    # there's only one path left).
    diff_file=$(mktemp) || return 1
    git diff-tree -r -z -m --no-commit-id --no-ext-diff --no-textconv --root "$commit" > "$diff_file"
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

# Inverse of is_tag_safe_to_delete's reachability outcome, for exactly the
# same branch-gone-or-merged population -- the manual-review candidate set
# git-cleanup's own SKILL.md already reports under "Needs Review (rebase-
# backup tag...)" but, until now, never gave any further help with. A tag
# whose branch still exists and isn't merged is excluded from BOTH sets (it's
# not a review candidate either -- the branch may still need this recovery
# point). Deliberately a separate function rather than inverting
# is_tag_safe_to_delete's own return value: that function's callers (--list,
# the delete loop) need "safe" to mean exactly what it already means, and a
# tri-state return would change its existing, already-reviewed contract for
# no benefit here -- a small sibling function with its own duplicated branch-
# status check (mirroring phase1-analysis.sh's own cross-referenced-comment
# precedent for tolerated duplication) is the lower-risk shape.
is_tag_needs_review() {
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
        return 1
      fi
      if is_tag_content_reachable "$tag"; then
        return 1
      fi
      return 0
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

# Returns 0 (a still-valid "keep" decision exists -- suppress this
# candidate from the review offer) only if $DECISIONS_FILE has a "keep"
# entry for "tag:$1" whose recorded item_sha AND default_branch_sha both
# still exactly match the current values passed in ($2, $3); returns 1 for
# no decision, a decision for a different (stale) state, or a missing/
# unreadable/malformed file. Read-only. $1 is always this script's own
# internal loop variable here, never text a caller composed into a command
# -- jq's `--arg` is pure string data regardless, but that property alone
# doesn't protect against the calling shell reinterpreting metacharacters
# in a name typed directly into command text (see DECISIONS_FILE's own
# comment above).
decision_is_valid_keep() {
  local tag="$1" current_item_sha="$2" current_default_sha="$3"
  [ -f "$DECISIONS_FILE" ] || return 1
  local decision recorded_item recorded_default
  decision=$(jq -r --arg k "tag:$tag" '.decisions[$k].decision // empty' "$DECISIONS_FILE" 2>/dev/null) || return 1
  [ "$decision" = "keep" ] || return 1
  recorded_item=$(jq -r --arg k "tag:$tag" '.decisions[$k].item_sha // empty' "$DECISIONS_FILE" 2>/dev/null) || return 1
  recorded_default=$(jq -r --arg k "tag:$tag" '.decisions[$k].default_branch_sha // empty' "$DECISIONS_FILE" 2>/dev/null) || return 1
  [ "$recorded_item" = "$current_item_sha" ] && [ "$recorded_default" = "$current_default_sha" ]
}

# Refuses --diff/--force/--keep outright unless the caller's supplied token
# matches the CURRENT value already read from $REVIEW_SNAPSHOT -- takes
# that value as an argument rather than opening the file itself (Codex
# cross-model-review finding, PR #322 round 3, Critical: an earlier version
# of this function opened the file independently, which meant every caller
# still performed TWO SEPARATE opens -- one here for validation, a second,
# later one in the caller's own triple-parsing loop. Live-reproduced: a
# third --list-review landing in the gap between those two opens replaced
# the snapshot after this function's own read had already validated the OLD
# token against the OLD content, so the caller's later, separate open read
# the NEW (already-replaced) content instead -- an old token for tag A
# force-deleted tag B). Embedding the generation token inside the snapshot
# file (this constant's own definition above) only closes the race if
# validation and parsing share the SAME open file description throughout a
# single invocation -- every caller below now opens $REVIEW_SNAPSHOT exactly
# ONCE via `exec {fd}< "$REVIEW_SNAPSHOT"`, reads the embedded generation
# field from that fd, passes it here, and continues reading the tag/oid/dsha
# triples from that SAME fd afterward. A POSIX rename (the `mv` that
# publishes a fresh snapshot) only repoints the path to a new inode -- an
# already-open file descriptor keeps reading the ORIGINAL inode's content
# regardless of what the path now points to (live-verified on this exact
# environment: an fd opened before a `mktemp`+`mv` replacement kept reading
# the pre-replacement bytes after the replacement completed) -- so a
# concurrent --list-review can never again invalidate a read that's already
# in progress, only one that hasn't started yet. A missing/unreadable
# snapshot (no --list-review has ever run) is treated the same as a
# mismatch: fail closed, never assume "no file yet" means "anything goes."
require_generation_token() {
  local supplied="$1" current="$2"
  if [ -z "$current" ] || [ "$supplied" != "$current" ]; then
    echo "Error: the review snapshot has changed since you ran --list-review (no matching generation) -- run --list-review again and start this candidate's review over, since a previously-shown index no longer reliably maps to the tag you reviewed" >&2
    exit 1
  fi
}

# Emits tag\0oid\0default_branch_sha\0 triples, not just tag\0 -- unlike
# $SNAPSHOT (list_deletable), this snapshot's whole reason to exist is to
# survive across a human reading --diff's evidence and later deciding to
# --force/--keep, a window with no bound on how long a human takes to
# decide. Recording each tag's oid AND $default_branch's oid AT THIS MOMENT
# lets --force/--keep refuse if EITHER moved at any point since -- not just
# during their own near-instantaneous execution (which is all a freshly
# re-resolved oid could ever detect), and not just the tag's own oid
# (security-reviewer finding M2: without pinning $default_branch too, a
# force-push or rewind of the default branch between --diff and the actual
# decision could invalidate evidence the human already reviewed with no way
# to detect it). Also drops any candidate with a still-valid "keep" decision
# already recorded (folding what would otherwise be a separate caller-side
# filtering step into this one script call -- security-reviewer finding M1:
# this keeps the index a caller sees always identical to the snapshot's own
# row numbering, with no separate renumbering step to get wrong).
list_review() {
  local default_sha
  default_sha=$(git rev-parse "$default_branch" 2>/dev/null) || return 0
  for tag in $(git tag -l '*-rebase-backup-*'); do
    if is_tag_needs_review "$tag"; then
      local item_sha
      # `|| continue` (not a bare assignment) -- security-reviewer/Codex
      # cross-model-review finding (F1): under this script's own
      # `set -euo pipefail`, a plain `var=$(cmd)` assignment with no `||`
      # fallback triggers immediate script exit the instant `cmd` fails,
      # BEFORE any check afterward can run -- live-verified. A tag deleted
      # in the narrow window between the `git tag -l` enumeration above and
      # this resolution would otherwise kill the entire --list-review run
      # silently, not just skip that one tag. `continue` (skip this tag,
      # keep processing the rest) is the correct behavior here, not a
      # decision-file lookup against an empty oid.
      item_sha=$(git rev-parse "refs/tags/$tag" 2>/dev/null) || continue
      if decision_is_valid_keep "$tag" "$item_sha" "$default_sha"; then
        printf 'Suppressed (previously reviewed and kept, no change since): %q\n' "$tag" >&2
        continue
      fi
      printf '%s\0%s\0%s\0' "$tag" "$item_sha" "$default_sha"
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

if [ "${1:-}" = "--list-review" ]; then
  # Generation token + tag/oid/dsha triples written to a TEMP file first,
  # then moved into place with a single atomic `mv` -- Codex cross-model-
  # review finding (PR #322 round 2, Critical): writing the snapshot and its
  # generation as two SEPARATE files/writes left a real window where an
  # interruption between them could leave an OLD generation token matching
  # NEW (already-replaced) snapshot content -- live-verified by replaying
  # exactly that interrupted-write sequence. A single file, single `mv`, has
  # no such window: either the whole update lands, or none of it does.
  generation="$(date -u +%Y%m%dT%H%M%S)-$$-$RANDOM-$RANDOM"
  review_tmp=$(mktemp "$(dirname "$REVIEW_SNAPSHOT")/.delete-rebase-backup-tags.review-snapshot.XXXXXX") || {
    echo "Error: could not create a temp file for the review snapshot" >&2
    exit 1
  }
  { printf '%s\0' "$generation"; list_review; } > "$review_tmp"
  mv "$review_tmp" "$REVIEW_SNAPSHOT"
  printf '# Generation: %s -- pass this back via --generation on --diff/--force/--keep\n' "$generation"
  i=0
  # One redirection on this whole block, not per-`read` -- the leading
  # `read` consumes the embedded generation field first, and the `while`
  # loop's own reads continue from the SAME stream position for the
  # tag/oid/dsha triples that follow it, rather than re-reading from the
  # file's start.
  {
    IFS= read -r -d '' _gen
    while IFS= read -r -d '' tag && IFS= read -r -d '' _oid && IFS= read -r -d '' _dsha; do
      i=$((i + 1))
      printf '%d\t%q\n' "$i" "$tag"
    done
  } < "$REVIEW_SNAPSHOT"
  exit 0
fi

# Read-only evidence for one manual-review candidate: the tag's own unique
# commits (mb..oid) plus a full tree diff between $default_branch's current
# state and the tag's own recorded oid -- deliberately the tag's WHOLE diff
# against $default_branch, not just the specific (path, commit) pairs that
# failed is_tag_content_reachable's internal per-commit walk. A human
# reviewing "is there real content here that would be lost" is better served
# by seeing everything the tag differs on than by having this reproduce the
# checker's own internal reasoning -- and it needs no new information beyond
# what --list-review's snapshot already gives an index into. Diffs against
# the snapshot's RECORDED oid, not a fresh "refs/tags/$tag" lookup -- so what
# this shows is always exactly what --force (below) would delete, even if
# the tag ref itself moved in between. Never destructive; safe to run any
# number of times against the same snapshot.
#
# The `git diff` call's exit status is checked explicitly and its stderr is
# captured, not suppressed -- security-reviewer finding C1: an empty diff is
# the POSITIVE signal in normal operation (tag's tree matches $default_branch,
# nothing lost by deleting), so a failed diff that ALSO produces empty stdout
# is indistinguishable from "safe to delete" unless the exit status is
# actually checked. Without this, a human could see blank evidence and
# approve a delete based on a broken check rather than a genuine match.
if [ "${1:-}" = "--diff" ]; then
  shift
  if [ "${1:-}" != "--generation" ] || [ -z "${2:-}" ]; then
    echo "Usage: $0 --diff --generation <token> <index>" >&2
    exit 2
  fi
  generation_arg="$2"
  shift 2
  idx="${1:-}"
  if ! [[ "$idx" =~ ^[0-9]+$ ]]; then
    echo "Error: index '$idx' is not a positive integer" >&2
    exit 2
  fi
  if [ ! -f "$REVIEW_SNAPSHOT" ]; then
    echo "Error: no review candidate list found -- run --list-review first" >&2
    exit 2
  fi
  # ONE open of $REVIEW_SNAPSHOT for both validation and parsing -- see
  # require_generation_token's own comment above for the race this closes
  # (two separate opens let a concurrent --list-review replace the file in
  # the gap between them). The leading read consumes the embedded
  # generation field; every read after it continues from the SAME open file
  # description, immune to any later replacement of the path.
  exec {snap_fd}< "$REVIEW_SNAPSHOT"
  current_gen=""
  IFS= read -r -d '' -u "$snap_fd" current_gen
  require_generation_token "$generation_arg" "$current_gen"
  tag="" oid="" dsha=""
  i=0
  while IFS= read -r -d '' -u "$snap_fd" t && IFS= read -r -d '' -u "$snap_fd" o && IFS= read -r -d '' -u "$snap_fd" d; do
    i=$((i + 1))
    if [ "$i" = "$idx" ]; then
      tag="$t"
      oid="$o"
      dsha="$d"
    fi
  done
  exec {snap_fd}<&-
  if [ -z "$tag" ]; then
    echo "Error: index '$idx' is out of range -- run --list-review again and retry" >&2
    exit 1
  fi
  printf '=== %q (oid %s) ===\n' "$tag" "$oid"
  # $dsha (the snapshot's own recorded $default_branch oid), not a fresh
  # `$default_branch` resolution -- Codex/CodeRabbit cross-model-review
  # finding (PR #322 round 1): re-resolving current $default_branch here
  # meant the SAME --diff call against the SAME unchanged snapshot could
  # show DIFFERENT evidence depending only on how much time passed since
  # --list-review -- live-verified: an identical `--diff 1` call, run again
  # after $default_branch advanced with no new --list-review in between,
  # produced a different diff (a rename-detected match instead of the
  # original new-file diff) for the exact same recorded candidate. Using
  # $dsha instead means this command is reproducible against a given
  # snapshot -- exactly what --force/--keep below already pin their own
  # atomic compare-and-delete to, so the evidence a human reviews here is
  # now guaranteed to be the SAME state those commands actually validate
  # against, not just usually the same.
  mb=$(git merge-base -- "$oid" "$dsha" 2>/dev/null) || mb=""
  if [ -n "$mb" ]; then
    # `-p` (each commit's actual patch), not `--oneline` (subjects only) --
    # Codex cross-model-review finding (PR #322 round 3, P1): the caution
    # note below this block tells the reviewer to "review each unique
    # commit's own diff above, not just its one-line subject" -- but with
    # `--oneline`, no such diff was ever printed for the reviewer to look
    # at, only the subjects. Live-reproduced with commits titled only "one"
    # and "two": a string unique to the first commit (later reverted by the
    # second, so absent from the final tree-content diff below) never
    # appeared anywhere in `--diff`'s output at all -- a human could approve
    # deleting the tag that was its only remaining reference without ever
    # seeing the content actually at risk. `--no-ext-diff --no-textconv`
    # match the tree-content diff call below, for the same reason.
    echo "--- unique commits ($mb..$oid) ---"
    git log -p --no-ext-diff --no-textconv "${mb}..${oid}" -- 2>/dev/null
  else
    # Codex cross-model-review finding (F1, round 3): a failed merge-base
    # (no common ancestor -- an orphan branch, a grafted/shallow boundary,
    # or a `merge --allow-unrelated-histories` root) was silently skipping
    # this whole section with no explanation, then falling straight through
    # to the tree-content diff below. If that diff then happened to come
    # back empty (the two trees are byte-identical despite sharing no
    # history at all -- live-reproduced with a real orphan-branch tag), the
    # only thing the human reviewer saw was a clean, reassuring "no
    # differences" message, with nothing to signal that ancestry itself
    # could never be established for this candidate -- exactly the kind of
    # anomalous, unrelated-history case this script already treats with
    # extra scrutiny elsewhere (the `--root` handling for parentless
    # commits, a few lines up). The tree-content diff below is still valid,
    # accurate evidence either way (a tree comparison needs no common
    # ancestor), but the reviewer needs to know this warning applies before
    # trusting it.
    echo "Warning: no common ancestor found with $default_branch -- unique-commit history cannot be shown for this candidate (orphan branch, grafted/shallow history, or an unrelated-histories merge root)" >&2
  fi
  echo "--- content diff: $default_branch @ ${dsha:0:12} (as recorded by --list-review) vs $tag (recorded oid $oid) ---"
  # `&& diff_rc=0 || diff_rc=$?`, not a bare assignment followed by
  # `diff_rc=$?` on the next line -- security-reviewer/Codex cross-model-
  # review finding (F1, same root cause as list_review's item_sha above):
  # under `set -euo pipefail`, a plain `diff_out=$(git diff ...)` with no
  # `||` fallback triggers immediate script exit the instant `git diff`
  # fails, BEFORE the very next line (`diff_rc=$?`) can ever run --
  # live-verified: this made the C1 fix's own error-status check dead code,
  # unreachable, exactly the same class of bug it was meant to guard
  # against. The `&&`/`||` compound's own exit status is always 0 (the
  # assignment branch that actually runs always succeeds), so `set -e`
  # never fires on this line regardless of whether `git diff` itself
  # succeeded or failed -- `$diff_rc` still ends up holding the real exit
  # code either way.
  diff_out=$(git diff --no-ext-diff --no-textconv "$dsha" "$oid" -- 2>&1) && diff_rc=0 || diff_rc=$?
  if [ "$diff_rc" -ne 0 ]; then
    echo "Error: could not produce evidence for this candidate -- do NOT treat this as \"no content differs\"" >&2
    printf '%s\n' "$diff_out" >&2
    exit 1
  fi
  if [ -z "$diff_out" ]; then
    if [ -z "$mb" ]; then
      echo "(no differences -- this candidate's tree matches $default_branch's recorded tree exactly, but see the no-common-ancestor warning above before treating that as sufficient evidence)"
    else
      echo "(no differences -- this candidate's tree matches $default_branch's recorded tree exactly)"
      # General caution, not just the self-reverted-content case Codex named
      # specifically (cross-model-review finding, PR #322 round 1): this
      # candidate is only in --list-review at all because the AUTOMATED
      # reachability check already failed to verify it (is_tag_needs_review
      # returned true) -- so a matching final tree here can only mean the
      # automated per-commit walk found something it couldn't confirm was
      # genuinely reflected on $default_branch, yet the end states happen to
      # coincide anyway. That can happen for more than one reason (content
      # reorganized into differently-grouped commits -- issue #317's own
      # still-open case -- or content added then reverted within this tag's
      # own history, live-verified with the exact
      # scenario_self_reverted_unique_content_fails_closed fixture: the
      # unique-commit list above DOES include the add/revert pair, but a
      # human skimming one-line commit subjects, not full diffs, could
      # easily miss that on their own) -- worth surfacing explicitly rather
      # than trusting the reviewer to always read every commit's own diff.
      echo "Note: this candidate reached manual review because the automated check could not verify it -- an exact tree match despite that can mean content was reorganized across differently-grouped commits, or added then later reverted within this tag's own history; review each unique commit's own diff above, not just its one-line subject, before treating an empty diff as equivalent to \"nothing unique happened here\"" >&2
    fi
  else
    printf '%s\n' "$diff_out"
  fi
  exit 0
fi

# Force-delete one or more manual-review candidates -- the deliberate bypass
# of is_tag_needs_review/is_tag_safe_to_delete this whole mode exists for.
# Every tag reachable via $REVIEW_SNAPSHOT already FAILED the automated
# reachability check (that's the only way it got into this snapshot in the
# first place), so re-running that check here would always refuse and this
# mode would never do anything. This is the actual security-relevant surface
# added by this feature -- calling it is a human decision made outside this
# script entirely (git-cleanup's own guided-review phase requires two
# separate confirmations, having shown --diff's evidence, before ever
# reaching this call); the script's own job is only to execute that decision
# without introducing a NEW way to lose data beyond what the human already
# saw.
#
# The safety net here is deliberately NOT "re-resolve the tag's current oid
# and delete against that" -- that would only ever protect against a move
# happening during --force's own near-instantaneous execution (essentially
# no window at all), and would silently delete whatever the tag CURRENTLY
# points to even if it moved entirely between --diff (what the human
# actually reviewed) and this call, with no way to detect it (found while
# writing this feature's own regression tests: scenario
# scenario_force_refuses_on_toctou_move failed against an earlier version of
# this code that re-resolved fresh, because there is no time window within a
# single invocation for a "moved since I looked" race to manifest -- the
# race that matters here spans the whole human-decision-making gap between
# --list-review/--diff and --force, which can be arbitrarily long). Instead,
# compare against $REVIEW_SNAPSHOT's own RECORDED tag oid AND recorded
# $default_branch oid (captured when --list-review ran, the same values
# --diff's evidence was built from) -- if EITHER differs from the current
# value, refuse outright rather than deleting against evidence the human
# never actually saw (security-reviewer finding M2: pinning the tag's oid
# alone left the default branch itself free to move -- a rewind or
# force-push there between --diff and the decision would silently
# invalidate the reviewed evidence with nothing to detect it).
#
# Never removes $REVIEW_SNAPSHOT on completion (security-reviewer finding
# C2): guided-manual-review.md's own procedure reviews items ONE AT A TIME,
# and deleting the snapshot after the first "Delete now" would renumber
# every remaining candidate on the next --list-review, reopening the exact
# "same index, different tag" race this snapshot mechanism exists to
# prevent -- on the one path where the reachability check is deliberately
# skipped. Re-running --force against an already-consumed index already
# fails safely on its own (the tag no longer resolves), so there is no
# correctness reason to clear the snapshot proactively; only a fresh
# --list-review ever replaces it.
if [ "${1:-}" = "--force" ]; then
  shift
  if [ "${1:-}" != "--generation" ] || [ -z "${2:-}" ]; then
    echo "Usage: $0 --force --generation <token> <index> [index...]" >&2
    exit 2
  fi
  generation_arg="$2"
  shift 2
  if [ "$#" -eq 0 ]; then
    echo "Usage: $0 --force --generation <token> <index> [index...]" >&2
    exit 2
  fi
  if [ ! -f "$REVIEW_SNAPSHOT" ]; then
    echo "Error: no review candidate list found -- run --list-review first" >&2
    exit 2
  fi
  declare -A force_wanted
  for arg in "$@"; do
    if ! [[ "$arg" =~ ^[0-9]+$ ]]; then
      echo "Error: index '$arg' is not a positive integer" >&2
      exit 2
    fi
    force_wanted["$arg"]=1
  done
  force_matched_tags=()
  force_matched_oids=()
  force_matched_dshas=()
  i=0
  # ONE open of $REVIEW_SNAPSHOT for both validation and parsing -- see
  # require_generation_token's own comment above for the race this closes.
  exec {snap_fd}< "$REVIEW_SNAPSHOT"
  current_gen=""
  IFS= read -r -d '' -u "$snap_fd" current_gen
  require_generation_token "$generation_arg" "$current_gen"
  while IFS= read -r -d '' -u "$snap_fd" tag && IFS= read -r -d '' -u "$snap_fd" oid && IFS= read -r -d '' -u "$snap_fd" dsha; do
    i=$((i + 1))
    if [ -n "${force_wanted[$i]:-}" ]; then
      force_matched_tags+=("$tag")
      force_matched_oids+=("$oid")
      force_matched_dshas+=("$dsha")
    fi
  done
  exec {snap_fd}<&-
  if [ "${#force_matched_tags[@]}" -ne "${#force_wanted[@]}" ]; then
    echo "Error: one or more requested indices are out of range -- run --list-review again and retry" >&2
    exit 1
  fi
  force_failed=0
  for m in "${!force_matched_tags[@]}"; do
    tag="${force_matched_tags[$m]}"
    expected_oid="${force_matched_oids[$m]}"
    expected_dsha="${force_matched_dshas[$m]}"
    # `|| current_oid=""` / `|| current_dsha=""` -- security-reviewer/Codex
    # cross-model-review finding (F1): under `set -euo pipefail`, a bare
    # `var=$(cmd)` assignment with no `||` fallback triggers immediate
    # script exit the instant `cmd` fails, before the `[ -z "$current_oid" ]`
    # check below can ever run -- live-verified: a tag deleted concurrently
    # after --list-review (or an unresolvable $default_branch) silently
    # killed the whole --force invocation instead of skipping just that one
    # index and reporting "Skipped", which also stopped any LATER index in
    # the same multi-index --force call from ever being processed.
    current_oid=$(git rev-parse "refs/tags/$tag" 2>/dev/null) || current_oid=""
    current_dsha=$(git rev-parse "$default_branch" 2>/dev/null) || current_dsha=""
    if [ -z "$current_oid" ]; then
      echo "Skipped '$tag': could not resolve its current object id" >&2
      force_failed=1
      continue
    fi
    if [ "$current_oid" != "$expected_oid" ]; then
      echo "Skipped '$tag': moved since --list-review (was $expected_oid, now $current_oid) -- run --list-review and --diff again, and confirm before forcing" >&2
      force_failed=1
      continue
    fi
    if [ -z "$current_dsha" ] || [ "$current_dsha" != "$expected_dsha" ]; then
      echo "Skipped '$tag': $default_branch advanced since --list-review (was $expected_dsha, now ${current_dsha:-unresolvable}) -- the evidence you reviewed may be stale; run --list-review and --diff again" >&2
      force_failed=1
      continue
    fi
    # The checks above and the delete below are still two SEPARATE steps up
    # to this point (a fast, friendly rejection for the common case of
    # something having already moved before --force was even invoked) --
    # but the ACTUAL delete now verifies $default_branch's oid again, in the
    # SAME atomic transaction as the delete itself, closing the narrower gap
    # between "the checks above passed" and "the delete below actually
    # runs" -- Codex cross-model-review finding (PR #322 round 3, P1): only
    # the tag's own oid was atomically protected by the old
    # `git update-ref -d <ref> <old-oid>` call; $default_branch's oid was
    # checked sequentially beforehand with no atomic binding to the delete
    # itself, so a $default_branch rewind landing in that specific gap could
    # still let the delete through despite having already "failed" the
    # check moments earlier. Live-reproduced: rewinding $default_branch
    # immediately before the delete call still let it succeed. `git
    # update-ref --stdin` verifies one ref and deletes another as ONE
    # atomic transaction -- if EITHER ref no longer matches, the WHOLE
    # transaction (including the delete) is refused; live-verified against
    # a real crafted race (git's own "cannot lock ref ...: is at X but
    # expected Y", exit 128, tag left untouched).
    default_branch_full_ref=$(git rev-parse --symbolic-full-name "$default_branch" 2>/dev/null) || default_branch_full_ref=""
    if [ -z "$default_branch_full_ref" ]; then
      echo "Error: failed to force-delete tag '$tag' -- could not resolve $default_branch's full ref name" >&2
      force_failed=1
      continue
    fi
    if printf 'verify %s %s\ndelete refs/tags/%s %s\n' "$default_branch_full_ref" "$expected_dsha" "$tag" "$expected_oid" | git update-ref --stdin; then
      :
    else
      echo "Error: failed to force-delete tag '$tag' -- $tag or $default_branch moved since verification, or another error occurred" >&2
      force_failed=1
    fi
  done
  exit "$force_failed"
fi

# Records a "keep, don't ask again" decision for one manual-review candidate
# by INDEX -- never a raw tag name (security-reviewer finding C3/M4): moving
# this read-modify-write entirely inside the script, keyed the same way
# --diff/--force already are, means the calling skill never needs to compose
# a jq/git command containing a literal tag name -- no prior mode of this
# script ever emitted one for a caller to safely capture into a variable in
# the first place, and Claude Code's Bash tool has no persistent shell state
# across separate calls to carry one even if it had. Same TOCTOU refusal as
# --force (tag oid AND $default_branch oid must both still match what
# --list-review recorded) -- keeping a tag based on evidence that's gone
# stale since the human reviewed it is exactly as wrong as force-deleting
# one would be. Never removes $REVIEW_SNAPSHOT, matching --force's own
# rationale above.
if [ "${1:-}" = "--keep" ]; then
  shift
  if [ "${1:-}" != "--generation" ] || [ -z "${2:-}" ]; then
    echo "Usage: $0 --keep --generation <token> <index>" >&2
    exit 2
  fi
  generation_arg="$2"
  shift 2
  idx="${1:-}"
  if ! [[ "$idx" =~ ^[0-9]+$ ]]; then
    echo "Error: index '$idx' is not a positive integer" >&2
    exit 2
  fi
  if [ ! -f "$REVIEW_SNAPSHOT" ]; then
    echo "Error: no review candidate list found -- run --list-review first" >&2
    exit 2
  fi
  # ONE open of $REVIEW_SNAPSHOT for both validation and parsing -- see
  # require_generation_token's own comment above for the race this closes.
  exec {snap_fd}< "$REVIEW_SNAPSHOT"
  current_gen=""
  IFS= read -r -d '' -u "$snap_fd" current_gen
  require_generation_token "$generation_arg" "$current_gen"
  tag="" oid="" dsha=""
  i=0
  while IFS= read -r -d '' -u "$snap_fd" t && IFS= read -r -d '' -u "$snap_fd" o && IFS= read -r -d '' -u "$snap_fd" d; do
    i=$((i + 1))
    if [ "$i" = "$idx" ]; then
      tag="$t"
      oid="$o"
      dsha="$d"
    fi
  done
  exec {snap_fd}<&-
  if [ -z "$tag" ]; then
    echo "Error: index '$idx' is out of range -- run --list-review again and retry" >&2
    exit 1
  fi
  # `|| current_oid=""` / `|| current_dsha=""` -- security-reviewer/Codex
  # cross-model-review finding (F1), same as --force's identical check
  # above: under `set -euo pipefail`, a bare `var=$(cmd)` assignment with
  # no `||` fallback triggers immediate script exit before the check below
  # can run, silently killing --keep instead of reporting the documented
  # "moved since --list-review" refusal.
  current_oid=$(git rev-parse "refs/tags/$tag" 2>/dev/null) || current_oid=""
  current_dsha=$(git rev-parse "$default_branch" 2>/dev/null) || current_dsha=""
  if [ -z "$current_oid" ] || [ "$current_oid" != "$oid" ]; then
    echo "Error: this candidate moved since --list-review -- run --list-review and --diff again, and confirm before keeping" >&2
    exit 1
  fi
  if [ -z "$current_dsha" ] || [ "$current_dsha" != "$dsha" ]; then
    echo "Error: $default_branch advanced since --list-review -- run --list-review and --diff again, and confirm before keeping" >&2
    exit 1
  fi
  # Protect $DECISIONS_FILE from an accidental `git add -A`/`git commit -a`
  # in whatever repo this script actually runs in -- Codex/CodeRabbit
  # cross-model-review finding (PR #322 round 1): this SOURCE repo's own
  # `.gitignore` (`**/*.local.*`) already covers it, but git-kit is a
  # DISTRIBUTED plugin -- a consumer repo that installs it has no such rule
  # of its own, and live-verifying with this machine's personal global
  # excludesfile neutralized (a true "foreign environment" simulation)
  # confirmed `git add -A` happily stages this file there. Writing to the
  # repo's own PER-REPO `info/exclude` (never shipped, never committed by
  # anyone) rather than a tracked `.gitignore` keeps the decision file at
  # its already-documented working-tree location (see this constant's own
  # definition above for why that placement is deliberate) while still
  # closing the gap for every repo this script ever runs in, not just this
  # one. Idempotent: only appended once, checked by an exact-line match.
  exclude_file="$(git rev-parse --git-path info/exclude)"
  exclude_pattern=".claude/git-cleanup-review-decisions.local.json"
  mkdir -p "$(dirname "$exclude_file")"
  if [ ! -f "$exclude_file" ] || ! grep -qxF "$exclude_pattern" "$exclude_file" 2>/dev/null; then
    printf '%s\n' "$exclude_pattern" >> "$exclude_file"
  fi
  mkdir -p "$(dirname "$DECISIONS_FILE")"
  if [ -f "$DECISIONS_FILE" ]; then
    existing_version=$(jq -r '.version // empty' "$DECISIONS_FILE" 2>/dev/null) || existing_version=""
    if [ -n "$existing_version" ] && [ "$existing_version" != "1" ]; then
      echo "Error: $DECISIONS_FILE has unrecognized version '$existing_version' -- refusing to overwrite" >&2
      exit 1
    fi
  else
    echo '{"version":1,"decisions":{}}' > "$DECISIONS_FILE"
  fi
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  tmp_file=$(mktemp "$(dirname "$DECISIONS_FILE")/.git-cleanup-review-decisions.XXXXXX") || {
    echo "Error: could not create a temp file for the decision write" >&2
    exit 1
  }
  if ! jq --arg k "tag:$tag" --arg sha "$oid" --arg dsha "$dsha" --arg ts "$ts" \
    '.version = 1 | .decisions[$k] = {"decision":"keep","item_sha":$sha,"default_branch_sha":$dsha,"decided_at":$ts}' \
    "$DECISIONS_FILE" > "$tmp_file"; then
    echo "Error: failed to update the decision file" >&2
    rm -f "$tmp_file"
    exit 1
  fi
  mv "$tmp_file" "$DECISIONS_FILE"
  printf 'Recorded: keep %q (as of %s) -- suppressed from future --list-review output unless this tag or %s moves\n' \
    "$tag" "$ts" "$default_branch"
  exit 0
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 --list | <index> [index...] | --list-review | --diff --generation <token> <index> | --force --generation <token> <index> [index...] | --keep --generation <token> <index>" >&2
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
  # `|| pre_check_oid=""` -- security-reviewer/Codex cross-model-review
  # finding (F1, pre-existing sibling instance): under `set -euo pipefail`,
  # a bare `pre_check_oid=$(git rev-parse ...)` with no `||` fallback
  # triggers immediate script exit the instant the tag no longer resolves
  # (e.g. already deleted by another process), before the very next line's
  # `[ -z "$pre_check_oid" ]` check -- the exact "Skipped" graceful-
  # degradation path below -- can ever run. Live-verified: this silently
  # killed the whole multi-tag delete loop on the first already-gone tag,
  # instead of skipping just that one and continuing with the rest, exactly
  # the partial-failure behavior this loop's own comments document as the
  # intended design.
  pre_check_oid=$(git rev-parse "refs/tags/$tag" 2>/dev/null) || pre_check_oid=""
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
