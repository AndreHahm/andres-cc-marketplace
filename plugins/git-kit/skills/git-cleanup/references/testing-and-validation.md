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
- [ ] A tag whose derived branch no longer exists locally is reported "no longer exists locally" and is a
      `STALE_REBASE_BACKUP_TAG` candidate
- [ ] A tag whose derived branch still exists and is merged into the default branch is reported "exists,
      merged into `<default>`" and is a `STALE_REBASE_BACKUP_TAG` candidate
- [ ] A tag whose derived branch still exists and is NOT merged is reported "exists, not merged into
      `<default>`" and is never proposed for deletion — Phase 3.6 leaves it alone regardless of the tag's
      own age
- [ ] `git tag -d` is called directly, with no marker-handshake write beforehand — confirmed
      `guard-raw-destructive-cleanup.sh` only matches `git branch -D`/`worktree remove --force`, never
      `git tag -d`
- [ ] Gate 1/Gate 2 list stale rebase-backup tags as their own category, distinct from branch and
      stale-remote-branch categories, never silently merged into either

**Live results, 2026-08-31:** ran the updated `phase1-analysis.sh` against a throwaway scratch repo with
three rebase-backup tags: one whose branch was merged and then deleted (correctly reported "no longer
exists locally"), one whose branch was merged but kept (correctly reported "exists, merged into main"),
and one whose branch is still active/unmerged (correctly reported "exists, not merged into main"). All
three matched the intended Phase 3.6 categorization with no false positives or negatives.

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
