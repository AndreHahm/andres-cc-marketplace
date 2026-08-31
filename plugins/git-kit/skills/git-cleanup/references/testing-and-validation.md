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
      NOT reachable from the default branch (a rebase-then-merge sequence, where the merged branch's tip
      is a different commit object than the tag's pre-rebase commit) is reported "reachable from
      `<default>`: NO" and is NEVER proposed for deletion — the reachability check always runs for the
      merged case too, never skipped just because the branch itself is already known-safe to delete
      (found by `cross-model-review`, Codex Phase 1 re-review after the first data-loss fix, 2026-08-31 —
      the merged-branch case turned out to have the exact same flaw as the branch-gone case, just less
      obvious since "merged" sounds like a stronger safety signal than it actually is here; live-verified
      with a real rebase-then-merge sequence, confirming `git branch --merged` reports the branch merged
      while `git merge-base --is-ancestor <pre-rebase-sha> main` still returns false)
- [ ] A tag whose derived branch still exists and is NOT merged is reported "exists, not merged into
      `<default>`" and is never proposed for deletion, with no reachability check run at all — Phase 3.6
      leaves it alone regardless of the tag's own age, and the extra `git merge-base` call is skipped
      entirely for this case since the outcome doesn't depend on it
- [ ] `git tag -d` is called directly, with no marker-handshake write beforehand — confirmed
      `guard-raw-destructive-cleanup.sh` only matches `git branch -D`/`worktree remove --force`, never
      `git tag -d`
- [ ] Gate 1/Gate 2 list stale rebase-backup tags as their own category, distinct from branch and
      stale-remote-branch categories, never silently merged into either
- [ ] The ref-name safety check (`^[A-Za-z0-9._/-]+$`) always runs before a tag is surfaced at Gate 1 or
      passed to `git tag -d`, matching Phase 3.5's identical check before `gh api -X DELETE` — a tag name
      failing this check is skipped and reported, never included in a deletion command
      (found by `cross-model-review`, Codex Phase 1 + Codex Phase 2's own independent re-derivation +
      Claude Phase 2, 2026-08-31: `git check-ref-format --allow-onelevel` accepts a tag name containing
      shell metacharacters, e.g. `` `$(id)-rebase-backup-20260831-120000` ``, live-verified as a legal git
      ref)
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
