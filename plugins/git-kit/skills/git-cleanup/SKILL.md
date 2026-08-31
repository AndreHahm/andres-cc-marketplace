---
name: git-cleanup
description: >-
  Safely analyzes and cleans up local git branches and worktrees by categorizing them as merged, squash-merged, superseded, or active work.
disable-model-invocation: true
allowed-tools: Bash(git branch:*), Bash(git worktree:*), Bash(git fetch:*), Bash(git log:*), Bash(git status:*), Bash(git symbolic-ref:*), Bash(git -C:*), Bash(git tag:*), Bash(gh pr view:*), Bash(gh repo view:*), Bash(gh api -X DELETE repos/*/git/refs/heads/*:*), Bash(*/git-kit/scripts/write-git-kit-marker.sh:*), Bash(*/git-kit/skills/git-cleanup/scripts/phase1-analysis.sh:*), Read, Grep
---

# Git Cleanup

Safely clean up accumulated git worktrees and local branches by categorizing them into: safely deletable (merged), potentially related (similar themes), and active work (keep).

**On the `Bash(git -C:*)` grant:** this is broad by necessity, not oversight — Phase 4's dirty-state and
gitignored-content checks run `git -C <worktree-path> status --porcelain[--ignored]` against a worktree
path that's only known at runtime, and `Bash(prefix:*)` permission syntax can't express "any `-C <path>`
but only followed by `status`" without a wrapper script. Reviewed 2026-08-11 (git-kit retro follow-up);
no narrower grant is expressible with the current permission syntax.

## When to Use

- When the user has accumulated many local branches and worktrees
- When branches have been merged but not cleaned up locally
- When remote branches have been deleted but local tracking branches remain

## When NOT to Use

- Do not use for general remote branch management (this is local cleanup only) — **narrow exception:**
  Phase 3.5's remote-branch fallback deletes a remote branch only when its own PR is live-confirmed
  `MERGED` via `gh pr view`, as a repair for a known `gh pr merge --delete-branch` failure mode (see
  Phase 3.5 for the mechanism). It never deletes a remote branch for any other reason — an open PR, no
  PR at all, or "no local counterpart" alone are never sufficient by themselves.
- Do not use for repository maintenance tasks like gc or prune
- Not designed for headless or non-interactive automation (requires user confirmations at two gates)
- Cannot run from a session sandboxed to a worktree checkout — this command needs to operate on the
  primary checkout's branch/worktree list, and a worktree-sandboxed session cannot `cd` there. Run it from
  a session started in the primary checkout instead. See `finishing-work`'s hand-off note for the same
  constraint on the more common path into this skill.

## Core Principle: SAFETY FIRST

**Never delete anything without explicit user confirmation.** This skill uses a gated workflow where users must approve each step before any destructive action.

## Critical Implementation Notes

See [references/critical-implementation-notes.md](references/critical-implementation-notes.md) for the
squash-merge `-D` requirement and the PR-history investigation commands — the branch-grouping procedure
itself is already fully covered by Phase 2 below, so the reference file doesn't restate it. Read the
reference before Phase 3 (Categorize) for the squash-merge nuance; the PR-history commands apply
specifically to `[gone]` branches within Phase 2/3.

## Workflow

### Phase 1: Comprehensive Analysis

Gather ALL information upfront before any categorization. Run `"${CLAUDE_PLUGIN_ROOT}/skills/git-cleanup/scripts/phase1-analysis.sh"` directly via `Bash` — it resolves the default branch, lists local branches and worktrees, fetches/prunes, gets merged-branch and recent PR-merge history, and for each non-protected branch (protected names excluded via the script's own `grep -vE` filter) reports unmerged and unpushed commits plus whether its `origin/<branch>` counterpart still exists. It also lists remote-only branches with no local counterpart at all (candidates for Phase 3.5's fallback), and every local `*-rebase-backup-*` tag left over from `git-rebase-sync`'s pre-rebase safety backup, alongside its derived branch name and that branch's current status (candidates for Phase 3.6's cleanup). Read its output rather than re-deriving these git calls by hand.

**Note on branch names:** Git branch names can contain characters that break shell expansion. Always quote `"$branch"` in commands.

### Phase 2: Group Related Branches

**Do this BEFORE individual categorization.**

Identify branch groups by shared prefixes:

```bash
# List branches and extract prefixes
git branch --format='%(refname:short)' | sed 's/-[^-]*$//' | sort | uniq -c | sort -rn
```

For each group with 2+ branches:

1. **Compare commit histories** - Which branches contain commits from others?
2. **Find merge evidence** - Which PRs incorporated work from this group?
3. **Identify the "final" branch** - Usually the most recent or most complete
4. **Mark superseded branches** - Older iterations whose work is in main or in a newer branch

**SUPERSEDED requires evidence, not just shared prefix:**
- A PR merged the work into main, OR
- A newer branch contains all commits from the older branch
- Name prefix alone is NOT sufficient — similarly named branches may contain independent work

Example analysis for `feat/api-*` branches:

```markdown
### Related Branch Group: feat/api-*

| Branch | Commits | PR Merged | Status |
|--------|---------|-----------|--------|
| feat/api | 12 | #29 (initial API) | Superseded - work in main |
| feat/api-v2 | 8 | #45 (API improvements) | Superseded - work in main |
| feat/api-refactor | 5 | #67 (refactor) | Superseded - work in main |
| feat/api-final | 4 | None found | Superseded by above PRs |

**Recommendation:** All 4 branches can be deleted - work incorporated via PRs #29, #45, #67
```

### Phase 3: Categorize Remaining Branches

For branches NOT in a related group, categorize individually:

```
Is branch merged into default branch?
├─ YES → SAFE_TO_DELETE (use -d)
└─ NO → Is tracking a remote?
        ├─ YES → Remote deleted? ([gone])
        │        ├─ YES → Was work squash-merged? (check main for PR)
        │        │        ├─ YES → SQUASH_MERGED (use -D)
        │        │        └─ NO → REMOTE_GONE (needs review)
        │        └─ NO → Local ahead of remote? (check: git log origin/<branch>..<branch>)
        │                ├─ YES (has output) → UNPUSHED_WORK (keep)
        │                └─ NO (empty output) → SYNCED_WITH_REMOTE (keep)
        └─ NO → Has unique commits?
                ├─ YES → LOCAL_WORK (keep)
                └─ NO → SAFE_TO_DELETE (use -d)
```

**Category definitions:**

| Category | Meaning | Delete Command |
|----------|---------|----------------|
| SAFE_TO_DELETE | Merged into default branch | `git branch -d` |
| SQUASH_MERGED | Work incorporated via squash merge | `git branch -D` |
| SUPERSEDED | Part of a group, work verified in main via PR or in newer branch | `git branch -D` |
| REMOTE_GONE | Remote deleted, work NOT found in main | Review needed |
| UNPUSHED_WORK | Has commits not pushed to remote | Keep |
| LOCAL_WORK | Untracked branch with unique commits | Keep |
| SYNCED_WITH_REMOTE | Up to date with remote | Keep |
| STALE_REMOTE_ONLY | No local branch; remote branch's own PR is live-confirmed `MERGED` (Phase 3.5) | `gh api -X DELETE` |
| STALE_REBASE_BACKUP_TAG | Leftover `git-rebase-sync` pre-rebase tag; originating branch is gone or merged (Phase 3.6) | `git tag -d` |

### Phase 3.5: Remote Branch Fallback (stale `origin/<branch>` after merge)

**Why this exists:** `gh pr merge --delete-branch` deletes the local and remote branch together, but its
local half needs to check out the default branch first — which fails with
`fatal: '<default>' is already used by worktree ...` whenever that default branch is already checked out
elsewhere (near-guaranteed if the merged branch had its own worktree, since the primary checkout almost
always has the default branch checked out). When that local checkout fails, the remote branch deletion is
silently skipped too — `merge-pr`'s own step 7 already works around the resulting non-zero exit by
checking PR state instead of trusting the exit code, but that fix only avoids a false "merge failed"
report; it doesn't repair the branch-deletion gap. `finishing-work`'s own step 1.5 is the primary fix,
applied right after the merge that caused it — this phase is the safety net for anything that slipped
past that (an older merge, a merge run through some other path).

**Two cases, both requiring live PR-state confirmation before any deletion — never inferred from branch
existence alone:**

1. **Still-listed local branches** (from Phase 1's per-branch loop): if a branch already categorized
   `SAFE_TO_DELETE`/`SQUASH_MERGED`/`SUPERSEDED` above also shows `origin/<branch>` as "still exists on
   origin" in Phase 1's output, its remote counterpart gets deleted alongside the local one — no separate
   PR check needed here, since that category assignment already required merge evidence.
2. **Remote-only orphans** (Phase 1's "Remote-only branches" list — no local counterpart at all, e.g. a
   branch a prior `git-cleanup` run already deleted locally before this fallback existed): for each one,
   run `gh pr view <branch> --json state,number` live. Only if `state` is exactly `MERGED`, categorize it
   `STALE_REMOTE_ONLY`. **Any other result — `OPEN`, `CLOSED` (without merging), or no PR found at
   all — leaves that branch untouched entirely, not even flagged for review.** This is what keeps this
   phase a narrow repair for one specific known failure mode rather than general remote branch management:
   a branch with no merged PR evidence is out of scope, full stop.

### Phase 3.6: Rebase-Backup Tag Cleanup (leftover `git-rebase-sync` safety tags)

**Why this exists:** `git-rebase-sync`'s Step 3 creates a local-only, never-pushed annotated tag
(`{branch}-rebase-backup-{timestamp}`) immediately before every rebase, as a recovery point if the rebase
goes wrong. Nothing in that skill — or anywhere else in git-kit — ever deletes these tags afterward, so
they accumulate indefinitely once the branch they were protecting is long gone or merged.

Phase 1's own tag enumeration (`=== Rebase-backup tags ===`) already lists every tag matching the exact
`{branch}-rebase-backup-{8-digit-date}-{6-digit-time}` shape, alongside its derived branch name, that
branch's current status, and — when the branch no longer exists locally — whether the tag's own commit is
reachable from the default branch. Categorize each one from that output — no extra git calls needed here:

- **Branch no longer exists locally, tag reachable from the default branch** → `STALE_REBASE_BACKUP_TAG`,
  safe to delete — the tag's content already made it into the default branch by some path, so the tag is
  redundant.
- **Branch no longer exists locally, tag NOT reachable from the default branch** → **never categorize as
  safe to delete.** The branch's own deletion was never verified by this run — it may have been
  force-deleted outside this skill's own SAFE_TO_DELETE/SQUASH_MERGED evidence trail (e.g. manually, or by
  a rebase that dropped/skipped a commit) — so this tag may be the *only* remaining reachable copy of
  those commits. Leave it alone and report it under a distinct "needs review — unique history" note
  outside the deletable list, the same treatment Phase 3's REMOTE_GONE category already gets for the
  analogous branch-level case; never fold it into "delete all recommended."
- **Branch exists, merged into the default branch** → `STALE_REBASE_BACKUP_TAG`, safe to delete — "merged"
  already guarantees ancestry (unlike the branch-gone case above), so the branch itself is already safe to
  delete and its backup tag is redundant.
- **Branch exists, not merged** → leave the tag alone. The branch may still need this recovery point,
  and the tag being merely old is not evidence otherwise (see Rationalizations below).

Fold the result into Gate 1 as its own list, the same way Phase 3.5's stale remote branches get their own
list — never silently merge it into the branch categories above, since a tag isn't a branch and
`git tag -d` isn't `git branch -d`/`-D`. **Before including a tag in this list, validate its full name
against `^[A-Za-z0-9._/-]+$`** (see Phase 5's Execute section for why — a git-legal tag name can contain
shell metacharacters) — a name that fails this check is never surfaced at Gate 1, not just skipped at
execution time.

### Phase 4: Dirty State Detection

Check ALL worktrees and current directory for uncommitted changes:

```bash
# For each worktree path
git -C <worktree-path> status --porcelain

# For current directory
git status --porcelain
```

**Also check for gitignored content** — `git status --porcelain` never lists gitignored files, tracked
or not, so a worktree can carry a `.env`, a local settings override, or other gitignored content that this
check alone would silently miss:

```bash
# For each worktree path
git -C <worktree-path> status --porcelain --ignored

# For current directory
git status --porcelain --ignored
```

Do not use `git clean` here — it's a destructive command with no place in an analysis-only phase of a
skill whose Core Principle is "never delete anything without explicit user confirmation." `--ignored` is
read-only and sufficient. If the ignored-file list is long (e.g. `node_modules/`, `.venv/`), show only the
top-level entries plus a count rather than every path, so the warning stays readable.

**Exclude `.claude/settings.local.json` and any `**/CLAUDE.local.md`** from this warning — `starting-work`
now copies both into every worktree it creates from the main worktree's own copy, so a worktree's version
is a duplicate, not the only copy; deleting the worktree does not lose them the way an untracked `.env` or
scratch file would. Do not list these two patterns under "will also be deleted" below.

**Display warnings prominently:**

```markdown
WARNING: ../proj-auth has uncommitted changes:
  M  src/auth.js
  ?? new-file.txt

Ignored (not tracked by git, will also be deleted):
  .env

These changes will be LOST if you remove this worktree.
```

**Check for session locks:** `git worktree list --verbose` shows `locked: <reason>` for any locked
worktree (`starting-work` locks every worktree it creates — see its own Instructions). A locked worktree
recommended for deletion needs an unlock step before `git worktree remove` — note this against that
worktree in the analysis rather than only discovering it when the removal command itself fails.

### GATE 1: Present Complete Analysis

Present everything in ONE comprehensive view. Group related branches together. See `assets/analysis-report-template.md` for the full example layout (related branch groups, individual branch categories, worktrees, and summary).

Use AskUserQuestion with clear options:
- Delete all recommended (groups + merged + squash-merged + stale remote-only + stale rebase-backup tags)
- Delete specific groups/categories
- Let me pick individual branches

**Do not proceed until user responds.**

### GATE 2: Final Confirmation with Exact Commands

Show the EXACT commands that will run, with correct flags:

```markdown
I will execute:

# Merged branches (safe delete)
git branch -d fix/typo

# Squash-merged branches (force delete - work is in main via PRs)
git branch -D feat/login
git branch -D feat/api
git branch -D feat/api-v2
git branch -D feat/api-refactor
git branch -D feat/api-final

# Worktrees (unlock first if session-locked, per Phase 4's lock check)
git worktree unlock ../proj-auth
git worktree remove ../proj-auth

# Stale remote branches (Phase 3.5 — PR confirmed MERGED via gh pr view)
gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/feat/old-worktree-feature

# Stale rebase-backup tags (Phase 3.6 — originating branch is gone or merged, name validated)
git tag -d -- feat/gone-branch-rebase-backup-20260701-093000

Confirm? (yes/no)
```

**IMPORTANT:** This is the ONLY confirmation needed for deletion. Do not add extra confirmations if `-D` is required.

### Phase 5: Execute

Run each deletion as a **separate command** so partial failures don't block remaining deletions. Report the result of each. Immediately before each `git branch -D` call — never earlier, since git-kit's guard hook only accepts a marker up to 60 seconds old — run `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-cleanup-destructive git-cleanup`. This writes the marker git-kit's destructive-cleanup guard requires before it will let a raw `git branch -D` targeting a protected branch name through — the same marker-handshake pattern every other git-kit skill uses before its own guarded command. Plain `git branch -d` (lowercase, already-merged-only) and plain `git worktree remove` (no `--force`) aren't guarded and need no marker; only `git worktree remove --force`/`-f` does, since a plain removal already refuses on a dirty or locked worktree via git's own safeguard.

```bash
git branch -d fix/typo
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-cleanup-destructive git-cleanup
git branch -D feat/login
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-cleanup-destructive git-cleanup
git branch -D feat/api
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-cleanup-destructive git-cleanup
git branch -D feat/api-v2
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-cleanup-destructive git-cleanup
git branch -D feat/api-refactor
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-cleanup-destructive git-cleanup
git branch -D feat/api-final
git worktree unlock ../proj-auth
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-cleanup-destructive git-cleanup
git worktree remove ../proj-auth
gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/feat/old-worktree-feature
git tag -d -- feat/gone-branch-rebase-backup-20260701-093000
```

If a deletion fails, report the error and continue with remaining deletions. If `git worktree remove`
fails specifically because the worktree is still locked (the unlock step above was skipped, or a lock was
added after Phase 4's check), report this distinctly from a generic removal failure — say plainly that it's
locked and by which reason, rather than surfacing git's raw error text unexplained.

**Stale remote branches (Phase 3.5):** no marker write needed — `gh api -X DELETE repos/*/git/refs/heads/*`
isn't guarded by any PreToolUse hook (unlike `git branch -D` against a protected name), the same reason
`merge-pr`'s own manual-delete-branch path calls it directly. Before each call, validate the branch name
against `^[A-Za-z0-9._/-]+$` — the same safety check `merge-pr` applies before this exact command, since
git ref names can otherwise contain shell metacharacters (`;&|$`, backticks, parens) that would reach a
shell context unsafely; if a name fails this check, skip it and report why rather than attempting the
call. Resolve `<owner>/<repo>` via `gh repo view --json nameWithOwner --jq .nameWithOwner` once per run,
not once per branch.

**Stale rebase-backup tags (Phase 3.6):** no marker write needed — `git tag -d` isn't guarded by
`guard-raw-destructive-cleanup.sh` (that hook only matches `git branch -D`/`worktree remove --force`), and
deleting a tag never touches a protected branch name in the first place. **Before proposing or executing
any tag deletion, validate the full tag name against `^[A-Za-z0-9._/-]+$`** — the same safety check Phase
3.5 already applies before its `gh api -X DELETE` call, since a git tag name is legal with shell
metacharacters a naive interpolation would execute (e.g. `` `$(cmd)-rebase-backup-20260831-120000` `` is a
git-accepted tag name — `git check-ref-format` confirms it — that would run `cmd` if composed unsafely
into a shell command); if a name fails this check, skip it and report why rather than ever including it in
Gate 1/Gate 2 or attempting deletion. Once validated, run `git tag -d -- "$tag"` — the `--` end-of-options
marker is defense in depth, not a substitute for the validation above — one call per tag, so a partial
failure part-way through still lets the rest proceed.

### Phase 6: Report

```markdown
## Cleanup Complete

### Deleted
- fix/typo
- feat/login
- feat/api
- feat/api-v2
- feat/api-refactor
- feat/api-final
- Worktree: ../proj-auth
- Remote branch (stale, Phase 3.5): feat/old-worktree-feature
- Rebase-backup tag (stale, Phase 3.6): feat/gone-branch-rebase-backup-20260701-093000

### Remaining (4 branches)
| Branch | Status |
|--------|--------|
| main | current |
| wip/new-feature | active work |
| experiment/old | needs review |
```

## Safety Rules

1. **Never invoke automatically** - Only run when user explicitly uses `/git-cleanup`
2. **Two confirmation gates only** - Analysis review, then deletion confirmation
3. **Use correct delete command** - `-d` for merged, `-D` for squash-merged/superseded
4. **Never touch protected branches** - main, master, develop, release/* are excluded from Phase 1's
   per-branch commit-analysis loop by `scripts/phase1-analysis.sh`'s own `grep -vE` filter (run directly,
   not just read), and any raw `git branch -D` that still targets one of these names is additionally
   hard-blocked by git-kit's `guard-raw-destructive-cleanup.sh` PreToolUse hook
5. **Block dirty worktree removal** - Refuse without explicit data loss acknowledgment. "Dirty" covers
   gitignored content too, not just tracked/untracked-but-not-ignored changes — `git status --porcelain`
   alone misses gitignored files entirely, so Phase 4's `--ignored` check is what actually completes this
   rule's coverage
6. **Unlock before removing** - A session-locked worktree (per Phase 4's lock check) gets
   `git worktree unlock` immediately before `git worktree remove`, never `--force` as a substitute for
   unlocking — `--force` bypasses the dirty-worktree safeguard in Safety Rule 5 too, not just the lock
7. **Group related branches** - Don't scatter them across categories
8. **Never delete a remote branch without live PR-merged confirmation** - Phase 3.5's fallback only
   deletes `origin/<branch>` when `gh pr view <branch>` confirms `state: MERGED` at the time of the
   check, not from "no local branch" or "not in Phase 1's merged list" alone - an open PR, a closed
   (unmerged) PR, or no PR at all always leaves that branch untouched
9. **Never delete a rebase-backup tag whose originating branch is still active** - Phase 3.6 only
   proposes a `*-rebase-backup-*` tag for deletion when its derived branch no longer exists locally or is
   already merged into the default branch - an unmerged, still-active branch's backup tag is always left
   alone, regardless of the tag's own age
10. **Never delete a rebase-backup tag whose branch is gone unless its content is verified reachable** -
    "branch no longer exists locally" alone is not evidence the tag is redundant, since that branch's
    deletion was never verified by this run; Phase 3.6 only proposes deletion in this case once
    `git merge-base --is-ancestor` confirms the tag's own commit is reachable from the default branch -
    an unreachable tag is reported separately as needing manual review, never included in "delete all
    recommended"
11. **Never interpolate an unvalidated tag name into a shell command** - a git tag name is legal with
    shell metacharacters (`git check-ref-format` accepts e.g. `` `$(cmd)-rebase-backup-20260831-120000` ``),
    so every candidate is checked against `^[A-Za-z0-9._/-]+$` before it's ever surfaced at Gate 1 or
    passed to `git tag -d`, the same safety check Phase 3.5 already applies to remote branch names

## Rationalizations to Reject

These are common shortcuts that lead to data loss. Reject them:

| Rationalization | Why It's Wrong |
|-----------------|----------------|
| "The branch is old, it's probably safe to delete" | Age doesn't indicate merge status. Old branches may contain unmerged work. |
| "I can recover from reflog if needed" | Reflog entries expire. Users often don't know how to use reflog. Don't rely on it as a safety net. |
| "It's just a local branch, nothing important" | Local branches may contain the only copy of work not pushed anywhere. |
| "The PR was merged, so the branch is safe" | Squash merges don't preserve branch history. Verify the *specific* commits were incorporated. |
| "I'll just delete all the `[gone]` branches" | `[gone]` only means the remote was deleted. The local branch may have unpushed commits. |
| "The user seems to want everything deleted" | Always present analysis first. Let the user choose what to delete. |
| "The branch has commits not in main, so it has unpushed work" | "Not in main" ≠ "not pushed". A branch can be synced with its remote but not merged to main. Always check `git log origin/<branch>..<branch>`. |
| "It's gitignored, so it's not important" | Gitignored means *not in git history* — it is often the only copy of a `.env`, a local override, or uncommitted scratch output. Absence from git is not evidence of unimportance. |
| "This remote branch has no local copy, so its PR must be merged and it's safe to delete" | No local copy only means nobody has it checked out here — it could be an open PR someone else is working on, or a branch with no PR at all. Phase 3.5 always confirms `state: MERGED` live via `gh pr view` before ever proposing deletion. |
| "This rebase-backup tag is old, it's probably safe to delete" | Age alone says nothing about whether the branch it protects is still active — a long-running feature branch can be rebased repeatedly with none of its backup tags becoming safe to delete. Phase 3.6 only proposes deletion once the derived branch is confirmed gone or merged. |
| "The branch is gone, so its backup tag must be redundant" | The branch's own deletion was never verified by this skill run — it may have been force-deleted outside git-cleanup's own evidence trail, or a rebase may have dropped a commit the tag still holds. Phase 3.6 always confirms the tag's commit is reachable from the default branch (`git merge-base --is-ancestor`) before proposing deletion in this case; an unreachable tag may be the only remaining copy of its commits. |

## Testing & Validation

See [references/testing-and-validation.md](references/testing-and-validation.md) for activation
triggers/non-triggers, the Phase 4 gitignored-content detection scenarios, and the full quality-gates
checklist.