# Testing & Validation

**Verify this skill activates on:**
- "clean up my old branches and worktrees"
- "I have a bunch of stale branches, help me clean up"

**Verify it does NOT activate on:**
- "delete this one specific branch" without a broader cleanup context
- automated/headless invocation — this skill requires two user confirmations and is not designed for
  non-interactive use

**Verify Phase 4's gitignored-content detection:**
- A worktree whose only content is gitignored (e.g. a local `.env`, nothing else uncommitted) — confirm
  Phase 4 warns with the "Ignored (not tracked by git, will also be deleted):" block, rather than reporting
  the worktree as clean because `git status --porcelain` alone found nothing
- A worktree with both tracked-dirty and gitignored content — confirm both warning blocks appear together,
  clearly separated
- A worktree with neither — confirm no warning fires and the worktree proceeds through normal
  categorization

**Quality gates:**
- [ ] Phase 4 always runs `--ignored` alongside the plain `--porcelain` check for every worktree, never
      only one or the other
- [ ] A long ignored-file list (e.g. `node_modules/`) is summarized (top-level entries + count), never
      dumped in full and burying the warning
- [ ] `git clean` is never invoked at any point in this skill — detection only, never deletion of untracked
      or ignored content
- [ ] Safety Rule 5's "dirty" always includes gitignored content, not just tracked/untracked-but-not-ignored
      changes

**Verify Phase 3.6's rebase-backup tag cleanup (live-verified, 2026-08-31, against a scratch repo built
specifically for this — not this repository's own history, since it has no real `*-rebase-backup-*` tags
to exercise):**
- [ ] `phase1-analysis.sh`'s tag enumeration only matches a tag fitting the exact
      `{branch}-rebase-backup-{8-digit-date}-{6-digit-time}` shape — a tag that merely contains the
      substring `-rebase-backup-` without the trailing digit-shape is never swept in
- [ ] A tag whose derived branch no longer exists locally AND whose commit is reachable from the default
      branch (`git merge-base --is-ancestor` succeeds) is reported "no longer exists locally" +
      "reachable from `<default>`: yes" and is a `STALE_REBASE_BACKUP_TAG` candidate
- [ ] A tag whose derived branch no longer exists locally AND whose commit is NOT reachable from the
      default branch is reported "reachable from `<default>`: NO -- this tag may be the only remaining
      copy of its commits" and is NEVER proposed for deletion — surfaced instead under a separate
      "needs review — unique history" note, never folded into "delete all recommended"
      (found by `cross-model-review`, Codex Phase 1 re-review after the injection fix, 2026-08-31 — a
      real, severe data-loss risk distinct from the earlier injection finding; live-verified with a
      force-deleted, never-merged branch whose only surviving commit was confirmed reachable solely via
      its backup tag, via `git merge-base --is-ancestor <sha> main` returning false)
- [ ] A tag whose derived branch still exists, is merged into the default branch, AND whose own commit is
      reachable from the default branch is reported "exists, merged into `<default>`" +
      "reachable from `<default>`: yes" and is a `STALE_REBASE_BACKUP_TAG` candidate
- [ ] A tag whose derived branch still exists, is merged into the default branch, but whose own commit is
      NOT reachable from the default branch by raw SHA (a rebase-then-merge sequence, where the merged
      branch's tip is a different commit object than the tag's pre-rebase commit) — the reachability
      check always runs for the merged case too, never skipped just because the branch itself is already
      known-safe to delete (found by `cross-model-review`, Codex Phase 1 re-review after the first
      data-loss fix, 2026-08-31 — the merged-branch case turned out to have the exact same flaw as the
      branch-gone case, just less obvious since "merged" sounds like a stronger safety signal than it
      actually is here; live-verified with a real rebase-then-merge sequence, confirming
      `git branch --merged` reports the branch merged while
      `git merge-base --is-ancestor <pre-rebase-sha> main` still returns false). **Superseded by PR #275**
      (see the "Live results, 2026-09-01" section below): raw-SHA unreachability here is no longer the
      final word — `is_tag_content_reachable`'s exact-diff-text fallback (patch-id used only as a cheap
      pre-filter, never the acceptance criterion) now recognizes this exact case as reachable when the
      tag's content genuinely matches the default branch, and Gate 1 reports it as
      "reachable from `<default>`: yes (content match after rebase...)" and it IS eligible for "delete all
      recommended" — never solely because the raw-SHA check failed. A tag unreachable by *both* signals
      still reports "NO" and is never proposed for deletion.
- [ ] A tag whose derived branch still exists and is NOT merged is reported "exists, not merged into
      `<default>`" and is never proposed for deletion, with no reachability check run at all — Phase 3.6
      leaves it alone regardless of the tag's own age, and the extra `git merge-base` call is skipped
      entirely for this case since the outcome doesn't depend on it
- [ ] `delete-rebase-backup-tags.sh`'s own internal `git update-ref -d` call runs with no marker-handshake
      write beforehand — confirmed `git-guard-raw-destructive-cleanup.sh` only matches
      `git branch -D`/`worktree remove --force`, never `git tag -d`/`git update-ref -d`
- [ ] Gate 1/Gate 2 list stale rebase-backup tags as their own category, distinct from branch and
      stale-remote-branch categories, never silently merged into either
- [ ] Deletion always goes through `delete-rebase-backup-tags.sh`'s index-only interface — the agent
      never types a tag name into any command, including as a script argument; a character-class
      validation on an agent-composed value was tried first and found both unsafe in principle (no class
      is both shell-safe and complete against every git-legal name) and, separately, incomplete in
      practice (`^[A-Za-z0-9._/-]+$` rejected legitimate branches like `feat/c++`)
      (found by `cross-model-review`, Codex Phase 1 + Codex Phase 2's own independent re-derivation +
      Claude Phase 2 for the injection risk, 2026-08-31: `git check-ref-format --allow-onelevel` accepts
      a tag name containing shell metacharacters, e.g. `` `$(id)-rebase-backup-20260831-120000` ``,
      live-verified as a legal git ref; then Codex's round-2 PR review for the completeness gap the
      narrower regex introduced, live-verified with `git check-ref-format --branch 'feat/c++'` and
      `feat/x=y,z@w`, both legal)
- [ ] `delete-rebase-backup-tags.sh --list` independently re-derives the deletable-tag set itself
      (branch gone or merged AND reachable), never trusting Phase 3.6's earlier read of the same facts —
      live-verified against a scratch repo with 3 tags (one safely deletable on an ordinary branch, one
      safely deletable on a branch with special characters `feat/c++`, one NOT deletable because its
      branch is still active): `--list` correctly included both deletable tags (including the
      special-character one) and excluded the active one
- [ ] Deleting by index removes exactly the intended tag and leaves the rest untouched — live-verified
      deleting index 1 twice in sequence (`feat/c++`'s tag, then the plain one) against the same 3-tag
      scratch repo, confirming only the active branch's tag survived
- [ ] The script's error paths match `git-stage-selected-files.sh`'s own conventions: no `--list` run yet
      (or the snapshot was already consumed) → "no candidate list found -- run --list first"; a
      non-digit index → "is not a positive integer"; an out-of-range index → "one or more requested
      indices are out of range" — all live-verified
- [ ] Each tag's safety is re-verified immediately before deletion, not just trusted from the `--list`
      snapshot — the snapshot only protects index-to-tag mapping against drift, not the tag's own state;
      a tag force-moved after `--list` runs is skipped at delete time with "no longer verified safe to
      delete", not silently deleted
      (found by `cross-model-review` round 5 on PR #262, both models independently — Codex Phase 1 raised
      it, Codex's own Phase 2 pass re-derived it independently before seeing Claude's input, and Claude's
      Phase 2 pass confirmed it, citing this repo's own
      `.claude/rules/recheck-state-before-side-effecting-action.md`; live-verified: force-moved a listed
      tag to an unreachable commit via `git tag -f` between `--list` and delete, confirmed the delete call
      now skips it and reports why, and the tag survives)
- [ ] Deletion is a true atomic compare-and-delete, not just "re-verify then delete by name" — the script
      resolves each tag's current object id via the fully-qualified `refs/tags/<name>` form immediately
      after `is_tag_safe_to_delete` returns true, then deletes with
      `git update-ref -d refs/tags/<name> <resolved-oid>`, which only succeeds if the ref still points at
      exactly that object; a force-move in the (now much narrower) window between resolving the oid and
      the delete call is refused, not silently deleted (PR #275, Devin automated PR review — the
      re-verify-then-name-based-delete pattern PR #262 shipped still had a residual race between the
      re-verify and the delete call itself, meaningfully widened by this predicate's own content-fallback
      taking real wall-clock time to run; live-verified in an isolated scratch repo: deleting with the
      correct, just-resolved oid succeeds, and deleting after force-moving the tag with a now-stale oid is
      refused with `error: cannot lock ref ...: is at <new> but expected <old>`, exit 1, tag intact)
      **Also verify `git rev-parse "refs/tags/<name>"` (no bare tag name, no `--end-of-options`) is what
      resolves the oid** — `--end-of-options` was tried first and found to not actually suppress option
      parsing for `git rev-parse` in the git version this was verified against: it gets echoed back as a
      literal token on the output's first line instead, live-verified; the fully-qualified `refs/tags/`
      prefix sidesteps the whole class of risk unconditionally instead (a value starting with `refs/tags/`
      can never be misparsed as an option, regardless of what the tag's own name starts with)
- [ ] The Category Definitions quick-reference table's `STALE_REBASE_BACKUP_TAG` row states the
      reachability condition explicitly, not just "branch gone or merged" — a reader skimming only the
      table (not Phase 3.6's own prose) must not be able to reconstruct the pre-fix, unsafe rule
      (found by Codex's automated PR review on PR #262, 2026-08-31: the table's own text contradicted
      Phase 3.6's actual, more restrictive rule)
- [ ] `phase1-analysis.sh`'s `default_branch` resolution always falls back to `main` when
      `origin/HEAD` has no symbolic-ref set, even though `sed` exits 0 on empty stdin (so a bare
      `... || echo "main"` never fires its fallback) — live-verified against a repo with no origin
      remote configured at all: before the fix, `default_branch` resolved to the empty string and
      every rebase-backup tag was misreported as unreachable ("reachable from : NO"); after the fix,
      the same repo correctly reports "reachable from main: yes"
      (found by Devin's automated PR review on PR #262, 2026-08-31 — a pre-existing gap in this
      script's default-branch resolution, surfaced because Phase 3.6's new reachability check is the
      first caller whose behavior actually depends on `$default_branch` never being empty)

**Live results, 2026-08-31:** ran the updated `phase1-analysis.sh` against a throwaway scratch repo with
five rebase-backup tags: one whose branch was merged (without rebasing) and then deleted (correctly
reported "no longer exists locally" + "reachable from main: yes"), one whose branch was merged (without
rebasing) but kept (correctly reported "exists, merged into main" + "reachable from main: yes"), one whose
branch is still active/unmerged (correctly reported "exists, not merged into main", no reachability check
run), one whose branch was force-deleted without ever merging (correctly reported "no longer exists
locally" + "reachable from main: NO"), and one whose branch was rebased onto an advanced `main` and then
merged (correctly reported "exists, merged into main" + "reachable from main: NO" — confirming the
rebase-then-merge case is caught even though the branch itself genuinely shows as merged). All five
matched the intended Phase 3.6 categorization with no false positives or negatives. Separately,
`git check-ref-format --allow-onelevel '$(id)-rebase-backup-20260831-123456'` was run live and confirmed
git accepts that string as a legal tag name, validating the ref-name safety check added above.

**Live results, 2026-08-31 (post-PR-review fixes):** re-ran against a sixth scratch repo with no origin
remote configured at all — before the `default_branch` fallback fix, every tag was misreported as
unreachable ("reachable from : NO", empty default-branch name visible in the output); after the fix,
the same repo correctly resolves to `main` and reports "reachable from main: yes". Re-ran the original
five-scenario repo afterward too, confirming no regression from the fallback fix.

**Verify Phase 3.5's remote-branch fallback (verified live, 2026-08-16, against two real stale remote
branches in this repository — `feat/plugin-auditor-codex-integration` (PR #41) and
`fix/sync-claude-mirror` (PR #20), both merged PRs whose remote branch survived the merge because a
worktree had them checked out):**
- [ ] `phase1-analysis.sh`'s remote-only branch list never includes `origin/HEAD`'s own symbolic-ref
      pointer as a spurious candidate — this git version renders it as bare `origin` (not `origin/HEAD`),
      which the script's filter must explicitly exclude before stripping the `origin/` prefix (confirmed
      live: an unfiltered run surfaced `origin` itself as a fake "branch")
- [ ] A remote-only branch whose PR is `OPEN` is never categorized `STALE_REMOTE_ONLY` and never appears
      in Gate 1/Gate 2's deletion list
- [ ] A remote-only branch with no PR at all is never categorized `STALE_REMOTE_ONLY`
- [ ] `gh pr view <branch>` is always called live per candidate — never inferred from "no local branch"
      or Phase 1's merged-branch list alone
- [ ] The ref-name safety check (`^[A-Za-z0-9._/-]+$`) always runs before `gh api -X DELETE`, matching
      `merge-pr`'s own check before the identical command
- [ ] No marker-handshake write happens before `gh api -X DELETE repos/*/git/refs/heads/*` — confirmed no
      PreToolUse hook guards that command (unlike `git branch -D` against a protected name)
- [ ] The remote-only-branch enumeration always scopes to `refs/remotes/origin` specifically
      (`git for-each-ref refs/remotes/origin`) — never `git branch -r`, which lists every configured
      remote and would leak a second remote's branches (e.g. `upstream/topic`) in as false candidates
      (found by CodeRabbit's automated PR review, 2026-08-16; re-verified live afterward — see below)

**Live results, 2026-08-16:** `phase1-analysis.sh` correctly surfaced both real stale branches after the
`origin`-symref filter fix; `gh pr view` correctly returned `state: MERGED` for both (PR #41, PR #20).
PR #41's branch was deleted via `finishing-work`'s step 1.5 (see that skill's own live-verification note).
PR #20's branch (`fix/sync-claude-mirror`) — which had no local counterpart, exercising the Phase 3.5
remote-only-orphan path specifically — was deleted end-to-end via this skill's exact Gate-1-confirm →
`gh api -X DELETE` procedure, with explicit user confirmation. A follow-up `git ls-remote --heads origin
fix/sync-claude-mirror` confirmed it was gone.

**Re-verified live, 2026-08-16, after fixing the origin-only-enumeration finding above:** re-ran the fixed
`phase1-analysis.sh` in this repository (a single-remote repo, so the fix couldn't be exercised against an
actual second remote here) — output unchanged and correct (empty remote-only-branch list, both real stale
branches already cleaned up by that point), confirming the fix didn't regress the single-remote case this
repo actually has.

**Verify the content-reachability fallback (`is_tag_content_reachable`, PR #275), live-verified
2026-09-01 against this repository's own real rebase-backup tags and a set of isolated scratch-repo
tests for each underlying git mechanic — not a hypothetical claim about how `git patch-id`/
`git diff-tree` behave, each was independently reproduced live. Superseded 2026-09-11 by a per-path,
per-blob redesign (see "Live results, 2026-09-11" below) that drops `git patch-id`/exact-diff-text
matching entirely — the mechanics this block documents (patch-id narrowing, exact-diff-text acceptance)
no longer exist in the current script; kept here as the historical record of what PR #275 actually
shipped and tested, same as PR #275's own "Superseded by" note above it did for its predecessor:**
- [ ] A rebase-merged tag (SHA differs from the default branch, content identical) is recognized as
      content-reachable and eligible for deletion — live-verified against this repo's real
      `feat/merge-pr-conflict-checks-rebase-backup-20260901-064237` tag: all 6 commits unique to the tag
      had an exact patch-id match on `main`, and the raw diff text (not just the patch-id) was confirmed
      byte-identical between the tag's pre-rebase commit and `main`'s post-rebase commit — the mechanism
      this fallback exists for
- [ ] `git patch-id` is whitespace-insensitive — two commits whose diffs differ ONLY in leading
      whitespace amount (2 vs. 4 spaces added to the same line) produced an identical patch-id in an
      isolated scratch repo, confirming patch-id alone is unsafe as the acceptance criterion; the
      predicate uses it only to narrow candidates, requiring an exact byte-for-byte diff-text match
      before ever accepting one (found by Codex fresh-eyes, `cross-model-review` round 1)
- [ ] The exact-diff-text requirement does not reject the genuine rebase-merge case — git blob hashes are
      purely content-addressed, so a rebase that doesn't touch a commit's actual content leaves the
      "index `<old>`..`<new>`" line inside that commit's diff text byte-identical too; live-verified
      against the real tag above
- [ ] A merge commit with no unique content (`git diff-tree --cc` empty) inside a tag's history is
      skipped rather than failing the whole tag closed — live-verified in an isolated scratch repo with a
      genuine conflict-free merge; a merge commit with real hand-resolved conflict content (`--cc`
      non-empty, content differing from every parent) still fails the tag closed, since there's nothing
      on the default branch to verify it against — live-verified with a genuine hand-resolved 3-way
      conflict (found by Claude fresh-eyes, `cross-model-review` round 2). **Superseded 2026-09-11
      (later the same day, in a separate round from the per-path/per-blob redesign this whole block
      documents): the `--cc`-based skip itself was a real false positive, not just a to-be-improved
      mechanic — see the "a second Codex connector round" entry further below. `--cc`'s "no unique
      content" reading is blind to a merge that force-resolves to exactly one parent's state; the
      current check diffs against each parent separately (`-m`) instead of using `--cc` at all.**
- [ ] A `git diff-tree` failure (bad object, corrupted ref) is distinguished from a genuinely empty/
      trivial merge diff by checking the exit status separately from stdout emptiness — live-verified: a
      deliberately invalid commit reference produced empty stdout AND exit 128, which the fix correctly
      treats as a failure (fail closed) rather than a trivial merge (found by Codex fresh-eyes,
      `cross-model-review` round 3)
- [ ] The full `--list` sweep against this repository's real rebase-backup tags stayed consistent across
      every fix in this round (19-20 tags, depending on unrelated concurrent repo activity, correctly
      recognized as content-reachable both before and after each hardening pass; 2-3 genuinely
      unreachable tags correctly stayed flagged throughout)
- [ ] The full create → list → delete round-trip works end-to-end through the script's own index-only
      interface — live-verified with a throwaway tag: created with its branch already deleted, confirmed
      it appeared in `--list`, deleted by index, confirmed removal via a follow-up `git tag -l`

**Covered by a persisted, repeatable fixture** (flagged by Devin's automated PR review on PR #275;
addressed in the same PR rather than deferred; updated 2026-09-11 for the per-path/per-blob redesign, its
two `cross-model-review` follow-up rounds, and the two GitHub automated-review rounds below): `scripts/test-content-reachable.sh`
sources `is_path_blob_reachable`/`check_diff_records`/`is_tag_content_reachable` directly from
`delete-rebase-backup-tags.sh` -- never a hand-copied re-implementation, so it can't silently drift from
the real code -- and currently exercises 19 scenarios in isolated, throwaway git repos, covering: a
genuine rebase-merge (SHA differs, content identical) recognized as reachable; a whitespace-only
difference NOT falsely matching; a trivial merge commit not aborting the walk; a `git diff-tree` failure
(merge and non-merge) distinguished from an empty diff; the atomic compare-and-delete succeeding on a
matching oid and refusing on a stale one; content reorganized into a different commit grouping still
recognized, and that not masking a file that genuinely never landed; a parentless (root) commit's content
checked in both directions; a non-ASCII path deletion checked against `$default_branch`'s real state
rather than a mis-parsed literal string, in both directions; a mode-only change (`chmod +x`) checked in
both directions; a filename containing a pathspec metacharacter still matched literally; a deletion
check failing closed when the path's blob is unreadable, not just when the path is absent; a blob present
on `$default_branch` only before divergence not satisfying reachability; content genuinely inherited
unchanged from the merge-base still recognized; and `$default_branch`'s own genuine merge-conflict-resolution
content still recognized after the per-path history search was batched into one `git log --raw` call. Run
directly: `bash scripts/test-content-reachable.sh`. All 5 passed on the fix that shipped in PR #275; all 19
pass on the current script (see the six dated 2026-09-11 "Live results" entries above for the redesign
and each review round that grew this count from 5 to 19).

**Live results, 2026-09-11 (per-path/per-blob content-reachability redesign):** the exact-diff-text
approach above was found to have a much higher real-world failure rate than its own disclosed limitation
suggested -- not just "an unrelated part of the same file changed," but any case where the destination
branch's history reorganizes a tag commit's changes into a *different set of commits* than the tag
recorded. Live-verified against this repository's own real rebase-backup tags at the time:
- `feat/pr-ci-governance-rebase-backup-20260907-210042` -- one commit, 13 files added together. The
  matching commit on `main` (same message, found via `git log --all --grep`) carried only 12 of them; the
  13th (`.github/actions/fork-safety/action.yml`) landed via a wholly separate, later commit
  (`be72cbeb`, "vendor composite actions referenced by new label workflows"). The old exact-diff-text
  check could never match this (12-file diff ≠ 13-file diff); the new per-path check finds the exact
  blob for every one of the 13 files somewhere in `main`'s own history at that path, correctly recognizing
  the tag as content-reachable. Confirmed via `delete-rebase-backup-tags.sh --list`: this tag went from
  absent (old algorithm) to listed (new algorithm), with no other repo state change in between.
- Three other tags with 10-19 unique commits each (`feat/ci-pipeline-foundation` ×2,
  `feat-analysis-kit-new-dimensions`) remained correctly unreachable under the new algorithm too --
  spot-checked several of their reported-missing paths (e.g.
  `.github/actions/workflow-killswitch/action.yml`) and confirmed those exact blobs never appear
  anywhere in `main`'s own history at that path, even though the path currently exists there with
  different content -- genuine evidence the tag's specific content was superseded/rewritten rather than
  merely reorganized, correctly kept unreachable rather than a false negative.
- Performance: `--list` over 5 tags (one with 19 unique commits) completed in ~15s against this
  repository's real history (~3800 tracked files, hundreds of commits) -- acceptable for a manually
  triggered, interactive cleanup tool with no hot-path requirement.

**Live results, 2026-09-11 (security-reviewer follow-up on the redesign above):** a mandatory
`security-reviewer` dispatch against the redesign (per
`.claude/rules/require-security-review-before-new-gate.md` -- this redesign is a structural change to an
existing destructive-action gate's own pass/fail logic) found one Critical and two Major findings, all
verified live in an isolated scratch repo before fixing (never fixed on the reviewer's say-so alone):
- **Critical (C1):** a PARENTLESS commit (a `git subtree --squash` import, a
  `merge --allow-unrelated-histories` root, a grafted/shallow boundary commit) inside the tag's own unique
  history produced NO `git diff-tree` output at all without `--root` -- live-verified in a scratch repo
  (empty stdout, exit 0) -- which the inner loop read as "this commit changed nothing" and passed
  unverified, regardless of whether its content ever actually landed on `$default_branch`. Fixed by adding
  `--root`, which makes such a commit show its whole tree as `A` (add) entries the existing per-path check
  already handles correctly.
- **Major (M1):** the non-merge commit's own `git diff-tree` call never checked its exit status separately
  from empty output -- the exact sibling of the `cc_rc` guard the merge-commit branch already carries
  (Codex fresh-eyes finding F1, PR #275). Live-verified: corrupting a commit's own tree object (deleting
  its `.git/objects/<sha>` blob) produced empty stdout + exit 128, which the unfixed code read as "no
  changes" rather than a verification failure. Fixed by capturing the exit status separately (mirroring
  the merge branch) and failing closed on non-zero.
- **Major (M2):** the raw tab-delimited `git diff-tree` format C-quotes any path containing a non-ASCII
  byte (under the default `core.quotePath=true`) or a literal quote/backslash/control character -- that
  quoted string is not the real path. Live-verified against a real `café.txt`: `git cat-file -e
  "$default_branch:\"caf\\303\\251.txt\""` (the literal quoted form) fails as a bad revision spec
  regardless of whether the real, correctly-named file exists on `$default_branch` or not -- which the
  deletion branch's `&&` misread as "path absent," silently treating a genuinely-not-reflected deletion as
  satisfied. Fixed by switching to `-z` (NUL-delimited, unquoted) output, parsed via `read -r -d ''` into a
  temp file (a `$(...)` variable can't hold `-z` output -- a NUL byte truncates a bash string) --
  live-verified afterward: `git cat-file -e "$default_branch:café.txt"` (the real, correctly-parsed path)
  behaves correctly in both directions.
- A `trap ... RETURN` for the new temp file's cleanup was considered and rejected: bash's `RETURN` trap is
  process-wide, not scoped to one function invocation, so it would also fire when `is_path_blob_reachable`
  (called from inside the same diff-record loop) returns, unlinking the temp file while the outer loop's
  `read -r -d '' ... < "$file"` redirection might still be reading it -- harmless on Linux (unlink doesn't
  invalidate an already-open fd) but not guaranteed on the Windows/Git-Bash environment this script
  actually runs in. Used explicit `rm -f` at every return path instead, isolated to a small
  `check_diff_records` helper so the caller only needs 3 cleanup call sites rather than one per return
  inside the parsing loop.
- 5 new regression scenarios added to `test-content-reachable.sh` (12 total, up from 7): a root commit's
  content recognized when it lands, and correctly kept unreachable when it doesn't; a non-ASCII deletion
  recognized when reflected on `$default_branch`, and correctly kept unreachable when it isn't; and a
  `git diff-tree` failure on a non-merge commit failing closed. All 12 passed after the fixes; re-ran
  `delete-rebase-backup-tags.sh --list` against this repository's real remaining tags afterward and
  confirmed no regression (`feat/pr-ci-governance-rebase-backup-20260907-210042` still the only one
  listed, ~17s).
- **R20 sweep found a real, live drift this same pass:** `phase1-analysis.sh` carries its own independent
  copy of the reachability check (for Gate 1's "reachable from `<default>`: yes/no" display), explicitly
  commented "this script's report must agree with what that script would actually delete" -- it still had
  the OLD patch-id/exact-diff-text implementation, which would have kept reporting
  `feat/pr-ci-governance-rebase-backup-20260907-210042` as unreachable at Gate 1 while `--list` (already
  fixed) correctly offered it for deletion at Gate 2 -- a real, user-visible contradiction between what
  the skill displays and what it would actually do. Replaced with the same `is_path_blob_reachable`/
  `check_diff_records`/`is_tag_content_reachable` functions (kept byte-identical between the two scripts
  deliberately). Re-ran `phase1-analysis.sh` against this repository afterward and confirmed its output
  now agrees exactly with `--list`: `feat/pr-ci-governance-rebase-backup-20260907-210042` reports
  "reachable from main: yes (content match after rebase...)"; the other three multi-commit tags still
  correctly report "NO."

**Live results, 2026-09-11 (`cross-model-review` pass on the redesign + security fixes above):** run
before opening the PR, per `create-pr`'s own mandatory pre-push gate. Both Claude and Codex reviewed the
full diff independently (Phase 1), then each cross-examined the other's findings (Phase 2) — no
single-model fallback, full two-model run both phases.
- **Confirmed (High confidence, both sides): mode-only changes weren't verified.** Codex fresh-eyes found
  that `check_diff_records` discarded both mode fields from the raw diff-tree record, and
  `is_path_blob_reachable` compared blob identity only — a tag commit whose only change was `chmod +x`
  (or a file/symlink swap with byte-identical content) would be reported "content-reachable" even if that
  mode change never landed on `main`. Claude's Phase 2 pass independently re-derived the same code-level
  facts and confirmed it, additionally correcting the severity: this session's own earlier
  `security-reviewer` dispatch had filed the identical gap as informational ("no blob content is lost"),
  but the whole point of this check is whether the tag's content is genuinely present elsewhere, and a
  mode change is content the tag captured — Major, not informational, is the accurate severity. Fixed by
  capturing `new_mode` from the raw diff-tree record (previously discarded) and switching
  `is_path_blob_reachable`'s acceptance test from `git rev-parse "$commit:$path"` (blob only) to
  `git ls-tree "$commit" -- "$path"` (mode + blob together, requiring both to match).
- **Confirmed (High confidence, both sides): non-literal pathspec matching.** Claude fresh-eyes found
  that `git rev-list "$default_branch" -- "$path"` treats `$path` as a pathspec, not a literal string —
  a real filename containing `*`, `?`, or `[` could be glob-interpreted. Codex's Phase 2 pass
  independently confirmed it and agreed it's safe-direction only (the actual acceptance check right
  after is an exact literal-path lookup, so this could only ever cause a spurious "needs manual review,"
  never a false "safe to delete"). Fixed with `export GIT_LITERAL_PATHSPECS=1` once near the top of both
  scripts (rather than patching every individual pathspec argument), live-verified in a scratch repo
  before applying it: an unquoted `release*txt.txt` pathspec matched an unrelated `releaseXtxt.txt` file
  without the env var, and matched nothing (correctly) with it set.
- Both findings were user-approved for fixing (not deferred) before the PR was opened. 3 new regression
  scenarios added to `test-content-reachable.sh` (15 total, up from 12): a mode-only change recognized
  when reflected on `$default_branch`, and correctly kept unreachable when it isn't; and a filename
  containing a pathspec metacharacter (`release[1].txt`) still correctly matched under
  `GIT_LITERAL_PATHSPECS=1`. The mode-change scenarios use `git update-index --chmod=+x` rather than a
  real filesystem `chmod` — this repository's own `core.filemode=false` default (typical on Windows/NTFS,
  which has no real POSIX executable bit) makes a real `chmod` invisible to git entirely;
  `update-index --chmod` forces the mode directly in the index regardless of platform, live-verified
  before writing the fixture. All 15 passed after the fixes; re-ran `delete-rebase-backup-tags.sh --list`
  against this repository's real remaining tags afterward and confirmed no regression
  (`feat/pr-ci-governance-rebase-backup-20260907-210042` still the only one listed).

**Live results, 2026-09-11 (`cross-model-review` round 2, on the mode-tracking/literal-pathspec fix
above):** re-run per the skill's own re-commit-then-re-review loop, since the round 1 fix was itself a
code change to the diff being reviewed.
- **Confirmed (High confidence): the deletion branch's own object-read failure wasn't distinguished from
  genuine absence.** Codex fresh-eyes found that `check_diff_records`' deletion check,
  `git cat-file -e "${default_branch}:${path}" 2>/dev/null && return 1`, fails (nonzero exit) both when
  the path is genuinely absent from `$default_branch` AND when the path still exists there but its blob
  object is missing or corrupted — the two cases are indistinguishable by exit code alone, and the `&&`
  silently treated both as "deletion satisfied." Live-verified before fixing: deleting a blob object out
  from under an otherwise-intact tree entry made `cat-file -e` fail while the path was still genuinely
  present, and the old code read that failure as a clean pass. This is the exact same anti-pattern
  (`cc_rc`, the non-merge `diff_rc` check) already fixed twice elsewhere in this same diff, just missed
  in the one remaining place it applied — a real instance of exactly what
  `.claude/rules/require-tests-for-behavior-changes.md`'s "Fix Completeness: Sweep Sibling Occurrences"
  section warns against. Fixed by switching to `git ls-tree "$default_branch" -- "$path"`, which never
  needs to open the blob at all to answer "does this path exist in the tree" — live-verified separately:
  it returns exit 0 with the entry still listed even when that same blob is deleted, and exit 0 with
  empty output only when the path is genuinely absent; a nonzero exit means `$default_branch` itself
  couldn't be read (a bad ref or corrupted root tree), which now fails closed the same way the non-merge
  `diff-tree` call already does.
- 1 new regression scenario added to `test-content-reachable.sh` (16 total, up from 15): a deletion
  record's verification fails closed when the path's blob is unreadable, not just when the path is
  absent — built by corrupting a real blob object out from under an otherwise-intact tree entry, mirroring
  the live-verification technique used to find the bug itself. All 16 passed after the fix; re-ran
  `delete-rebase-backup-tags.sh --list` against this repository's real remaining tags afterward and
  confirmed no regression.
- Claude's own Phase 1 pass on this round reported no findings (`verdict: approve`) — the only finding
  this round came from Codex fresh-eyes, confirmed independently (Claude re-derived the same code-level
  facts and live-verified them before accepting the finding, rather than trusting Codex's report alone).
  A third round then had both models converge on zero findings, closing the `cross-model-review` loop.

**Live results, 2026-09-11 (GitHub's own automated PR review, after the PR was opened):** `cross-model-review`
only ever reviews the local working diff before a PR exists (see that skill's own "When NOT to Use") — once
PR #315 was opened, GitHub's own automated reviewers (the Codex connector, CodeRabbit, Devin) ran
independently against the pushed commits, per `handling-review-findings`. Two real findings surfaced, both
verified live before fixing rather than accepted on the reviewer's say-so:
- **Confirmed (the Codex connector, P1 — the most serious defect found across this entire fix): the
  history search had no lower bound at all.** `is_path_blob_reachable` searched `$default_branch`'s
  *entire* history for a matching blob+mode, with no restriction to commits at or after the tag's own
  divergence point. This is a genuine false positive, not a safe-direction limitation like the other
  findings in this file: a path added then deleted from `$default_branch` entirely BEFORE a tag's branch
  even existed, then coincidentally re-added with byte-identical content on that branch, matches the stale
  PRE-divergence blob and gets reported "reachable" even though `$default_branch` never actually restored
  it after diverging -- live-reproduced exactly as the reviewer described before fixing: added `data.txt`
  on `main`, deleted it, branched off, re-added identical `data.txt` on the branch, deleted the branch --
  confirmed the unbounded search reported the resulting backup tag reachable while `main` never contained
  the file post-divergence. Fixed by passing the tag's own merge-base (`$mb`, already computed in
  `is_tag_content_reachable`) down through `check_diff_records` into `is_path_blob_reachable`, which now
  checks `$mb`'s own tree directly first (content already present at the shared ancestor is inherited by
  `$default_branch` automatically, even if no commit strictly after `$mb` ever touches that path again --
  live-verified separately with a tag that modifies a path then reverts it back to `$mb`'s own original
  content, confirming excluding `$mb` from the search would introduce a *new* false negative), then walks
  only `$mb..$default_branch` for everything else.
- **Confirmed (the Codex connector, P2): the mode-change test fixtures were not portable to Linux CI.**
  `new_repo()` never set `core.filemode`, so the mode-change scenarios' `git update-index --chmod=+x`
  behaved differently depending on the host's own default -- harmless on this repository's own
  Windows/NTFS machine (`core.filemode=false`, no real POSIX executable bit to compare against), but on a
  host where `core.filemode` defaults to `true` (typical on Linux/ext4, i.e. this repository's own GitHub
  Actions runners), the index-only mode change leaves the working-tree file's real permission bits
  mismatched, and the very next `git checkout` to switch branches refuses due to that apparent local
  modification. Live-verified: forcing `core.filemode=true` on an already-built scratch repo from this
  suite made `git status` immediately report the mode-changed file as modified; forcing it back to `false`
  (matching the fix, applied in `new_repo()` before any of the scenario logic runs) confirmed clean.
- 2 new regression scenarios added to `test-content-reachable.sh` for the P1 fix (18 total, up from 16): a
  blob present on `$default_branch` only before divergence does not satisfy reachability, and content
  genuinely inherited unchanged from the merge-base is still recognized (the second scenario required
  isolating the merge-base fast path from the unrelated "every commit's own content must independently be
  reachable" requirement -- an earlier draft of this fixture masked the very thing it meant to test by
  conflating the two, caught before persisting it by actually running it against the real function rather
  than reasoning about it in the abstract). P2's fix needed no new scenario -- it's a fixture-environment
  correctness fix, not new behavior to cover. All 18 passed after both fixes; re-ran
  `delete-rebase-backup-tags.sh --list` against this repository's real remaining tags afterward and
  confirmed no regression (`feat/pr-ci-governance-rebase-backup-20260907-210042` still the only one listed).

**Live results, 2026-09-11 (CodeRabbit nitpick: batch the per-commit `git ls-tree` loop):** requested by
the user after triaging the round above; not gated on `review_findings_severity_gate` (this repo's
default is `false` -- every finding gets fixed regardless of severity -- and the user explicitly asked
for it regardless).
- **The naive version of this optimization has a real correctness trap, caught before shipping it.**
  CodeRabbit's own suggested replacement -- `git log --raw -z --root` in place of the per-commit
  `git ls-tree` loop -- silently drops a genuine match for any merge commit with real hand-resolved
  conflict content: `git log --raw` (unlike `git ls-tree`, which reads a commit's final tree directly)
  shows nothing at all for a merge commit's own diff unless given `-m` (or `--cc`), since a merge has no
  single parent to diff against by default. Live-verified in an isolated scratch repo before writing the
  fix: a real 2-way conflict, resolved and committed, produced zero raw records under plain `--raw`, and
  correct records under `-m`. This exact pattern (a merge commit silently reads as "nothing changed" via
  a diff-based tool where a tree-based one wouldn't have that blind spot) is the same shape as this
  file's own C1/M1 findings from earlier rounds -- caught here by testing the actual git behavior first,
  per `.claude/rules/verify-tool-behavior-before-instructing.md`, rather than trusting the reviewer's
  one-line suggestion or its own auto-generated "prompt for AI agents" text (which didn't mention merge
  commits at all).
- **A second, independent gotcha found only by running the change against the existing test suite:**
  `git log --raw`'s default raw-format object names are ABBREVIATED (short), unlike `git diff-tree`'s
  raw format (already used everywhere else in this file), which defaults to FULL 40-char hashes with no
  extra flag needed. The first version of this fix (missing this) broke 7 of the 18 existing regression
  scenarios -- every blob comparison silently failed for the wrong reason, since a 7-char abbreviated
  hash can never equal the full `$wanted_blob` this function receives. `--full-index` (the flag
  `git diff`/`git diff-tree` themselves document for exactly this purpose) was tried first and found NOT
  sufficient for `git log` specifically -- `--no-abbrev` is the flag that actually works there, found by
  testing each in isolation rather than assuming the documented `diff`/`diff-tree` flag would transfer.
- **Performance verified with a controlled, back-to-back A/B comparison** (not a single before/after
  timing, which this repository's own shared, concurrently-active state makes noisy) -- same shell
  session, same 5 real tags, old and new implementations run back to back, twice each: old ~20.2-20.4s,
  new ~14.6-15.9s, a consistent ~25-30% improvement both times.
- 1 new regression scenario added to `test-content-reachable.sh` (19 total, up from 18): a merge commit
  on `$default_branch`'s own side (not the tag's) with genuine hand-resolved conflict content is still
  found by the batched search. All 19 passed after the fix; re-ran `delete-rebase-backup-tags.sh --list`
  and `phase1-analysis.sh` against this repository's real remaining tags afterward and confirmed no
  regression -- both scripts' output stayed identical to every prior round.

**Live results, 2026-09-11 (a second Codex connector round, on the just-merged CodeRabbit-nitpick
commit): the `--cc`-based merge-commit skip inside `is_tag_content_reachable` itself had the exact
same "empty diff misread as safe-to-skip" blind spot the earlier rounds in this file already fixed
elsewhere, just in a place none of them touched.**
- **Confirmed (the Codex connector, P1 on commit `bd9ea5de4c`): a merge inside the tag's own history
  that force-resolves to exactly ONE parent's state for a path is invisible to `--cc`, even when that
  represents real content loss relative to the OTHER parent.** The original (PR #275) merge-commit
  handling used `git diff-tree --cc`, which only shows a path that differs from EVERY parent, and
  treated an empty `--cc` diff as "this merge contributes nothing new, skip it" -- correct for a
  genuinely trivial merge, but not for a merge that discards content matching one parent exactly, since
  that case is *also* `--cc`-empty by `--cc`'s own definition. Three scratch-repo constructions were
  needed to isolate this cleanly before fixing: the first two were each masked by a confound (the
  dropped content's own standalone commit was independently caught by the existing per-parent walk in
  one case; an unrelated unreachable change on the same branch in the other) -- the third finally
  isolated it: one parent (`main`) adds a file in its own commit; the other parent is a divergent branch
  with only an `--allow-empty` commit (zero real content changes of its own, so nothing else in the walk
  can catch it); the tag's own merge is forced (`git rm` before committing) to drop the file, exactly
  matching the empty-change parent's tree. `--cc` reported no diff at all; `main` still had the file the
  merge discarded. Fixed by replacing the `--cc`-based special case with the same `-m` (per-parent raw
  diff) technique already used elsewhere in this file (`is_path_blob_reachable`'s batched search): `-m`
  is a no-op for a non-merge commit (verified identical output with and without it) but makes a merge
  commit show a full diff against EACH parent separately, so a path that matches one parent exactly but
  differs from the other still produces a record -- which then flows through the existing
  `check_diff_records`/`is_path_blob_reachable` machinery exactly like any other path change, with no
  special-casing left for merges at all. This also removes the earlier "a merge with real
  conflict-resolution content has no single path's before-state to diff against, fail closed" limitation
  entirely -- `-m`'s per-parent diff already resolves an unambiguous pre-image per parent, so that content
  is now verified rather than unconditionally rejected.
- 1 new regression scenario added to `test-content-reachable.sh` (20 total, up from 19):
  `scenario_merge_resolves_to_one_parent_content_loss_fails_closed`, reproducing the isolated
  scratch-repo construction above -- built on a separate branch from the tag's own merge (never merged
  back into `main` directly), the same construction pitfall `scenario_bad_ref_fails_closed`'s own
  comment already documents (merging directly into `main` collapses the merge-base to the tag's own tip,
  making the check pass trivially for the wrong reason regardless of whether the fix works). Re-ran the
  existing `scenario_trivial_merge_skipped` (a genuinely trivial merge, no unique content from either
  side) and `scenario_bad_ref_fails_closed` (a corrupted merge tree) to confirm the `-m` unification
  doesn't regress either: both still pass, since `-m` produces zero records for a genuinely trivial merge
  and `git diff-tree -m` still fails non-zero (fails closed) when the merge's own tree object is
  unreadable, exactly as the old `--cc` call did. All 20 passed after the fix; re-ran
  `delete-rebase-backup-tags.sh --list` and `phase1-analysis.sh` against this repository's real remaining
  tags afterward and confirmed no regression -- both scripts' output stayed identical to every prior
  round.

**Live results, 2026-09-12 (issue #317: content merged in a different commit order):** found live during a
real `/git-cleanup` run after PR #315 merged -- 5 rebase-backup tags were left for manual review;
investigating one (`feat-analysis-kit-new-dimensions-rebase-backup-20260910-194109`) found a false negative
distinct from every gap fixed above.
- **Root cause: per-commit blob matching has no notion of a path's own FINAL state, only each individual
  commit's own post-image.** `is_tag_content_reachable` requires every one of the tag's own unique
  commits to have its own per-path post-image blob independently found somewhere in `$default_branch`'s
  history. When the tag's own branch merges `$default_branch` back in mid-development and keeps editing
  the same path, an EARLIER commit's blob reflects only that commit's own partial edit -- without content
  a LATER commit in the same tag branch went on to incorporate -- and `$default_branch`'s own history may
  never pass through that same intermediate, partial state, even though the tag's FINAL state for that
  path is byte-identical to `$default_branch`'s current content. Live-verified against the real tag above:
  its blocking commit `c4690df1`'s own post-image blob for `.codacy.yml` never appears anywhere in main's
  `.codacy.yml` history (main added the same two pieces of content in the opposite order), yet the tag's
  FINAL `.codacy.yml` (at its tip) diffed byte-identical against main's current `.codacy.yml`.
- **Fix:** `is_path_blob_reachable` now takes the tag name as a fifth parameter (threaded down through
  `check_diff_records` and `is_tag_content_reachable`, the same parameter-threading pattern `$mb` already
  used for the pre-divergence-blob fix above) and, before falling through to the existing per-commit
  history search, checks a shortcut first: if the tag's own tip blob+mode for this path already matches
  `$default_branch`'s CURRENT blob+mode for the same path, the commit under test is satisfied regardless
  of what its own individual blob was -- whatever content that commit introduced was itself superseded by
  a later commit within the tag's own history, and it's the tag's FINAL contribution for the path that
  would actually be lost by deleting the tag, not any intermediate state along the way. This is
  purely additive (an early-return before the existing search, never a replacement of it) and
  safe-direction-only: it can only turn a false "not reachable" into a correct "reachable" when the exact
  final blob+mode genuinely match; it can never mask a genuine mismatch, since the shortcut requires an
  exact blob+mode match at the CURRENT tip, not a fuzzy or historical one.
- **Sibling-occurrence sweep (`.claude/rules/require-tests-for-behavior-changes.md`): `phase1-analysis.sh`
  carries an intentional, comment-disclosed duplicate of these same three functions** (Phase 1's own
  reporting pass, run before Phase 3.6's actual deletion proposal) -- grepping for the same anti-pattern
  signature found it still had the pre-fix per-commit-only logic, which would have left Phase 1's own
  reported "reachable from main: NO" verdict silently disagreeing with `--list`'s now-corrected output for
  the same tag. Applied the identical parameter-threading and shortcut fix there too, mirroring the
  existing "see delete-rebase-backup-tags.sh's identical comment" cross-reference convention this
  duplicate already uses instead of restating the full rationale a second time.
- **Verified against this repository's own real tag set** (8 rebase-backup tags present, 2026-09-12):
  before the fix, `--list` reported only 1 of 8 as deletable
  (`fix/git-cleanup-rebase-tag-content-reachability-rebase-backup-20260911-232051`), and `phase1-analysis.sh`
  reported the same 1 of 8 as `reachable from main: yes`. After the fix, both scripts agree: 3 of 8 are
  reachable/deletable -- the same tag plus 2 new ones (`feat-analysis-kit-new-dimensions-rebase-backup-20260910-194109`,
  the exact tag #317 was filed from, and `feat/ci-pipeline-foundation-rebase-backup-20260907-143553`). A
  per-tag diagnostic pass (comparing the old per-commit-only result against the new shortcut for every
  failing path) confirmed the other 5 tags' failures are genuine content mismatches, not additional
  instances of this bug -- the shortcut correctly declines to fire for any of them (fail-closed preserved).
- 2 new regression scenarios added to `test-content-reachable.sh` (22 total, up from 20):
  `scenario_reordered_final_state_recognized` (a positive case reproducing the exact bug shape: an
  earlier tag commit's own intermediate blob never appears in `$default_branch`'s history, but the tag's
  FINAL blob for that path matches `$default_branch`'s current content exactly) and
  `scenario_reordered_final_state_mismatch_fails_closed` (the negative counterpart -- confirms the
  shortcut doesn't overreach when the final states genuinely don't match). Sanity-checked
  `scenario_reordered_final_state_recognized` against the pre-fix function bodies (extracted via the same
  `git show HEAD:...` + sed-range technique this suite already uses) and confirmed it correctly reports
  "not reachable" there, proving the new scenario actually exercises the bug rather than passing
  vacuously. All 22 scenarios passed after the fix.

**Live results, 2026-09-12 (the final-state shortcut above was REVERTED, same day, before ever
shipping): a mandatory pre-push `cross-model-review` pass found it unsafe.** This fix, and the
guided-manual-review feature built alongside it (Phase 7, see this file's own later entry), were both
about to be pushed together when Codex's fresh-eyes Phase 1 pass (dispatched via `cross-model-review`,
high confidence) raised a Major correctness finding against the shortcut above.
- **The finding:** `is_path_blob_reachable`'s shortcut accepted ANY commit's blob as reachable purely
  because the TAG'S OWN tip blob for that path matched `$default_branch`'s current blob -- without ever
  checking whether the specific commit's own `wanted_blob` had any relationship to that tip blob at all.
  Concretely: a tag whose unique history adds UNIQUE content to a path, then REVERTS that same path back
  to `$default_branch`'s own untouched original content in a LATER commit, has a tip that trivially
  matches `$default_branch` -- but the reverted-away unique content was never on `$default_branch` in any
  form and would become permanently unreachable (eventually garbage-collected) once the tag is deleted.
  This is a genuine false POSITIVE ("safe to delete" when it isn't) -- strictly worse than #317's own
  false-negative bug, which only produced an unnecessary manual-review prompt, never data loss.
- **Live-verified before reverting**, in an isolated scratch repo mirroring the exact finding: a tag adds
  `SECRET-CONTENT` to `secret.txt`, then a later commit in the same tag reverts it to `original`;
  `$default_branch` never touches `secret.txt` at all. Confirmed `--list` reported this tag as
  automatically SAFE TO DELETE before the revert, and correctly moved it to `--list-review` ("needs
  review") after.
- **No safe narrowing was found that preserves both properties.** Restricting the shortcut to only fire
  when a commit's own blob equals the tag's own tip blob for that path (the only version that provably
  can't also be a discarded intermediate) closes the false positive -- but that restriction makes the
  shortcut fire exclusively for whichever commit is literally the LAST to touch a path, which the
  pre-existing `mb`-tree check and `mb..$default_branch` history search already cover on their own. #317's
  own scenario specifically requires validating an EARLIER, non-final commit's blob (`c4690df1`, superseded
  within the tag by a later merge) -- exactly the case a safely-narrowed shortcut can no longer help with.
  Distinguishing "superseded on the way to an equivalent final state" from "discarded via an unrelated
  revert" would require actual content/diff analysis, a deliberate departure from this file's
  long-standing, extensively-defended commitment to blob-identity-only comparison (see the file's own
  historical rejection of a patch-id-based approach for the same reason).
- **Fix: fully reverted** -- `is_path_blob_reachable`/`check_diff_records`/`is_tag_content_reachable` are
  back to their pre-#317-session per-commit-only form (including removing the now-unused `tag` parameter
  threading) in both `delete-rebase-backup-tags.sh` and `phase1-analysis.sh`. `#317`-shaped tags once again
  report "needs review" via `--list-review`, exactly as before this session -- but are now actually
  actionable, via Phase 7's guided-manual-review feature (a human reviews `--diff`'s real evidence and
  decides `--force`/`--keep`), which is arguably the correct tool for this class of case regardless: no
  blob-identity-only automation can safely distinguish it from Codex's counter-example, but a human looking
  at the actual diff can.
- **Regression suite updated to match** (still 31 scenarios total, alongside Phase 7's own additions --
  see that entry below): `scenario_reordered_final_state_recognized` renamed to
  `scenario_reordered_final_state_not_auto_recognized` and its assertion inverted (now proves #317's own
  case correctly fails closed with no shortcut); `scenario_reordered_final_state_mismatch_fails_closed`
  removed (redundant once there's no shortcut left to guard against overreaching); new
  `scenario_self_reverted_unique_content_fails_closed` added, locking in Codex's exact counter-example as
  a permanent regression guard against ever reintroducing this specific class of false positive. All 31
  passed after the revert; re-verified against this repository's own real tags afterward --
  `feat-analysis-kit-new-dimensions-rebase-backup-20260910-194109` (the actual #317 tag) is back under
  `--list-review`, not `--list`.

**Live results, 2026-09-13 (a fresh cross-model-review pass, run again after the revert above, per this
skill's own re-commit-then-re-review requirement -- found a second, unrelated, real bug in the same
file):** Codex's fresh-eyes Phase 1 pass on the corrected diff (high confidence) flagged a `set -euo
pipefail` interaction neither the original security-reviewer pass nor this session's own re-review of the
revert had caught.
- **The finding:** under this script's own `set -euo pipefail`, a bare `var=$(cmd)` assignment with no
  `||` fallback makes the WHOLE ASSIGNMENT STATEMENT's exit status equal to `cmd`'s own exit status --
  and if that's non-zero, `set -e` triggers immediate script exit *right there*, before any following
  line (a `[ -z "$var" ]` check, or a separate `rc=$?` capture) ever runs. Flagged in `--force`/`--keep`'s
  `current_oid`/`current_dsha` resolution (lines 760-761/825-826 at the time) -- exactly the "Skipped"
  graceful-degradation path those functions document as their own intended behavior, made unreachable.
- **Live-verified before fixing**, in an isolated scratch repo: built a genuine rebase-backup tag,
  ran `--list-review`, then deleted the tag entirely (simulating a concurrent deletion) before calling
  `--force 1` -- confirmed the script died with exit 128 and **zero output**, never printing the
  documented `Skipped '<tag>': could not resolve its current object id` message at all.
- **Sibling-occurrence sweep found 5 total instances**, not just the 2 Codex flagged -- 2 more introduced
  by this same session's own new code (`list_review`'s `item_sha`, and this session's own C1 fix for
  `--diff`'s `diff_out`/`diff_rc` -- meaning the C1 fix's own exit-status check was *itself* dead code
  from the moment it shipped, an ironic instance of the exact anti-pattern C1 was written to guard
  against), and 3 in PRE-EXISTING code predating this session entirely (`check_diff_records`'s `del_out`,
  `is_tag_content_reachable`'s `tag_commits`, and the plain `--list`/`<index>` delete loop's
  `pre_check_oid` -- live-verified this last one too: a multi-index `--list`/delete call died on the
  *first* already-gone tag and silently never processed any later index in the same call, despite this
  loop's own comments explicitly documenting one-failure-doesn't-block-the-rest as its intended design).
  User explicitly approved fixing all 3 pre-existing instances in this same PR rather than deferring them
  (asked via `AskUserQuestion`, since they predate this session's diff).
- **Fix:** each bare assignment now either appends `|| var=""` (when the caller only needs an
  empty-vs-non-empty check afterward: `list_review`'s `item_sha` uses `|| continue` instead, since the
  intended behavior there is to skip a tag that vanished mid-enumeration entirely, not emit a snapshot row
  with a blank oid) or uses `cmd && rc=0 || rc=$?` (when the caller needs the *actual* exit code
  preserved, as in `--diff`'s `diff_rc` and `check_diff_records`'s `del_rc`) -- both forms make the whole
  compound statement's own exit status always 0, so `set -e` never fires regardless of whether the
  underlying git command succeeded or failed, while still letting the existing downstream check see the
  real result.
- **1 new regression scenario** added (32 total, up from 31):
  `scenario_plain_delete_skips_already_gone_tag_and_continues`, invoking the real CLI (`--list` then a
  multi-index delete) rather than the extracted functions, since the bug lives in the CLI's own delete
  loop. Sanity-checked against the pre-fix script (extracted via the same `git show HEAD:...` technique
  this suite already uses): confirmed it dies with exit 128 and zero output, proving the scenario
  genuinely exercises the bug rather than passing vacuously. All 32 scenarios passed after the fix.

**Live results, 2026-09-13 (a third cross-model-review pass, run again after the F1 fix above, per this
skill's own re-commit-then-re-review requirement -- found a third, unrelated, real bug in `--diff`
mode):** Claude's own fresh-eyes pass on this round's diff (the F1 fix commit itself) found nothing --
re-swept every bare `var=$(cmd)` assignment in the file and confirmed no instance remained without a
fallback. Codex's fresh-eyes Phase 1 pass (Major, correctness, high confidence) flagged a gap this
sweep didn't cover, since it isn't a `set -e` issue at all: `--diff`'s merge-base handling.
- **The finding:** `mb=$(git merge-base -- "$oid" "$default_branch" 2>/dev/null) || mb=""` already fails
  gracefully when no common ancestor exists (an orphan branch, a grafted/shallow boundary, or an
  unrelated-histories merge root) -- but the "unique commits" section it gates was silently skipped with
  no explanation, and the tree-content diff below it still ran regardless (a tree comparison needs no
  common ancestor at all, so it isn't itself the bug). If that diff then came back empty -- the two trees
  happen to be byte-identical despite sharing no history whatsoever -- the only thing a human reviewer
  saw was an unqualified `(no differences -- this candidate's tree matches $default_branch's current
  tree exactly)` message, with nothing to signal that ancestry itself could never be established for
  this candidate -- exactly the kind of anomalous, unrelated-history case this same file already treats
  with extra scrutiny elsewhere (the `--root` handling for parentless commits, and `security-reviewer`'s
  original C1 finding about it).
- **Live-verified before fixing**, in an isolated scratch repo: created a real orphan branch
  (`git checkout --orphan`) with a tree byte-identical to `main`'s, tagged it as a rebase-backup
  candidate, confirmed `git merge-base` genuinely fails (exit 1, no common ancestor), confirmed the tag
  correctly lands in `--list-review` (the automated `is_tag_content_reachable` check already fails closed
  on the same merge-base failure), then ran `--diff 1` against the pre-fix script and confirmed it
  printed only `(no differences -- this candidate's tree matches main's current tree exactly)` with zero
  indication anything unusual was going on.
- **Fix:** the `else` branch of the merge-base check now prints an explicit `Warning: no common ancestor
  found with $default_branch -- ...` to stderr before falling through to the content diff, and the
  `(no differences ...)` message itself grows a conditional caveat ("...but see the no-common-ancestor
  warning above before treating that as sufficient evidence") when `$mb` was empty. The underlying content
  diff is unchanged -- it was already correct, valid evidence; only the missing disclosure was the bug.
  `phase1-analysis.sh` has no `--diff`-equivalent evidence-display mode (only the automated
  `is_tag_content_reachable` check, whose own `|| return 1` on the same merge-base call already fails
  closed correctly) -- confirmed via a targeted grep before ruling out a sibling instance there, not
  assumed.
- **1 new regression scenario** added (33 total, up from 32): `scenario_diff_warns_on_no_common_ancestor`,
  building a real orphan-branch tag with an identical tree to the default branch and asserting `--diff`'s
  output contains both the new warning and the no-differences message together. Re-verified live against
  the fixed script (warning now appears) before adding the scenario. All 33 scenarios passed after the
  fix.

**Live results, PR #322 round 1 (2026-09-13, `handling-review-findings` triaging Codex's + CodeRabbit's
automated PR reviews):** 4 findings, all live-verified before fixing, all fixed in the same round.
- **F1 (Critical, Codex P1 + CodeRabbit Critical):** `--list-review` overwrote the shared
  `$REVIEW_SNAPSHOT` with no generation/version stamp. Live-reproduced: two orphan-tag candidates at
  indices 1/2, then a third candidate added and `--list-review` re-run (simulating a concurrent
  invocation), then the original index-1 tag removed and `--list-review` re-run again -- index 1 silently
  resolved to a completely different tag than the one first shown. The existing atomic oid compare-and-
  delete couldn't catch this -- it validates the CURRENT snapshot's own row, which is internally
  consistent by construction; the race is about whether a human's own memory of "index N" still matches
  the CURRENT snapshot's row N, not whether row N itself is stale. **Fix:** `--list-review` now generates
  a random token (timestamp + PID + two `$RANDOM` draws -- a staleness fingerprint, not a security
  boundary, and never derived from or composed with a raw tag name) written to
  `$REVIEW_SNAPSHOT.generation` and printed as a `# Generation: <token>` header line; `--diff`/`--force`/
  `--keep` all now require a matching `--generation <token>` argument, refusing outright (exit 1) on any
  mismatch or missing generation file. Live-verified after the fix: the old token from before a
  `--list-review` re-run is correctly refused, the new token correctly succeeds, and a `--force` call
  with no `--generation` flag at all gets a clean usage error rather than silently proceeding.
- **F2 (Major, Codex P1 + CodeRabbit Minor):** `--diff` re-resolved the current `$default_branch` for its
  `merge-base`/heading/`diff` calls instead of using the snapshot's own recorded `dsha` (read into a
  discarded `_d` variable). Live-reproduced: the SAME `--diff 1` call against the SAME unchanged snapshot
  produced DIFFERENT evidence before and after `$default_branch` advanced -- a rename-detected diff
  instead of the original new-file diff, with no new `--list-review` in between. **Fix:** capture `dsha`
  into a real variable and use it throughout `--diff`'s git calls instead of `$default_branch`; the
  printed heading now shows `$default_branch @ <dsha prefix> (as recorded by --list-review)` to make the
  pinning explicit. Live-verified after the fix: the identical `--diff` call now produces identical
  output before and after `$default_branch` advances, as long as no new `--list-review` ran.
- **F3 (Major, Codex P1):** `--diff` gave no signal when a review candidate's final tree matched
  `$default_branch` exactly for reasons other than the already-covered no-common-ancestor case. Codex's
  own framing was narrower (self-reverted content within a single tag) -- live-verified with the exact
  `scenario_self_reverted_unique_content_fails_closed` fixture: the unique-commit list DOES show both the
  add and revert commits, so the evidence isn't literally hidden, but a human skimming one-line commit
  subjects rather than full diffs could easily miss it. **Fix, broadened beyond Codex's own framing:**
  every candidate reaching `--diff` at all already failed the automated `is_tag_content_reachable` check
  by construction, so an exact final-tree match is ALWAYS evidence the automated walk couldn't verify
  something, not just in the self-revert case -- issue #317's own reordered-commit-grouping case produces
  the identical symptom. Added a general caution note (`Note: this candidate reached manual review
  because the automated check could not verify it...`) whenever `diff_out` is empty and `mb` resolved
  (the no-common-ancestor branch already has its own separate warning).
- **F4 (Minor, Codex P2 + CodeRabbit Minor/quick-win):** `$DECISIONS_FILE` relied entirely on this SOURCE
  repo's own `.gitignore` (`**/*.local.*`) to stay untracked -- but git-kit is a DISTRIBUTED plugin, and a
  consumer repo installing it has no such rule of its own. First live-verification attempt gave a false
  negative (the file showed as ignored) because this machine's own personal global `core.excludesfile`
  (`~/.gitignore_global`) happens to ignore `.claude/` outright -- re-verified with `GIT_CONFIG_GLOBAL=
  /dev/null`/`GIT_CONFIG_SYSTEM=/dev/null` (a true foreign-environment simulation, no personal machine
  config involved): `git add -A` staged the decision file. **Fix:** `--keep` now also appends a per-repo
  `info/exclude` entry (`git rev-parse --git-path info/exclude`, never a tracked `.gitignore` change,
  idempotent) the first time it creates `$DECISIONS_FILE`, keeping the file's already-deliberate
  working-tree location (see the script's own comment on that decision) while closing the gap for every
  repo this script actually runs in, not just this one.
- **4 new regression scenarios** added (37 total, up from 33): `scenario_generation_mismatch_refuses`,
  `scenario_diff_pinned_to_snapshot_dsha_not_live_branch`,
  `scenario_diff_notes_reachability_check_failure_on_empty_diff`, and
  `scenario_keep_protects_decisions_file_via_info_exclude` -- one per fix above, each built from the same
  live-reproduction fixture used to verify the finding was real in the first place. The ~9 pre-existing
  scenarios that call `--diff`/`--force`/`--keep` were also updated to capture and pass the new generation
  token via a new shared `list_review_generation()` helper. All 37 scenarios passed after the fixes.

**Live results, PR #322 round 2 (2026-09-13, `handling-review-findings` triaging Codex's fresh review
of the round-1 fix commit):** 2 findings, both live-verified before fixing, both fixed in the same
round.
- **F1 (Critical):** round 1's own generation-token fix (above) wrote `$REVIEW_SNAPSHOT` and a separate
  sibling `$REVIEW_SNAPSHOT.generation` file as two SEPARATE, non-atomic writes. Codex found the exact
  race this left open: if a SECOND `--list-review` successfully overwrites the snapshot but is
  interrupted before it reaches its own generation-file write, the OLD generation file still holds a
  token from an EARLIER run, which now matches the CURRENT (already-replaced) snapshot content purely
  by coincidence of the write ordering. Live-reproduced: captured token A from run 1, then manually
  replayed exactly the interrupted-write sequence (overwrote the snapshot file's content the way a
  second run would, left the generation file untouched) -- `--diff --generation A 1` against the
  REPLACED snapshot succeeded (exit 0) and returned evidence for a completely different tag than the
  one token A was originally issued for. **Fix:** the generation token is now embedded as
  `$REVIEW_SNAPSHOT`'s own first NUL-terminated field, written to a temp file together with the
  tag/oid/dsha triples and moved into place with a single atomic `mv` (the same mktemp-then-mv pattern
  already used for `$DECISIONS_FILE`) -- no separate file, no two-write window for this class of race
  to occur in at all. `require_generation_token()` and all three read loops (`--diff`/`--force`/
  `--keep`) updated to read the embedded field (a leading `read` before the triples loop, both sharing
  one input redirection on the surrounding block so the stream position carries over correctly).
- **F2 (Minor):** `guided-manual-review.md`'s own Step 2 said "If `--list-review` returns anything,
  ask..." -- but `--list-review` always prints its `# Generation: <token> -- ...` header line, even
  with zero review candidates, so that condition is unconditionally true on every invocation.
  Live-verified: a repo with no rebase-backup tags at all still produced non-empty `--list-review`
  output (the header line alone). **Fix:** Step 2 now checks for at least one numbered candidate row
  (a line matching `<digit(s)><TAB><tag>`), not merely non-empty output.
- **1 new regression scenario** added (38 total, up from 37):
  `scenario_generation_embedded_atomically_no_sibling_file`, confirming the file-layout guarantee
  directly (no sibling `.generation` file, the embedded field matches the printed token, `--diff` still
  works normally) -- a genuine interrupted-syscall reproduction isn't something a test script can
  construct, since the whole point of atomicity is that there's no observable partial state to
  construct; the file-layout check is the strongest available proxy. F2's fix is documentation-only (the
  script's own always-print-the-header behavior is correct and unchanged) -- no script-level regression
  scenario needed; the live-verification above stands as its own evidence. All 38 scenarios passed after
  the fixes.
- **CodeRabbit's own re-review** of the round-1 fix commit (3 auto-replies on its own resolved threads)
  confirmed all 3 of its round-1 findings fixed correctly, with no new findings of its own this round.

**Live results, PR #322 round 3 (2026-09-13, `handling-review-findings` triaging Codex's fresh review of
the round-2 fix commit -- the 3rd and final round within `review_findings_max_rounds`):** 3 findings, all
P1, all live-verified before fixing, all fixed in the same round.
- **F1 (Critical):** round 2's own atomic-write fix (above) closed the snapshot's WRITE-side race, but
  every consumer (`--diff`/`--force`/`--keep`) still performed TWO SEPARATE file opens -- one inside
  `require_generation_token` to validate the embedded generation, a second, later one in the caller's own
  triple-parsing loop. Codex found the READ-side race this left open: a concurrent `--list-review`
  landing in the gap between those two opens replaces the snapshot after validation already passed
  against the OLD content, so the later, separate parse reads the NEW (already-replaced) content instead.
  Live-reproduced with a real background process (a temp copy of the script with a `sleep` injected right
  after it opens the file, racing a real foreground `--list-review`): a token validated when index 1
  named `atag` was still accepted after `atag` was independently removed and a fresh `--list-review`
  made index 1 name `ztag` instead -- the old token's `--force` call deleted `ztag`. **Fix:**
  `require_generation_token` no longer opens the file itself -- it takes the already-read generation
  value as a plain argument. Every caller now opens `$REVIEW_SNAPSHOT` exactly ONCE
  (`exec {snap_fd}< "$REVIEW_SNAPSHOT"`), reads the generation field from that fd, validates it, and
  continues reading the tag/oid/dsha triples from the SAME fd. This relies on POSIX rename semantics: an
  already-open file descriptor keeps reading its original inode's content regardless of what the path
  later points to -- live-verified directly on this environment (an fd opened before a `mktemp`+`mv`
  replacement kept reading the pre-replacement bytes afterward) before relying on it. Re-ran the exact
  reproduction above against the fixed script under the MAXIMUM possible race window (the sleep placed
  immediately after the file opens, before either read) and confirmed `--force` correctly resolved to
  the ORIGINAL `atag` (now gone) and refused, never touching `ztag`.
- **F2 (P1):** only the tag's own oid was atomically protected by `--force`'s
  `git update-ref -d <ref> <old-oid>` call -- `$default_branch`'s oid was checked sequentially
  beforehand with no atomic binding to the delete itself, so a `$default_branch` rewind landing in the
  gap between that check passing and the delete actually running could still let the delete through.
  Live-reproduced (same sleep-injection technique, this time delaying right before the delete):
  rewinding `$default_branch` in that gap still let an unpatched `--force` succeed. **Fix:** the
  sequential pre-checks stay (fast, friendly rejection for the common case), but the actual delete is now
  a single `git update-ref --stdin` transaction combining `verify <default_branch's full ref> <expected
  dsha>` with `delete refs/tags/<tag> <expected oid>` -- live-verified that this primitive is genuinely
  atomic across two DIFFERENT refs (a crafted repro: `verify` an intentionally stale branch oid alongside
  `delete` of a real tag in one transaction correctly refused the whole batch with git's own "cannot lock
  ref ...: is at X but expected Y", leaving the tag untouched) before relying on it, and that the matching
  positive case (both refs current) still succeeds normally. `$default_branch`'s full ref path is resolved
  via `git rev-parse --symbolic-full-name` (`update-ref --stdin` requires a fully-qualified ref, not a
  short branch name -- verified live that a bare `main` is rejected: "fatal: refusing to update ref with
  bad name").
- **F3 (P1):** the "unique commits" section printed only `git log --oneline` subjects, but the round-1
  caution note (added for F3 in that round) explicitly tells the reviewer to "review each unique commit's
  own diff above" -- no such diff was ever printed. Live-reproduced with commits titled only `one` and
  `two`: a string unique to the first commit (later reverted by the second, so absent from the final
  tree-content diff) never appeared anywhere in `--diff`'s output. **Fix:** `git log --oneline` replaced
  with `git log -p --no-ext-diff --no-textconv` (matching the flags already used for the tree-content diff
  call), printing each unique commit's actual patch, not just its subject.
- **3 new regression scenarios** added (41 total, up from 38): `scenario_force_immune_to_concurrent_
  snapshot_replacement` and `scenario_force_atomic_default_branch_verify_and_delete` both use a real
  background process racing a real foreground `--list-review`/branch-rewind (a temp copy of the script
  patched with a `sleep` inserted at the exact race point, via `awk`) rather than a hypothetical -- an
  actual concurrent-process reproduction, matching how each finding was first verified;
  `scenario_diff_shows_unique_commit_patches` reuses the exact one/two-commit fixture Codex's own
  reproduction used. All 41 scenarios passed after the fixes.
