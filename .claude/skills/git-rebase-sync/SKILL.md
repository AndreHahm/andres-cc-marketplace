---
name: git-rebase-sync
description: >-
  Sync a feature branch onto the latest origin base branch via git rebase, with safety rails, deliberate conflict resolution, and safe force-with-lease pushing.
allowed-tools: Bash(git branch:*), Bash(git fetch:*), Bash(git status:*), Bash(git tag:*), Bash(git rev-list:*), Bash(git rebase --continue:*), Bash(git rebase --abort:*), Bash(git rebase --rebase-merges:*), Bash(git rebase origin/:*), Bash(git add:*), Bash(git diff:*), Bash(git show:*), Bash(git push:*), Bash(git log:*), Bash(gh repo view:*)
---

# git-rebase-sync

Use this skill when you need to sync a feature branch onto the latest `origin/{base_branch}` via **git rebase**, including **conflict resolution** with explicit clarification questions when intent is ambiguous.

**On the git rebase grant:** scoped to the 4 forms this skill's workflow documents — `--continue`,
`--abort`, `--rebase-merges` (with an `origin/...` target), and a plain rebase onto `origin/...` — each
its own explicit `Bash(git rebase <form>:*)` entry rather than a blanket `Bash(git rebase:*)`. Corrected
2026-08-11: an earlier version of this note claimed the blanket grant "couldn't be narrowed further,"
which was wrong — `Bash(git rebase:*)` also permits `--exec`/`-x`, which runs an arbitrary command against
every replayed commit, something this skill never documents or uses. The `gh repo:*` grant was narrowed
to `gh repo view:*` for the same reason — the only documented use is `gh repo view --json
defaultBranchRef`, and the broader grant included `gh repo delete`.

## Goals
- Rebase the current branch onto a specified base branch (often the repo default branch like `dev` or `main`).
- Resolve conflicts deliberately, without guesswork.
- Keep safety rails: backup ref, confirmations before history-rewriting commands, and safe pushing.

## Hard Rules
- Do not create or switch to a different feature branch. Operate on the current branch name unless I explicitly ask otherwise.
- Before any history-rewriting command (`git rebase ...`, `git push --force*`), use `AskUserQuestion` to show the exact command(s) you will run and confirm before proceeding.
- Create a local backup ref (prefer an annotated tag) before starting the rebase. Do not push backup refs unless I explicitly ask.
- Prefer `git push --force-with-lease`, never plain `--force`.
- If the correct conflict resolution is unclear, stop and ask a targeted question. Do not invent product behavior.

## Workflow

### 1) Identify base + branch
- Determine the current branch:
  - `git branch --show-current`
- Determine the base branch you will rebase onto:
  - If not provided, use GitHub default branch:
    - `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
- Fetch latest:
  - `git fetch origin`

### 2) Preflight safety checks
- Ensure the working tree is clean and there is no operation in progress:
  - `git status`
- If `git status` indicates an in-progress merge/rebase/cherry-pick, stop and ask what to do (abort vs continue).

### 3) Create a local backup ref (do not push)
- Create an annotated tag at current `HEAD`:
  - `git tag -a {branch_name}-rebase-backup-$(date +%Y%m%d-%H%M%S) -m "pre-rebase backup" HEAD`
- Record the tag name as `{backup_ref}` for recovery.

### 4) Choose rebase mode (normal vs preserve merges)
- Check whether the branch contains merge commits:
  - `git rev-list --count --merges origin/{base_branch}..HEAD`
- If merge commits exist, ask whether to preserve them (`--rebase-merges`) or flatten them (plain rebase).

### 5) Run the rebase (requires confirmation)
- Use `AskUserQuestion` to show the exact command you intend to run and confirm before running it:
  - Typical:
    - `git rebase origin/{base_branch}`
  - With merge preservation:
    - `git rebase --rebase-merges origin/{base_branch}`

### 6) Conflict handling loop
When conflicts happen:
1. Collect context:
   - `git status`
   - Identify conflicted files (from status output).
2. For each conflicted file:
   - Open the file and understand the surrounding code and intent.
   - Prefer minimal, mechanical conflict resolutions:
     - Keep upstream changes unless the feature branch deliberately supersedes them.
     - Re-run generators (lockfiles, codegen) instead of hand-editing when appropriate.
   - If intent is ambiguous, ask a single targeted question, for example:
     - "Should we keep the new upstream behavior X, or keep the feature behavior Y?"
     - "Is this file generated and safe to regenerate, or do you want manual resolution?"
3. Apply the resolution, then stage only resolved files:
   - `git add <file...>`
4. Continue:
   - `git rebase --continue`
5. If you reach a point where resolution is too risky/unclear:
   - Stop and ask; optionally propose aborting the rebase.

Helpful commands during conflicts:
- Inspect current conflict hunks: `git diff`
- See the commit being replayed: `git show`
- If you need to back out: `git rebase --abort` (this is safe and should be preferred over destructive resets)

### 7) Post-rebase verification
- Show the new commit range:
  - `git log --oneline --decorate origin/{base_branch}..HEAD`
- Run appropriate repo checks (tests, typecheck, lint) if available.

### 8) Push updated branch (requires confirmation)
- If the branch already exists on origin, rebasing rewrites history, so pushing requires force-with-lease.
- Use `AskUserQuestion` to show the exact command and confirm before running it:
  - `git push --force-with-lease origin HEAD:{branch_name}`

## Recovery
- If something goes wrong, use `{backup_ref}` to restore the pre-rebase state.
- Do not run destructive commands (e.g., `git reset --hard`) unless the user explicitly confirms via `AskUserQuestion` after seeing the exact command.

## Testing & Validation

**Verify this skill activates on:**
- "sync my branch onto main via rebase"
- "rebase this feature branch onto origin/dev"
- "resolve the rebase conflicts on this branch"
- "force-with-lease push after rebasing"

**Verify it does NOT activate on:**
- "start a new branch for this feature" → `starting-work`
- "find the commit that broke this" → `git-bisect`
- "merge this PR" → `merge-pr`
- "clean up my old branches and worktrees" → `git-cleanup`

**Quality gates:**
- [ ] Never creates or switches to a different feature branch than the current one, unless explicitly asked
- [ ] Steps 5 and 8 always show the exact rebase/force-push command via `AskUserQuestion` and wait for
      confirmation before running it
- [ ] Always creates a local backup ref (annotated tag) before starting the rebase, and never pushes it
      unless explicitly asked
- [ ] Always uses `--force-with-lease`, never plain `--force`
- [ ] Stops and asks a single targeted question when conflict-resolution intent is ambiguous — never
      invents behavior
- [ ] If preflight (`git status`) shows an in-progress merge/rebase/cherry-pick, always stops and asks
      abort vs. continue rather than proceeding
- [ ] Never runs a destructive command like `git reset --hard` without explicit `AskUserQuestion`
      confirmation showing the exact command
- [ ] The `git rebase` grant stays as 4 explicit per-form entries (`--continue`/`--abort`/
      `--rebase-merges`/plain-onto-`origin/...`) — never collapsed back to a blanket `Bash(git rebase:*)`,
      which would also permit `--exec`/`-x`
- [ ] The `gh repo` grant stays scoped to `gh repo view:*` only — never widened to bare `gh repo:*`,
      which would also permit `gh repo delete`
