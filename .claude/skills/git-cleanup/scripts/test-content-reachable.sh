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
  # -b main: every scenario's own `default_branch=main; git show-ref ... ||
  # default_branch=master` fallback already tolerates either, but pinning
  # the actual initial branch name removes a real, host-dependent source of
  # flakiness (security-reviewer finding m8) -- a host whose
  # init.defaultBranch is "master" previously made $TARGET's own
  # $default_branch resolution and this suite's per-scenario default_branch
  # disagree about which branch is "the" default in a way that surfaced as
  # an unrelated-looking failure (an empty --diff, read as "no differences")
  # rather than a clearly-flaky-fixture signal.
  git -C "$dir" init -q -b main
  git -C "$dir" config user.email test@test.com
  git -C "$dir" config user.name test
  git -C "$dir" config core.autocrlf false
  # On a host where core.filemode defaults to true (typical on Linux/ext4 --
  # this repo's own machine defaults to false, typical on Windows/NTFS,
  # which has no real POSIX executable bit), `git update-index --chmod=+x`
  # (used by the mode-change scenarios below) updates only the INDEX, not
  # the working-tree file's real permission bits -- with filemode tracking
  # on, git then sees the working tree as locally modified (index/disk mode
  # mismatch) and a later `git checkout` to switch branches refuses,
  # breaking those scenarios on any host where filemode defaults to true.
  # Forced false here so scenario behavior is deterministic across hosts,
  # matching this repo's own actual setting rather than depending on
  # whatever the running machine happens to default to (GitHub automated
  # review, PR #315, Codex connector P2 -- live-verified: forcing
  # core.filemode=true on an already-built scratch repo from this suite
  # made `git status` immediately report the mode-changed file as modified).
  git -C "$dir" config core.filemode false
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
# own header text, correctly detecting a merge), while `git diff-tree -m`
# (originally `--cc`; both read the merge commit's own tree the same way,
# see the corruption comment below) genuinely fails with "fatal: unable to
# read tree" -- live-verified this combination is real, not simulated.
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
  # unrelated reason. The merge's OWN tree is needed only by `-m` (which
  # compares it against both parents; originally `--cc`, same requirement)
  # -- live-verified: merge-base stays intact, `git diff-tree -m` on the
  # merge fails cleanly ("fatal: unable to read tree"), and both feature1's
  # and feature2's own standalone diffs are completely unaffected, since
  # neither reads the merge's own tree.
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

# Scenario 13: a MODE-ONLY change (chmod +x, same blob) that genuinely lands
# on $default_branch must be recognized as reachable -- cross-model-review
# finding (Codex fresh-eyes, confirmed by Claude's Phase 2 pass, severity
# corrected upward from this session's earlier security-reviewer pass, which
# had filed the identical gap as merely informational). Uses
# `git update-index --chmod=+x` rather than a real filesystem `chmod`, since
# this repo's own `core.filemode=false` default (typical on Windows/NTFS,
# which has no real POSIX executable bit) makes a real `chmod` invisible to
# git entirely -- `update-index --chmod` forces the mode directly in the
# index regardless of platform, live-verified before writing this fixture.
scenario_mode_change_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'script content\n' > run.sh
    git add run.sh && git commit -q -m base
    git branch feature
    git checkout -q feature
    git update-index --chmod=+x run.sh
    git commit -q -m "make run.sh executable"
    git tag -a modetag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main independently makes the identical mode change.
    git update-index --chmod=+x run.sh
    git commit -q -m "main also makes run.sh executable"
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    is_tag_content_reachable modetag-rebase-backup-20260101-000000
  )
}

# Scenario 14: negative counterpart to scenario 13 -- the mode change is
# NEVER reflected on $default_branch (same blob, but $default_branch's own
# copy stays at the original mode). Before this fix, blob equality alone
# would have reported this "reachable" even though the mode change -- the
# only thing the tag's commit actually did -- never landed anywhere else;
# live-verified as a real false-positive-on-the-reachability-question against
# this exact fixture before the fix, and confirmed correctly failing closed
# after it.
scenario_mode_change_not_reflected_fails_closed() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'script content\n' > run.sh
    git add run.sh && git commit -q -m base
    git branch feature
    git checkout -q feature
    git update-index --chmod=+x run.sh
    git commit -q -m "make run.sh executable"
    git tag -a modemiss-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main never chmods run.sh -- it stays at its original mode forever.
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable modemiss-rebase-backup-20260101-000000; then
      exit 1  # the mode change was never verified -- must fail closed
    else
      exit 0
    fi
  )
}

# Scenario 15: a real filename containing a pathspec metacharacter (`[`)
# must still be recognized when its content genuinely lands on
# $default_branch via a separate commit -- regression coverage for
# GIT_LITERAL_PATHSPECS=1 (cross-model-review finding: Claude fresh-eyes,
# confirmed by Codex's Phase 2 pass) to confirm the fix doesn't itself break
# matching for exactly the kind of filename it targets.
scenario_special_char_filename_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > base.txt
    git add base.txt && git commit -q -m base
    git branch feature
    git checkout -q feature
    printf 'v1\n' > "release[1].txt"
    git add "release[1].txt" && git commit -q -m "feature: add release[1].txt"
    git tag -a bracketfile-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    printf 'v1\n' > "release[1].txt"
    git add "release[1].txt" && git commit -q -m "release[1].txt lands on main"
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    # Exported explicitly here to match the real script's own top-level
    # `export GIT_LITERAL_PATHSPECS=1` -- FUNCS only sources the individual
    # function bodies via sed, not that top-level line, so without this the
    # scenario would test default (glob) pathspec matching instead of the
    # actual fix as deployed.
    export GIT_LITERAL_PATHSPECS=1
    eval "$FUNCS"
    is_tag_content_reachable bracketfile-rebase-backup-20260101-000000
  )
}

# Scenario 16: a deletion record's verification must fail closed when
# $default_branch's own object for that path can't be read -- not just when
# the path is genuinely absent. `git cat-file -e "$default_branch:$path"`
# fails (nonzero exit) both when the path is genuinely gone AND when the
# path still exists but its blob object is missing/corrupted -- the two
# cases are indistinguishable by exit code alone, so the old `&&`-based
# check silently misread a corrupted-but-present path as "deletion
# satisfied" (cross-model-review finding, round 2, Codex fresh-eyes;
# live-verified before writing this fixture: deleting a blob object out from
# under an otherwise-intact tree entry makes `cat-file -e` fail while the
# path is still genuinely present in the tree). Fixed with `git ls-tree`
# instead, which never needs to open the blob to answer "does this path
# exist" -- live-verified separately: exit 0 with the entry still listed
# even when that same blob is deleted.
scenario_deletion_check_survives_corrupted_blob() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'secret content\n' > secret.txt
    git add secret.txt && git commit -q -m "add secret.txt"
    secret_blob=$(git rev-parse HEAD:secret.txt)
    git branch feature
    git checkout -q feature
    git rm -q secret.txt
    git commit -q -m "feature deletes secret.txt"
    git tag -a delcorrupttag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main still genuinely has secret.txt -- the deletion never landed. Now
    # corrupt ONLY its blob object (not the tree entry) to confirm the check
    # still correctly reports "not reflected" rather than being fooled by
    # the resulting read failure into reporting "satisfied".
    rm -f ".git/objects/${secret_blob:0:2}/${secret_blob:2}"
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable delcorrupttag-rebase-backup-20260101-000000; then
      exit 1  # secret.txt is still genuinely present -- must fail closed
    else
      exit 0
    fi
  )
}

# Scenario 17: a blob that existed on $default_branch only BEFORE the
# branches diverged -- added, then deleted, entirely pre-divergence -- must
# NOT satisfy reachability just because the tag's own branch happens to
# re-add byte-identical content. Without bounding the search to
# $mb..$default_branch, an unbounded full-history walk finds this stale
# pre-divergence blob and incorrectly reports "reachable" (GitHub automated
# review, PR #315, Codex connector P1 -- live-verified against this exact
# fixture before writing it: the unbounded version reported reachable even
# though $default_branch never contained the file after the branches split).
scenario_pre_divergence_blob_not_reachable() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'secret content\n' > data.txt
    git add data.txt && git commit -q -m "add data.txt"
    git rm -q data.txt
    git commit -q -m "main deletes data.txt (before any branch exists)"
    git branch feature
    git checkout -q feature
    printf 'secret content\n' > data.txt
    git add data.txt && git commit -q -m "feature re-adds identical data.txt"
    git tag -a predivtag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main never restores data.txt after the branches diverged.
  )
  (
    cd "$repo"
    default_branch=main
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable predivtag-rebase-backup-20260101-000000; then
      exit 1  # data.txt was never restored post-divergence -- must fail closed
    else
      exit 0
    fi
  )
}

# Scenario 18: positive counterpart/regression guard for scenario 17 --
# bounding the search to $mb..$default_branch must not introduce a NEW false
# negative for content genuinely inherited unchanged from the shared
# ancestor itself. The tag's history has two commits: one that modifies a
# path away from $mb's content (independently verified reachable too, via a
# separate main commit reproducing the same modification -- this isolates
# the fast path under test from the unrelated "every commit's own content
# must be reachable" requirement, which would otherwise fail the tag closed
# for a wholly different reason and mask what this scenario means to check),
# and one that reverts the path back to exactly $mb's own original content.
# $default_branch never independently reintroduces that original content
# after $mb -- it's only ever inherited from $mb itself, unchanged -- so
# only checking $mb's own tree directly (not just $mb..$default_branch,
# which excludes $mb) recognizes the revert commit correctly (live-verified
# before writing this fixture: excluding $mb from the check incorrectly
# reports this unreachable, even though $default_branch's current tree
# still has the pre-divergence content it never touched).
scenario_content_inherited_from_merge_base_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'shared content\n' > shared.txt
    git add shared.txt && git commit -q -m "add shared.txt"
    git branch feature
    git checkout -q feature
    printf 'MODIFIED\n' > shared.txt
    git add shared.txt && git commit -q -m "feature: modify shared.txt"
    printf 'shared content\n' > shared.txt
    git add shared.txt && git commit -q -m "feature: revert shared.txt to original"
    git tag -a reverttag-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main independently lands the SAME intermediate modification (so that
    # commit's own content is verifiable too) but never reintroduces the
    # original content afterward -- the revert commit's own reachability can
    # only come from $mb's own tree, inherited unchanged.
    printf 'MODIFIED\n' > shared.txt
    git add shared.txt && git commit -q -m "main independently makes the same modification"
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    is_tag_content_reachable reverttag-rebase-backup-20260101-000000
  )
}

# Scenario 19: $default_branch's OWN history contains a merge commit with
# genuine hand-resolved conflict content (not the tag's own merge -- that
# case is scenario_trivial_merge_skipped, about the merge-commit handling
# INSIDE is_tag_content_reachable's own walk of the tag's history; this one
# is about is_path_blob_reachable's batched `git log --raw` search finding
# a match that originates from such a merge commit on $default_branch's
# side). Regression coverage for the `-m` flag specifically (CodeRabbit
# automated PR review, PR #315): without it, `git log --raw` shows NOTHING
# for a merge commit with real conflict-resolution content, silently
# missing a genuine match -- live-verified before writing this fixture.
scenario_default_branch_merge_conflict_content_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    base_commit=$(git rev-parse HEAD)
    git branch branchA
    git branch branchB
    git checkout -q branchA
    printf 'A-content\n' > shared.txt
    git commit -q -am "branchA change"
    git checkout -q branchB
    printf 'B-content\n' > shared.txt
    git commit -q -am "branchB change"
    git checkout -q main 2>/dev/null || git checkout -q master
    git merge -q branchA -m "merge branchA"
    # A real, hand-resolved conflict -- not a trivial/no-op merge.
    git merge --no-ff -m "merge branchB (conflict)" branchB 2>&1 || true
    printf 'RESOLVED-content\n' > shared.txt
    git add shared.txt && git commit -q -m "merge branchB (conflict)"
    git branch -D branchA branchB >/dev/null
    # The tag's own branch independently arrives at the SAME resolved
    # content, via an ordinary commit off the original base -- never
    # touching $default_branch's own merge at all.
    git branch feature "$base_commit"
    git checkout -q feature
    printf 'RESOLVED-content\n' > shared.txt
    git commit -q -am "feature independently arrives at the resolved content"
    git tag -a mergeconflict-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    is_tag_content_reachable mergeconflict-rebase-backup-20260101-000000
  )
}

# Scenario 20: negative counterpart to scenario_trivial_merge_skipped -- a
# merge that force-resolves to exactly ONE parent's state for a path must
# NOT be silently skipped, even though `--cc` (the old check this replaced)
# reports it as trivial. Regression coverage for the `-m`-based unification
# of is_tag_content_reachable's merge and non-merge handling (GitHub
# automated review, PR #315, Codex connector P1 on commit bd9ea5de4c):
# `--cc` only shows a path that differs from EVERY parent, so it's blind to
# a merge that drops content matching one parent exactly, even when that
# represents real, unrecoverable loss relative to the OTHER parent.
#
# Construction (isolated in a scratch repo -- three earlier attempts each
# had a confound before this one isolated the bug cleanly, see this
# session's own investigation): parent1 (main) adds secret.txt in its own
# commit; parent2 is a divergent branch with ONLY an --allow-empty commit
# (zero real content changes of its own, so it can never be independently
# caught by check_diff_records' per-parent walk the way a real standalone
# change would be). The tag's own merge combines them but is FORCED (via
# `git rm` before committing) to drop secret.txt, making the merge's
# resulting tree match parent2 exactly -- which is exactly why `--cc`
# reports no diff at all. `main` is left unchanged and still has
# secret.txt, so the merge's own deletion was never actually reflected
# there.
scenario_merge_resolves_to_one_parent_content_loss_fails_closed() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > base.txt
    git add base.txt && git commit -q -m base
    # The tag's own merge is built on a SEPARATE branch, never merged back
    # into main -- if the merge were built directly on main, merge-base(tag,
    # main) would collapse to the tag's own tip (main IS the tag at that
    # point), making tag_commits empty and the check pass trivially for the
    # wrong reason, regardless of whether the bug under test is fixed (the
    # same construction pitfall scenario_bad_ref_fails_closed's own comment
    # documents).
    git branch p2
    git checkout -q -b tagbranch
    printf 'secret\n' > secret.txt
    git add secret.txt && git commit -q -m "p1 (main): add secret.txt"
    git checkout -q main 2>/dev/null || git checkout -q master
    git merge -q --ff-only tagbranch
    git checkout -q p2
    git commit -q --allow-empty -m "p2: divergent but empty commit"
    git checkout -q tagbranch
    git merge --no-ff --no-commit p2 >/dev/null 2>&1 || true
    git rm -q -f secret.txt
    git commit -q -m "merge p2 (forced to drop secret.txt to match p2 exactly)"
    git tag -a mergeblindspot-rebase-backup-20260101-000000 -m backup tagbranch
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D p2 tagbranch >/dev/null
    # main is intentionally left exactly as-is -- it still has secret.txt,
    # which the tag's own merge discarded without that discard ever landing
    # on main.
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable mergeblindspot-rebase-backup-20260101-000000; then
      exit 1  # main still has secret.txt -- this must fail closed
    else
      exit 0
    fi
  )
}

# Scenario 21: issue #317 -- content that lands on $default_branch via a
# DIFFERENT COMMIT ORDER than the tag recorded it, so no single historical
# commit on $default_branch ever matches one of the tag's own EARLIER,
# later-superseded commit blobs for a path, even though the tag's FINAL
# (tip) content for that path is byte-identical to $default_branch's CURRENT
# content. A "final-state shortcut" was tried here and REVERTED before
# shipping -- found unsafe by a pre-push cross-model-review pass (see
# scenario 23 below, which locks in the exact counter-example that killed
# it). No safe narrowing of that shortcut was found that still resolves
# this scenario (see is_path_blob_reachable's own comment for why), so this
# is now a NEGATIVE test: reordering-only convergence correctly still fails
# closed (reported "needs review", never auto-deleted) -- resolvable only
# via the guided-manual-review feature's human-reviewed --diff/--force.
scenario_reordered_final_state_not_auto_recognized() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'line0\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git branch feature
    git checkout -q feature
    # Commit 1: the tag's OWN addition -- this intermediate blob
    # ("line0\nP\n") never appears anywhere in main's own history.
    printf 'line0\nP\n' > shared.txt
    git add shared.txt && git commit -q -m "feature: add P"
    # Commit 2 (tip): the tag's own branch separately incorporates the
    # SAME content main independently added ("M"), producing the tag's
    # FINAL state.
    printf 'line0\nP\nM\n' > shared.txt
    git add shared.txt && git commit -q -m "feature: incorporate M"
    git tag -a reorderfinal-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main lands the identical final content in ONE commit -- it never
    # passes through the "line0\nP\n" intermediate state at all.
    printf 'line0\nP\nM\n' > shared.txt
    git add shared.txt && git commit -q -m "main lands the combined content directly"
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable reorderfinal-rebase-backup-20260101-000000; then
      exit 1  # no shortcut exists anymore -- must fail closed, not auto-recognize this
    else
      exit 0
    fi
  )
}

# Scenario 22: security-reviewer/cross-model-review finding (Codex
# fresh-eyes, high confidence, live-verified before reverting) -- the exact
# counter-example that killed the final-state shortcut scenario 21 once
# guarded. A tag's unique history adds UNIQUE content to a path, then a
# LATER commit in the SAME tag REVERTS that path back to $default_branch's
# own original (never-touched) content. The tag's own final state trivially
# matches $default_branch -- but the reverted-away unique content exists
# NOWHERE else and would be permanently lost (eventually garbage-collected)
# if a final-state-only check treated this as "reachable". Locks in that
# this must always fail closed, regardless of any future shortcut attempt.
scenario_self_reverted_unique_content_fails_closed() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'original\n' > secret.txt
    git add secret.txt && git commit -q -m base
    git branch feature
    git checkout -q feature
    printf 'SECRET-CONTENT\n' > secret.txt
    git add secret.txt && git commit -q -m "feature: add secret content"
    printf 'original\n' > secret.txt
    git add secret.txt && git commit -q -m "feature: revert secret.txt back to original"
    git tag -a selfrevert-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D feature >/dev/null
    # main never touches secret.txt at all -- stays at "original" forever.
  )
  (
    cd "$repo"
    default_branch=main
    # default_branch is read by is_tag_content_reachable via eval "$FUNCS" below,
    # which shellcheck can't see through -- false positive.
    # shellcheck disable=SC2034
    git show-ref --verify --quiet refs/heads/main || default_branch=master
    eval "$FUNCS"
    if is_tag_content_reachable selfrevert-rebase-backup-20260101-000000; then
      exit 1  # SECRET-CONTENT is unique to this tag -- must fail closed
    else
      exit 0
    fi
  )
}

# Scenarios 23-26: the --list-review/--diff/--force CLI modes added for
# git-cleanup's guided-manual-review phase. Unlike scenarios 1-22 (which
# `eval` the extracted function bodies in isolation), these invoke the real
# script directly ($TARGET) inside the scratch repo -- the behavior under
# test lives in the CLI dispatch itself (argument parsing, snapshot
# read/write, the atomic compare-and-delete), not in a function these tests
# could extract and eval the same way.

# Scenario 23: --list-review must show exactly the tags that fail the
# automated reachability check, and --list must show exactly the ones that
# pass -- the two lists are mutually exclusive by construction. Builds one of
# each in the same repo to confirm neither leaks into the other's output.
scenario_list_review_excludes_deletable_and_vice_versa() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    # Landed tag: feature adds a line that also lands on main verbatim.
    # Deliberately named so neither tag name is a substring of the other
    # (an earlier draft used "reachable"/"unreachable" -- "reachable" is a
    # literal substring of "unreachable", which made the exclusion greps
    # below pass or fail for the wrong reason regardless of the real
    # behavior; caught only by tracing an unexpected failure, not by
    # inspection).
    git checkout -q -b landedok-feature
    printf 'base\nlanded-line\n' > shared.txt
    git add shared.txt && git commit -q -m "landedok feature change"
    git tag -a landedok-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D landedok-feature >/dev/null
    printf 'base\nlanded-line\n' > shared.txt
    git add shared.txt && git commit -q -m "main lands the same line"
    # Never-landed tag: a genuinely different, never-landed change.
    git checkout -q -b neverlanded-feature
    printf 'base\nlanded-line\nnever-lands\n' > shared.txt
    git add shared.txt && git commit -q -m "neverlanded feature change"
    git tag -a neverlanded-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D neverlanded-feature >/dev/null
  )
  (
    cd "$repo"
    list_out=$(bash "$TARGET" --list 2>/dev/null)
    review_out=$(bash "$TARGET" --list-review 2>/dev/null)
    echo "$list_out" | grep -qF "landedok-rebase-backup-20260101-000000" || exit 1
    echo "$list_out" | grep -qF "neverlanded-rebase-backup-20260101-000000" && exit 1
    echo "$review_out" | grep -qF "neverlanded-rebase-backup-20260101-000000" || exit 1
    echo "$review_out" | grep -qF "landedok-rebase-backup-20260101-000000" && exit 1
    exit 0
  )
}

# Scenario 24: --diff must surface the actual differing content for a
# review candidate resolved by index, not just a pass/fail signal.
scenario_diff_shows_evidence_for_review_candidate() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git checkout -q -b orphan-feature
    printf 'base\nUNIQUE-MARKER-LINE\n' > shared.txt
    git add shared.txt && git commit -q -m "orphan feature change"
    git tag -a orphanmark-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D orphan-feature >/dev/null
  )
  (
    cd "$repo"
    bash "$TARGET" --list-review >/dev/null 2>&1
    diff_out=$(bash "$TARGET" --diff 1 2>/dev/null)
    echo "$diff_out" | grep -qF "UNIQUE-MARKER-LINE" || exit 1
    echo "$diff_out" | grep -qF "orphanmark-rebase-backup-20260101-000000" || exit 1
    exit 0
  )
}

# Scenario 25: --force must actually delete a genuine review candidate by
# index -- the positive counterpart to the existing scenario_atomic_delete,
# specifically for the review-snapshot path rather than the main snapshot.
scenario_force_deletes_review_candidate() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git checkout -q -b gone-feature
    printf 'base\nnever-lands\n' > shared.txt
    git add shared.txt && git commit -q -m "gone feature change"
    git tag -a gonefeat-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D gone-feature >/dev/null
  )
  (
    cd "$repo"
    bash "$TARGET" --list-review >/dev/null 2>&1
    bash "$TARGET" --force 1 >/dev/null 2>&1
    [ -z "$(git tag -l gonefeat-rebase-backup-20260101-000000)" ]
  )
}

# Scenario 26: --force must refuse (atomic compare-and-delete) when the tag
# was force-moved to a different object between --list-review and --force --
# the same TOCTOU protection scenario_atomic_delete already verifies for the
# plain delete path, mirrored here for the bypass path specifically, since
# --force's whole point is skipping the reachability re-check that path
# relies on -- the atomic compare-and-delete is the ONLY safety net left.
scenario_force_refuses_on_toctou_move() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git checkout -q -b moved-feature
    printf 'base\nnever-lands\n' > shared.txt
    git add shared.txt && git commit -q -m "moved feature change"
    git tag -a movedfeat-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main 2>/dev/null || git checkout -q master
    git branch -D moved-feature >/dev/null
  )
  (
    cd "$repo"
    bash "$TARGET" --list-review >/dev/null 2>&1
    # Force-move the tag to a different object after the snapshot was taken --
    # simulates a concurrent change in the window between --list-review and
    # --force.
    printf 'more\n' >> shared.txt
    git add shared.txt && git commit -q -m "moves the tag's target"
    git tag -f -a movedfeat-rebase-backup-20260101-000000 -m backup2 HEAD >/dev/null 2>&1
    if bash "$TARGET" --force 1 >/dev/null 2>&1; then
      exit 1  # should have refused -- the tag moved since --list-review
    fi
    # The tag must still exist (unchanged from the moved state), not deleted.
    [ -n "$(git tag -l movedfeat-rebase-backup-20260101-000000)" ]
  )
}

# Scenario 27: security-reviewer finding C1 -- an unresolvable
# $default_branch must fail loudly (a clear error, non-zero exit) rather
# than let --diff silently produce empty evidence indistinguishable from a
# genuine "no differences" match.
scenario_unresolvable_default_branch_fails_loudly() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > a.txt
    git add a.txt && git commit -q -m base
    git checkout -q -b other
    # Delete "main" entirely -- $default_branch has nothing to resolve to.
    git branch -D main >/dev/null
  )
  (
    cd "$repo"
    out=$(bash "$TARGET" --list 2>&1)
    rc=$?
    [ "$rc" -ne 0 ] || exit 1
    echo "$out" | grep -qi "does not resolve to a valid ref" || exit 1
    exit 0
  )
}

# Scenario 28: security-reviewer finding C2 -- --force must NOT delete
# $REVIEW_SNAPSHOT, so a second candidate from the same --list-review run
# stays usable (--diff/--force/--keep) after the first is force-deleted.
scenario_force_snapshot_survives_for_next_item() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    for n in one two; do
      git checkout -q -b "gone-$n"
      printf 'base\nnever-lands-%s\n' "$n" > shared.txt
      git add shared.txt && git commit -q -m "gone-$n change"
      git tag -a "gone$n-rebase-backup-20260101-000000" -m backup HEAD
      git checkout -q main
      git branch -D "gone-$n" >/dev/null
    done
  )
  (
    cd "$repo"
    bash "$TARGET" --list-review >/dev/null 2>&1
    bash "$TARGET" --force 1 >/dev/null 2>&1 || exit 1
    # The second candidate (index 2) must still be usable -- the snapshot
    # must not have been deleted by the first --force call.
    bash "$TARGET" --diff 2 >/dev/null 2>&1 || exit 1
    exit 0
  )
}

# Scenario 29: security-reviewer finding M2 -- --force must refuse when
# $default_branch itself advanced since --list-review, even though the
# tag's own oid never moved -- pinning only the tag's oid would miss this.
scenario_force_refuses_when_default_branch_advanced() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git checkout -q -b gone-feature
    printf 'base\nnever-lands\n' > shared.txt
    git add shared.txt && git commit -q -m "gone feature change"
    git tag -a defadvance-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main
    git branch -D gone-feature >/dev/null
  )
  (
    cd "$repo"
    bash "$TARGET" --list-review >/dev/null 2>&1
    # Advance main -- the tag itself never moves.
    printf 'main-advances\n' >> shared.txt
    git add shared.txt && git commit -q -m "main advances after --list-review"
    if bash "$TARGET" --force 1 >/dev/null 2>&1; then
      exit 1  # should have refused -- default_branch moved since --list-review
    fi
    [ -n "$(git tag -l defadvance-rebase-backup-20260101-000000)" ]
  )
}

# Scenario 30: --keep records a decision that suppresses the candidate from
# a subsequent --list-review, entirely via the script's own index-keyed
# interface (security-reviewer finding C3/M4 -- no jq/git command composed
# by the caller ever needs the raw tag name).
scenario_keep_records_and_suppresses() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git checkout -q -b keep-feature
    printf 'base\nnever-lands\n' > shared.txt
    git add shared.txt && git commit -q -m "keep feature change"
    git tag -a keepme-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main
    git branch -D keep-feature >/dev/null
  )
  (
    cd "$repo"
    bash "$TARGET" --list-review >/dev/null 2>&1
    bash "$TARGET" --keep 1 >/dev/null 2>&1 || exit 1
    [ -f .claude/git-cleanup-review-decisions.local.json ] || exit 1
    grep -qF "keepme-rebase-backup-20260101-000000" .claude/git-cleanup-review-decisions.local.json || exit 1
    # Fresh --list-review must no longer include the kept candidate.
    review_out=$(bash "$TARGET" --list-review 2>/dev/null)
    echo "$review_out" | grep -qF "keepme-rebase-backup-20260101-000000" && exit 1
    exit 0
  )
}

# Scenario 31: a "keep" decision must resurface (not stay permanently
# suppressed) once $default_branch advances past what was pinned at
# decision time -- the staleness rule this whole design is built around.
scenario_keep_resurfaces_after_default_branch_advances() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    git checkout -q -b stale-feature
    printf 'base\nnever-lands\n' > shared.txt
    git add shared.txt && git commit -q -m "stale feature change"
    git tag -a stalekeep-rebase-backup-20260101-000000 -m backup HEAD
    git checkout -q main
    git branch -D stale-feature >/dev/null
  )
  (
    cd "$repo"
    bash "$TARGET" --list-review >/dev/null 2>&1
    bash "$TARGET" --keep 1 >/dev/null 2>&1 || exit 1
    review_out=$(bash "$TARGET" --list-review 2>/dev/null)
    echo "$review_out" | grep -qF "stalekeep-rebase-backup-20260101-000000" && exit 1
    # Advance main -- the pinned default_branch_sha is now stale.
    printf 'main-advances\n' >> shared.txt
    git add shared.txt && git commit -q -m "main advances after keep"
    review_out2=$(bash "$TARGET" --list-review 2>/dev/null)
    echo "$review_out2" | grep -qF "stalekeep-rebase-backup-20260101-000000" || exit 1
    exit 0
  )
}

# Scenario 32: security-reviewer/Codex cross-model-review finding (F1),
# swept into the PRE-EXISTING plain-delete loop (--list / <index>) as a
# sibling instance of the same bug found in --force/--keep/--diff: under
# `set -euo pipefail`, `pre_check_oid=$(git rev-parse ...)` with no `||`
# fallback silently killed the ENTIRE multi-tag delete loop the instant one
# requested tag no longer resolved, instead of reporting "Skipped" for just
# that one and continuing with the rest -- exactly the partial-failure
# behavior this loop's own comments already document as intended. Invokes
# the real CLI (`--list` then `<index> <index>`), not the extracted
# functions, since the bug lives in the CLI's own delete loop.
scenario_plain_delete_skips_already_gone_tag_and_continues() {
  local repo; repo=$(new_repo)
  (
    cd "$repo"
    printf 'base\n' > shared.txt
    git add shared.txt && git commit -q -m base
    for n in 1 2; do
      git checkout -q -b "gone-$n"
      printf 'unique-%s\n' "$n" > "file-$n.txt"
      git add "file-$n.txt" && git commit -q -m "gone-$n change"
      # Fast-forward main to include this commit -- unambiguously makes
      # the tag's own commit an ancestor of main (raw-SHA safe-to-delete),
      # no content-reachability nuance needed for this test.
      git checkout -q main
      git merge -q --ff-only "gone-$n"
      git tag -a "gone$n-rebase-backup-20260101-000000" -m backup HEAD
      git branch -D "gone-$n" >/dev/null
    done
  )
  (
    cd "$repo"
    bash "$TARGET" --list >/dev/null 2>&1
    # Delete the FIRST candidate out from under the snapshot before the
    # actual delete call runs -- simulates a concurrent deletion between
    # --list and Phase 5's own delete call.
    git tag -d gone1-rebase-backup-20260101-000000 >/dev/null
    out=$(bash "$TARGET" 1 2 2>&1)
    rc=$?
    # Must NOT crash (a bash internal error / unexplained non-1 exit would
    # indicate the set -e crash reappeared) -- exit 1 here means "one of
    # the two indices failed," the correct partial-failure result.
    [ "$rc" -eq 1 ] || exit 1
    echo "$out" | grep -qF "Skipped 'gone1-rebase-backup-20260101-000000': could not resolve" || exit 1
    # The SECOND tag must still have been processed and deleted -- the
    # bug this test guards against made the whole loop die on the first
    # failure, never reaching the second index at all.
    [ -z "$(git tag -l gone2-rebase-backup-20260101-000000)" ] || exit 1
    exit 0
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
run scenario_mode_change_recognized "a mode-only change (chmod +x) reflected on default_branch is recognized"
run scenario_mode_change_not_reflected_fails_closed "a mode-only change not reflected on default_branch fails closed"
run scenario_special_char_filename_recognized "a filename containing a pathspec metacharacter is still matched literally"
run scenario_deletion_check_survives_corrupted_blob "a deletion check fails closed when the path's blob is unreadable, not just when absent"
run scenario_pre_divergence_blob_not_reachable "a blob present on default_branch only before divergence does not satisfy reachability"
run scenario_content_inherited_from_merge_base_recognized "content inherited unchanged from the merge-base is still recognized as reachable"
run scenario_default_branch_merge_conflict_content_recognized "default_branch's own merge-conflict-resolution content is still recognized"
run scenario_merge_resolves_to_one_parent_content_loss_fails_closed "a tag's own merge resolving to exactly one parent's state still fails closed on lost content"
run scenario_reordered_final_state_not_auto_recognized "content landed via a different commit order (issue #317) is NOT auto-recognized -- fails closed, deferred to guided manual review"
run scenario_self_reverted_unique_content_fails_closed "unique content later self-reverted within the same tag still fails closed (security-reviewer/Codex finding)"
run scenario_list_review_excludes_deletable_and_vice_versa "--list-review and --list are mutually exclusive over the same tag set"
run scenario_diff_shows_evidence_for_review_candidate "--diff surfaces the actual differing content for a review candidate"
run scenario_force_deletes_review_candidate "--force deletes a genuine review candidate by index"
run scenario_force_refuses_on_toctou_move "--force refuses when the tag moved since --list-review (atomic compare-and-delete)"
run scenario_unresolvable_default_branch_fails_loudly "an unresolvable default branch fails loudly instead of silently"
run scenario_force_snapshot_survives_for_next_item "--force doesn't delete the review snapshot, so the next candidate stays usable"
run scenario_force_refuses_when_default_branch_advanced "--force refuses when the default branch advanced since --list-review"
run scenario_keep_records_and_suppresses "--keep records a decision and suppresses the candidate from a fresh --list-review"
run scenario_keep_resurfaces_after_default_branch_advances "a kept decision resurfaces once the default branch advances past what was pinned"
run scenario_plain_delete_skips_already_gone_tag_and_continues "the plain --list delete loop skips an already-gone tag and still processes the rest (Codex F1 sibling instance)"

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
