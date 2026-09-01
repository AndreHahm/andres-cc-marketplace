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
`git diff-tree` behave, each was independently reproduced live:**
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

**Now covered by a persisted, repeatable fixture** (flagged by Devin's automated PR review on PR #275;
addressed in the same PR rather than deferred): `scripts/test-content-reachable.sh` sources
`default_branch_patchids`/`is_tag_content_reachable` directly from `delete-rebase-backup-tags.sh` --
never a hand-copied re-implementation, so it can't silently drift from the real code -- and exercises 5
scenarios in isolated, throwaway git repos: a genuine rebase-merge (SHA differs, content identical) is
recognized as reachable; a whitespace-only difference does NOT falsely match; a trivial merge commit
doesn't abort the walk; a `git diff-tree` failure is distinguished from an empty diff; and the atomic
compare-and-delete succeeds on a matching oid and refuses on a stale one. Run directly:
`bash scripts/test-content-reachable.sh`. All 5 passed on the fix that shipped in PR #275.
