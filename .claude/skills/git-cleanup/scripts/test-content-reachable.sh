#!/usr/bin/env bash
# Persisted regression test for is_tag_content_reachable's core behaviors
# (PR #275, redesigned to per-path blob-history matching per the follow-up
# fix disclosed in PR #275's own accepted-limitation comment). Sources the
# real is_path_blob_reachable/is_tag_content_reachable function bodies
# directly from delete-rebase-backup-tags.sh -- never a hand-copied
# re-implementation -- so this test can't silently drift from the code it's
# meant to guard. Builds isolated, throwaway git repos under
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

# Extract just the functions under test from the real script -- the same
# sed-range technique used for this behavior's own live verification during
# PR #275's review, not a fresh implementation.
FUNCS=$(sed -n '/^is_path_blob_reachable() {/,/^}/p; /^check_diff_records() {/,/^}/p; /^is_tag_content_reachable() {/,/^}/p' "$TARGET")

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
    eval "$FUNCS"
    if is_tag_content_reachable wstag-rebase-backup-20260101-000000; then
      exit 1  # a match here would be the bug this test guards against
    else
      exit 0
    fi
  )
}

# Scenario 3: a trivial (conflict-free) merge commit in the tag's own
# history must be skipped, not fail the whole tag closed -- and the overall
# tag must still come back reachable once every OTHER commit's content is
# genuinely matched on the default branch. Asserts a deterministic result
# rather than swallowing every outcome with `|| true`, which would let this
# scenario pass regardless of what is_tag_content_reachable actually
# returns (Devin automated PR review finding, PR #275 round 2).
scenario_trivial_merge_skipped() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > a.txt
    git add a.txt && git commit -q -m base
    # Both feature branches, and the merge combining them, stay off main
    # entirely -- so raw-SHA ancestry genuinely fails and this scenario
    # actually exercises the content fallback, not the fast ancestry path.
    git branch feature1
    git branch feature2
    git checkout -q feature1
    printf 'feature1-line\n' > d.txt
    git add d.txt && git commit -q -m "feature1 change"
    git checkout -q feature2
    printf 'feature2-line\n' > e.txt
    git add e.txt && git commit -q -m "feature2 change"
    git checkout -q feature1
    git merge --no-ff -q -m "trivial merge of feature2 into feature1" feature2
    git tag -a mergetag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature1 feature2 >/dev/null
    # Replay each feature commit's content individually on main, same file
    # paths -- the merge commit itself needs no replay (trivial, empty
    # --cc diff, should be skipped rather than requiring a match).
    printf 'feature1-line\n' > d.txt
    git add d.txt && git commit -q -m "feature1 change (landed on main)"
    printf 'feature2-line\n' > e.txt
    git add e.txt && git commit -q -m "feature2 change (landed on main)"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    is_tag_content_reachable mergetag-rebase-backup-20260101-000000
  )
}

# Scenario 4: exit-status vs. empty-stdout -- a `git diff-tree` failure on a
# merge commit must be treated as a failure (fail closed), never as
# "trivial merge, skip". Exercises the real is_tag_content_reachable, not
# git diff-tree standalone -- a regression that dropped the production
# exit-status check would go undetected by a test that only re-implements
# those same two lines outside the function under test (Devin automated PR
# review finding, PR #275 round 2). Constructs a genuine failure by
# deleting a merge commit's own second-parent's object: `git rev-parse
# --verify --quiet "$commit^2"` still succeeds (it only reads the commit's
# own header text, correctly detecting a merge), while `git diff-tree --cc`
# genuinely fails with "fatal: unable to read tree" -- live-verified this
# combination is real, not simulated.
#
# Every non-merge commit's content IS also replayed on main (unlike a
# scenario that only wants to test the merge in isolation) -- this is
# deliberate, not an oversight: without it, a broken version with the
# exit-status check removed would still return 1 (fail closed) anyway, for
# the unrelated reason that feature1/feature2's own content was never
# independently found on main, completely masking whether the exit-status
# regression itself was ever detected. With their content replayed, a
# correct implementation returns 1 solely because of the corrupted merge;
# a version with the exit-status check dropped would instead treat the
# corrupted merge as trivial, continue past it, find feature1/feature2 both
# genuinely matched, and incorrectly return 0 -- live-verified this
# distinction actually catches the regression (see the sanity check this
# fix's own PR review round performed before landing).
scenario_bad_ref_fails_closed() (
  local repo; repo=$(new_repo)
  cd "$repo"
  printf 'base\n' > a.txt
  git add a.txt && git commit -q -m base
  # The merge stays entirely off main -- built and tagged on a throwaway
  # branch, never merged in -- so merge-base(tag, main) resolves to "base",
  # not to the merge commit itself. Building the merge directly on main
  # would make the tag and main's tip the same commit, collapsing
  # tag_commits to empty and never reaching the merge-detection logic at
  # all -- a real construction bug caught while writing this fix.
  git checkout -q -b feature1
  printf 'feature1\n' > b.txt
  git add b.txt && git commit -q -m feature1
  git checkout -q -b feature2 main 2>/dev/null || git checkout -q -b feature2 master
  printf 'feature2\n' > c.txt
  git add c.txt && git commit -q -m feature2
  git checkout -q feature1
  git merge --no-ff -q -m merge feature2
  merge_sha=$(git rev-parse HEAD)
  git tag -a badreftag-rebase-backup-20260101-000000 -m backup "$merge_sha"
  git checkout -q main 2>/dev/null || git checkout -q master
  git branch -D feature1 feature2 >/dev/null
  # A distinguishing file FIRST, before either replay -- not appended
  # afterward. Two earlier attempts placed this commit AFTER the replays
  # and still hit the same collision: even with main's FINAL tree made
  # distinct, the INTERMEDIATE tree right after replaying just feature1+
  # feature2 (a.txt+b.txt+c.txt, nothing else yet) is still byte-for-byte
  # identical to the merge commit's own resulting tree, and git's
  # content-addressed store deduplicates identical trees into the SAME
  # object regardless of which commit reaches that state -- deleting "the
  # merge's own tree" then also deletes the tree that intermediate main
  # commit points to, breaking default_branch_patchids' own `git log -p
  # main` walk when it reaches that specific commit. Present from the very
  # first commit onward, z.txt keeps every state on main's own history
  # distinct from anything the merge commit (which never touches z.txt at
  # all) could ever produce.
  printf 'distinguishing\n' > z.txt
  git add z.txt && git commit -q -m "keep every main commit's tree distinct from the merge's own tree"
  # Replay both feature commits' content on main, same file paths -- so a
  # broken (exit-status-dropped) implementation would find them genuinely
  # matched and incorrectly succeed, rather than coincidentally failing
  # closed for an unrelated reason.
  printf 'feature1\n' > b.txt
  git add b.txt && git commit -q -m "feature1 (landed on main)"
  printf 'feature2\n' > c.txt
  git add c.txt && git commit -q -m "feature2 (landed on main)"
  # Delete the MERGE COMMIT's own tree object -- specifically not either
  # parent's tree/commit object. Two earlier attempts at this corruption
  # both failed to actually isolate the target, caught only by deliberately
  # reintroducing the original exit-status bug and confirming this scenario
  # still passed against it (a false PASS -- exactly the failure mode this
  # sanity check exists to catch): deleting parent2's own COMMIT object
  # broke `git merge-base`'s graph walk itself (needs to traverse parent2's
  # history for ancestry), making is_tag_content_reachable return 1 at its
  # very first line regardless of the fix under test; deleting parent2's
  # TREE object instead left merge-base intact, but that same tree is ALSO
  # what feature2's own standalone (non-merge) diff-tree walk needs later in
  # this same loop, corrupting it too and producing a return 1 for an
  # unrelated reason. The merge's OWN tree is needed only by `--cc` (which
  # compares it against both parents) -- live-verified: merge-base stays
  # intact, `git diff-tree --cc` on the merge fails cleanly ("fatal: unable
  # to read tree"), and both feature1's and feature2's own standalone diffs
  # are completely unaffected, since neither reads the merge's own tree.
  merge_tree=$(git rev-parse "${merge_sha}^{tree}")
  rm -f ".git/objects/${merge_tree:0:2}/${merge_tree:2}"

  default_branch=main
  git show-ref --verify --quiet refs/heads/main || default_branch=master
  eval "$FUNCS"
  if is_tag_content_reachable badreftag-rebase-backup-20260101-000000; then
    return 1  # a corrupted merge must never be read as "safe to skip"
  else
    return 0
  fi
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

# Scenario 6: content genuinely landed on $default_branch, but reorganized
# into a DIFFERENT commit grouping than the tag's own commit -- the case
# PR #275's exact-diff-text approach disclosed as a known, accepted
# limitation (a whole-commit diff match can never see this) and this
# redesign specifically targets. The tag's one commit adds two files
# together; $default_branch adds them via two SEPARATE commits instead.
# Live-verified against this repo's own real
# feat/pr-ci-governance-rebase-backup-20260907-210042 tag before writing
# this fixture (see is_path_blob_reachable's own comment).
scenario_reorganized_commit_grouping_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > base.txt
    git add base.txt && git commit -q -m base
    git branch feature
    git checkout -q feature
    printf 'file-a\n' > file-a.txt
    printf 'file-b\n' > file-b.txt
    git add file-a.txt file-b.txt
    git commit -q -m "feature: add both files together"
    git tag -a regroup-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # Same two files, same content, but landed via two SEPARATE commits --
    # a whole-commit diff match can never find either half this way.
    printf 'file-a\n' > file-a.txt
    git add file-a.txt && git commit -q -m "file-a lands on its own"
    printf 'file-b\n' > file-b.txt
    git add file-b.txt && git commit -q -m "file-b lands separately, later"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    is_tag_content_reachable regroup-rebase-backup-20260101-000000
  )
}

# Scenario 7: negative counterpart to scenario 6 -- reorganized commit
# grouping must NOT make the check overly permissive. One of the two files
# genuinely never lands on $default_branch; the tag must still fail closed.
scenario_reorganized_commit_grouping_partial_miss_fails_closed() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > base.txt
    git add base.txt && git commit -q -m base
    git branch feature
    git checkout -q feature
    printf 'file-a\n' > file-a.txt
    printf 'file-b\n' > file-b.txt
    git add file-a.txt file-b.txt
    git commit -q -m "feature: add both files together"
    git tag -a partial-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # Only file-a lands on main -- file-b never does.
    printf 'file-a\n' > file-a.txt
    git add file-a.txt && git commit -q -m "file-a lands on its own"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable partial-rebase-backup-20260101-000000; then
      exit 1  # file-b was never verified -- this must fail closed
    else
      exit 0
    fi
  )
}

# Scenario 8: a PARENTLESS (root) commit inside the tag's own unique history
# -- e.g. a `git subtree --squash` import, or a `merge --allow-unrelated-
# histories` root -- must still be checked, not silently skipped. Without
# `--root`, `git diff-tree` on a parentless commit produces NO output at
# all (live-verified separately before writing this fixture), which the
# inner loop would read as "this commit changed nothing" and pass
# unverified (security-reviewer finding C1). Here the root commit's content
# genuinely lands on $default_branch via an ordinary later commit, so the
# fixed check (which sees it via `--root`) must recognize it as reachable.
scenario_root_commit_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > base.txt
    git add base.txt && git commit -q -m base
    # "feature" and "sub" both descend from a real shared ancestor (base) so
    # merge-base(tag, main) resolves to something other than "no common
    # ancestor" -- an unrelated-histories merge directly into main itself
    # would instead make main's own tip BE the merge commit, collapsing
    # rev-list mb..tag to nothing useful. Merging into a separate feature
    # branch instead keeps main's own lineage independent, so main can
    # later land (or not land) the root commit's content through a genuine,
    # unrelated commit of its own.
    git checkout -q -b feature
    git checkout -q --orphan sub
    printf 'subtree-content\n' > sub.txt
    git add sub.txt && git commit -q -m "parentless subtree import"
    git checkout -q feature
    git merge -q --allow-unrelated-histories --no-ff -m "merge subtree into feature" sub
    git tag -a roottag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature sub >/dev/null
    # main never merges feature/sub at all -- it independently lands the
    # same content via its own ordinary commit.
    printf 'subtree-content\n' > sub.txt
    git add sub.txt && git commit -q -m "subtree content lands normally on main"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    is_tag_content_reachable roottag-rebase-backup-20260101-000000
  )
}

# Scenario 9: negative counterpart to scenario 8 -- a parentless commit's
# content that never lands on $default_branch must still fail closed. Guards
# against `--root` (or the loop that now sees its content) becoming
# over-permissive rather than merely fixing the false-pass.
scenario_root_commit_missing_fails_closed() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > base.txt
    git add base.txt && git commit -q -m base
    git checkout -q -b feature
    git checkout -q --orphan sub
    printf 'subtree-content\n' > sub.txt
    git add sub.txt && git commit -q -m "parentless subtree import"
    git checkout -q feature
    git merge -q --allow-unrelated-histories --no-ff -m "merge subtree into feature" sub
    git tag -a rootmiss-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature sub >/dev/null
    # sub.txt's content never lands on main at all.
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable rootmiss-rebase-backup-20260101-000000; then
      exit 1  # the root commit's content was never verified -- must fail closed
    else
      exit 0
    fi
  )
}

# Scenario 10: a tag commit deletes a path whose name needs C-quoting (a
# non-ASCII byte under the default core.quotePath=true) and $default_branch
# still has that path -- the deletion was never reflected there, so this
# must fail closed. Before the `-z` fix, the quoted literal string handed to
# `git cat-file -e` was itself a bad revision spec that always failed,
# which the `&&` misread as "path absent" regardless of the real state
# (security-reviewer finding M2, live-verified against this exact filename
# before writing this fixture).
scenario_nonascii_deletion_not_reflected_fails_closed() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'x\n' > "café.txt"
    git add "café.txt" && git commit -q -m "add cafe file"
    git branch feature
    git checkout -q feature
    git rm -q "café.txt"
    git commit -q -m "feature deletes the cafe file"
    git tag -a nonasciidel-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main never deletes café.txt -- it's still there.
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable nonasciidel-rebase-backup-20260101-000000; then
      exit 1  # main still has the file -- the deletion was never reflected
    else
      exit 0
    fi
  )
}

# Scenario 11: positive counterpart to scenario 10 -- the same non-ASCII
# deletion, but $default_branch also deletes the file, so the tag must be
# recognized as reachable.
scenario_nonascii_deletion_reflected_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'x\n' > "café.txt"
    git add "café.txt" && git commit -q -m "add cafe file"
    git branch feature
    git checkout -q feature
    git rm -q "café.txt"
    git commit -q -m "feature deletes the cafe file"
    git tag -a nonasciidelok-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    git rm -q "café.txt"
    git commit -q -m "main also deletes the cafe file"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    is_tag_content_reachable nonasciidelok-rebase-backup-20260101-000000
  )
}

# Scenario 12: a `git diff-tree` failure on a NON-merge commit (a corrupted/
# unreadable tree object) must be distinguished from a genuinely empty diff
# -- the same distinction `scenario_bad_ref_fails_closed` already requires
# for the merge-commit branch, mirrored here for the non-merge branch
# (security-reviewer finding M1, live-verified with this exact corruption
# technique before writing this fixture: empty stdout + exit 128).
scenario_diff_tree_failure_fails_closed() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > a.txt
    git add a.txt && git commit -q -m base
    git branch feature
    git checkout -q feature
    printf 'feature\n' > b.txt
    git add b.txt && git commit -q -m "feature change"
    git tag -a corrupttag-rebase-backup-20260101-000000 -m backup HEAD
    feature_commit=$(git rev-parse HEAD)
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # Corrupt the feature commit's own tree object so `git diff-tree` on it
    # fails with a real error rather than producing a genuinely empty diff.
    feature_tree=$(git rev-parse "${feature_commit}^{tree}")
    rm -f ".git/objects/${feature_tree:0:2}/${feature_tree:2}"
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable corrupttag-rebase-backup-20260101-000000; then
      exit 1  # a diff-tree failure must never be read as "safe to skip"
    else
      exit 0
    fi
  )
}

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
run scenario_reorganized_commit_grouping_recognized "content reorganized into different commits on default_branch is still recognized"
run scenario_reorganized_commit_grouping_partial_miss_fails_closed "reorganized grouping doesn't mask a genuinely missing file"
run scenario_root_commit_recognized "a parentless (root) commit's content is checked, not silently skipped"
run scenario_root_commit_missing_fails_closed "a parentless commit's missing content still fails closed"
run scenario_nonascii_deletion_not_reflected_fails_closed "a non-ASCII path deletion not reflected on default_branch fails closed"
run scenario_nonascii_deletion_reflected_recognized "a non-ASCII path deletion reflected on default_branch is recognized"
run scenario_diff_tree_failure_fails_closed "a git diff-tree failure on a non-merge commit fails closed"

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
