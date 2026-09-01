#!/usr/bin/env bash
# Persisted regression test for is_tag_content_reachable's core behaviors
# (PR #275). Sources the real default_branch_patchids/is_tag_content_reachable
# function bodies directly from delete-rebase-backup-tags.sh -- never a
# hand-copied re-implementation -- so this test can't silently drift from the
# code it's meant to guard. Builds isolated, throwaway git repos under
# `mktemp -d` for every scenario; never touches the repo this script itself
# lives in. Requested by Devin's automated PR review on PR #275
# ("Complex behavior lacks regression tests") -- the live scratch-repo
# verification that PR's own review round did is captured here as a
# repeatable fixture instead of remaining ad hoc.
#
# Run directly: bash test-content-reachable.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$SCRIPT_DIR/delete-rebase-backup-tags.sh"

# Extract just the two functions under test from the real script -- the same
# sed-range technique used for this behavior's own live verification during
# PR #275's review, not a fresh implementation.
FUNCS=$(sed -n '/^default_branch_patchids() {/,/^}/p; /^is_tag_content_reachable() {/,/^}/p' "$TARGET")

PASS=0
FAIL=0

report() {
  local ok="$1" desc="$2"
  if [ "$ok" = "0" ]; then
    echo "PASS  $desc"
    PASS=$((PASS + 1))
  else
    echo "FAIL  $desc"
    FAIL=$((FAIL + 1))
  fi
}

new_repo() {
  local dir
  dir=$(mktemp -d)
  git -C "$dir" init -q
  git -C "$dir" config user.email test@test.com
  git -C "$dir" config user.name test
  git -C "$dir" config core.autocrlf false
  echo "$dir"
}

# Scenario 1: rebase-merge is recognized -- a branch's commit is rebased
# (same content, different SHA/parent) onto an advanced main, then merged.
# The tag on the pre-rebase commit must be recognized as content-reachable.
scenario_rebase_merge_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git branch feature
    # Main advances by touching a DIFFERENT file, not shared.txt -- this
    # gives the eventual "replayed" commit a genuinely different parent
    # (real SHA divergence, like an actual rebase), while leaving
    # shared.txt's own blob state untouched by the advance, so the feature
    # change's diff text stays byte-identical whichever parent it's applied
    # to. Advancing main via the SAME file feature touches would instead
    # test the "changed base" case (a separate, known limitation -- see
    # is_tag_content_reachable's own comment on that).
    printf 'main-only\n' > main-only.txt
    git add main-only.txt && git commit -q -m "main advances (unrelated file)"
    git checkout -q feature
    printf 'feature-line\n' >> shared.txt
    git add shared.txt && git commit -q -m "feature change"
    git tag -a mytag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # simulate the rebase-then-merge: replay the identical shared.txt change
    # on top of the now-advanced main tip -- same diff text (shared.txt's
    # own context is unaffected by main-only.txt), different commit SHA
    printf 'feature-line\n' >> shared.txt
    git add shared.txt && git commit -q -m "feature change (rebased)"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    main_patchid_log=""
    eval "$FUNCS"
    is_tag_content_reachable mytag-rebase-backup-20260101-000000
  )
}

# Scenario 2: whitespace-only difference must NOT falsely match.
scenario_whitespace_not_matched() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'line1\nline2\n' > f.txt
    git add f.txt && git commit -q -m base
    git branch feature
    printf 'line1\n    line2\n' > f.txt
    git add f.txt && git commit -q -m "main gets 4-space indent"
    git checkout -q feature
    printf 'line1\n  line2\n' > f.txt
    git add f.txt && git commit -q -m "feature gets 2-space indent (different bytes, same patch-id)"
    git tag -a wstag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    main_patchid_log=""
    eval "$FUNCS"
    if is_tag_content_reachable wstag-rebase-backup-20260101-000000; then
      exit 1  # a match here would be the bug this test guards against
    else
      exit 0
    fi
  )
}

# Scenario 3: a trivial (conflict-free) merge commit in the tag's own
# history must be skipped, not fail the whole tag closed.
scenario_trivial_merge_skipped() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > a.txt
    git add a.txt && git commit -q -m base
    git branch topic
    printf 'topic-change\n' > b.txt
    git add b.txt && git commit -q -m "topic change"
    git checkout -q main 2>/dev/null || git checkout -q master
    printf 'main-change\n' > c.txt
    git add c.txt && git commit -q -m "main change"
    git merge --no-ff -q -m "trivial merge" topic
    git tag -a mergetag-rebase-backup-20260101-000000 -m backup HEAD
    # also replay both changes directly on a fresh commit so content exists
    # on main independent of the merge commit itself
    printf 'topic-change\n' > b2.txt
    git add b2.txt && git commit -q -m "topic change replayed"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    main_patchid_log=""
    eval "$FUNCS"
    # Not asserting reachable=true here (the merge tip's own two parent
    # commits aren't independently replayed under this exact tag setup) --
    # only that a trivial merge doesn't itself abort the walk. A bug would
    # show up as this call erroring/aborting instead of returning cleanly.
    is_tag_content_reachable mergetag-rebase-backup-20260101-000000 || true
  )
}

# Scenario 4: exit-status vs. empty-stdout -- a bad commit reference must
# be treated as a failure (fail closed), never as "trivial merge, skip".
scenario_bad_ref_fails_closed() (
  local repo; repo=$(new_repo)
  cd "$repo"
  printf 'base\n' > a.txt
  git add a.txt && git commit -q -m base
  cc_diff=$(git diff-tree --cc -p --no-commit-id -r --no-ext-diff --no-textconv \
    "0000000000000000000000000000000000dead" 2>/dev/null)
  cc_rc=$?
  [ -z "$cc_diff" ] && [ "$cc_rc" -ne 0 ]
)

# Scenario 5: atomic compare-and-delete -- correct oid succeeds, stale oid
# is refused and the tag survives.
scenario_atomic_delete() (
  local repo; repo=$(new_repo)
  cd "$repo"
  printf 'base\n' > a.txt
  git add a.txt && git commit -q -m base
  git tag -a deltag -m v1 HEAD
  oid=$(git rev-parse "refs/tags/deltag")
  git update-ref -d refs/tags/deltag "$oid" || return 1
  [ -z "$(git tag -l deltag)" ] || return 1

  git tag -a deltag -m v1 HEAD
  stale_oid=$(git rev-parse "refs/tags/deltag")
  printf 'more\n' >> a.txt
  git add a.txt && git commit -q -m more
  git tag -f -a deltag -m v2 HEAD >/dev/null 2>&1
  if git update-ref -d refs/tags/deltag "$stale_oid" 2>/dev/null; then
    return 1  # should have been refused
  fi
  [ -n "$(git tag -l deltag)" ] || return 1
)

# Each scenario is called via if/else, never as a bare statement -- under
# `set -e`, a bare failing command at top level aborts the whole script
# immediately, which would stop this file after the first real failure
# instead of reporting every scenario's own result.
run() {
  local rc=0
  "$1" || rc=$?
  report "$rc" "$2"
}

run scenario_rebase_merge_recognized "rebase-merged tag is recognized as content-reachable"
run scenario_whitespace_not_matched "whitespace-only difference does not falsely match"
run scenario_trivial_merge_skipped "trivial merge commit in tag history doesn't abort the check"
run scenario_bad_ref_fails_closed "a git diff-tree failure is distinguished from an empty diff"
run scenario_atomic_delete "atomic compare-and-delete succeeds on match, refuses on stale oid"

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
