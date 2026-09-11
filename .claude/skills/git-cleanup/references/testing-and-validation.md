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
      write beforehand — confirmed `guard-raw-destructive-cleanup.sh` only matches
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
- [ ] The script's error paths match `stage-selected-files.sh`'s own conventions: no `--list` run yet
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
      conflict (found by Claude fresh-eyes, `cross-model-review` round 2)
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
two `cross-model-review` follow-up rounds, and the GitHub automated-review round below): `scripts/test-content-reachable.sh`
sources `is_path_blob_reachable`/`check_diff_records`/`is_tag_content_reachable` directly from
`delete-rebase-backup-tags.sh` -- never a hand-copied re-implementation, so it can't silently drift from
the real code -- and currently exercises 18 scenarios in isolated, throwaway git repos, covering: a
genuine rebase-merge (SHA differs, content identical) recognized as reachable; a whitespace-only
difference NOT falsely matching; a trivial merge commit not aborting the walk; a `git diff-tree` failure
(merge and non-merge) distinguished from an empty diff; the atomic compare-and-delete succeeding on a
matching oid and refusing on a stale one; content reorganized into a different commit grouping still
recognized, and that not masking a file that genuinely never landed; a parentless (root) commit's content
checked in both directions; a non-ASCII path deletion checked against `$default_branch`'s real state
rather than a mis-parsed literal string, in both directions; a mode-only change (`chmod +x`) checked in
both directions; a filename containing a pathspec metacharacter still matched literally; a deletion
check failing closed when the path's blob is unreadable, not just when the path is absent; a blob present
on `$default_branch` only before divergence not satisfying reachability; and content genuinely inherited
unchanged from the merge-base still recognized. Run directly: `bash scripts/test-content-reachable.sh`.
All 5 passed on the fix that shipped in PR #275; all 18 pass on the current script (see the four dated
"Live results" entries above for the redesign and each review round that grew this count from 5 to 18).

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
