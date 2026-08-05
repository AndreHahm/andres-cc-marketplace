---
name: finishing-work
description: >-
  Sync back to a clean, current main after a PR merges — confirm the merge landed, switch to main,
  fast-forward pull, prune remote-tracking branches, and verify a clean repo state. Use when finishing
  work, asked to "I just merged, clean this up", "sync back to main after merge", "finish this branch",
  or "get back to a clean main". Never deletes branches or worktrees itself — hands off to `/git-cleanup`
  for that.
argument-hint: (optional) PR number or URL — defaults to the current branch's PR if omitted
allowed-tools: Bash(gh pr view:*), Bash(git checkout:*), Bash(git pull:*), Bash(git fetch:*), Bash(git status:*), Bash(git worktree:*), Bash(git branch:*)
---

# Finishing Work

Get local `main` back to a clean, current state right after a PR merges — without assuming the merge
actually happened, and without doing the branch/worktree deletion itself (that stays a deliberate,
user-invoked step via `/git-cleanup`).

## When to Use

Right after a PR merges: confirming the merge, returning to a synced `main`, and verifying nothing was
left dirty. Triggers: "I just merged, clean this up", "sync back to main after merge", "finish this
branch", "get back to a clean main".

## When NOT to Use

- **Actually deleting the merged branch or its worktree** — that's `/git-cleanup`'s job. This skill only
  syncs local state and tells you to run it.
- **The PR hasn't merged yet** — step 1 below checks this and stops if it hasn't; don't skip straight to
  syncing main on the assumption it landed.

## Instructions

1. **Confirm the PR actually merged**: `git branch --show-current` (for the report). `gh pr view
   $ARGUMENTS --json state,mergedAt`. If `state` isn't `MERGED` (still open, or closed without merging),
   tell the user exactly which state it's in and stop — don't sync main on an assumption.
2. **Return to main**: `git checkout main`, then `git pull --ff-only`. If that fails (diverged local
   main), tell the user why and stop rather than force anything.
3. **Prune**: `git fetch --prune` to drop stale remote-tracking refs for branches deleted on the remote.
4. **Verify clean state**: `git status --porcelain` on the current worktree must come back empty. Also
   run `git worktree list` — if another worktree is still tied to the just-merged branch, flag it
   (especially if it has uncommitted changes) without touching it.
5. **Hand off**: tell the user local `main` is synced and current, and that `/git-cleanup` is the next
   step to review and delete the merged branch (and worktree, if any). Never invoke `git-cleanup`
   automatically — it has `disable-model-invocation: true` by design and only runs on direct user
   invocation.

## Testing & Validation

**Verify this skill activates on:**
- "I just merged PR #42, clean this up"
- "sync back to main after merge" / "finish this branch"

**Verify it does NOT activate on:**
- "delete my old branches" → `/git-cleanup`
- "start a new branch for X" → `starting-work`

**Quality gates:**
- [ ] Step 1 always checks actual PR state via `gh pr view` — never assumes merged from context alone
- [ ] A not-yet-merged PR always stops the flow before touching `main`
- [ ] Step 5 always tells the user to run `/git-cleanup` themselves — never invokes it via `Skill()`
- [ ] A diverged local `main` at step 2 always stops rather than force-syncing
