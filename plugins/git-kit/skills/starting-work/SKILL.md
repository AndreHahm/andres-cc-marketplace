---
name: starting-work
description: >-
  Sync local main, then create a properly named branch (or worktree) to start new work. Use when
  starting new work, asked to "start a new branch", "create a branch for X", "sync main and branch
  off", or "set up a worktree for this feature" — before any commits happen. Validates the branch name
  against git-kit's <type>/<description> convention and offers a worktree as an alternative to a plain
  branch checkout.
argument-hint: (optional) branch type and description, e.g. "feature add-user-auth"
allowed-tools: Bash(git fetch:*), Bash(git checkout:*), Bash(git pull:*), Bash(git status:*), Bash(git branch --show-current:*), Bash(git symbolic-ref refs/remotes/origin/HEAD:*), Bash(git worktree add:*), Read
---

# Starting Work

Get from "I'm about to start something new" to a properly named, up-to-date branch (or worktree) in one
gated flow — instead of manually remembering to sync main, checking the naming convention, and deciding
whether a worktree makes sense, separately, every time.

## When to Use

Before writing any code for a new piece of work: syncing local `main` and creating the branch (or
worktree) it'll happen on. Triggers: "start a new branch", "create a branch for X", "sync main and
branch off", "set up a worktree for this feature".

## When NOT to Use

- **Rebasing an already-existing feature branch onto a newer main** — that's `/sync-branch`, not this
  skill. `starting-work` only runs before a branch exists.
- **Renaming an existing branch based on what it now contains** — that's `/update-branch-name`.
- **Anything after the first commit** — once work has started, this skill has nothing left to do.

## Instructions

1. **Note the starting point and sync**: `git branch --show-current` (for the report). `git fetch origin --prune`.
   Resolve the actual default branch — `git symbolic-ref refs/remotes/origin/HEAD` (falling back to
   `main` if that fails, e.g. no `origin` remote configured) — the same resolution `finishing-work` uses,
   so the two halves of the branch lifecycle agree on what "main" means in a repo that defaults to
   something else. Note: because the resolved branch name is dynamic, `allowed-tools` grants
   `Bash(git checkout:*)` broadly rather than pinned to a literal branch name — this also covers step 4's
   `git checkout -b`, so no separate grant is needed there. This skill never runs the file-restore form
   (`git checkout -- <path>`); only branch checkout and `-b` are ever invoked. If not already on the resolved default branch, ask via `AskUserQuestion` — "Base the
   new branch off `<resolved-branch>`, or off the current branch (`<name>`)?" — default the resolved
   branch. If basing off it: `git checkout <resolved-branch>`, then `git pull --ff-only`. If that fails
   (diverged local branch, or it's already checked out in another worktree), tell the user exactly why
   and stop rather than force anything. If basing off the current branch, skip the checkout/pull — see
   `references/worktree-decision.md` for why this branch-off-a-branch case is legitimate (e.g. stacking
   related work).
   Verify `git status --porcelain` is clean before proceeding; if not, tell the user to commit or stash
   first (point at `Skill(git-kit:commit)`) and stop here.
2. **Resolve the branch name**: use `$ARGUMENTS` if it supplies a type and description; otherwise ask
   via `AskUserQuestion` for both, one at a time. Validate:
   - Type: a single lowercase word, no slashes or spaces.
   - Description: kebab-case — lowercase letters, digits, and hyphens only; no leading/trailing/double
     hyphen.
   Don't hardcode or restate the accepted type list here — `commit`'s own "Branch Naming Convention"
   section is the single source of truth for that. If the user is unsure what type to use, point them
   there instead of guessing or duplicating the list. **If either value fails validation**, tell the
   user why and ask again via `AskUserQuestion` — never pass an invalid type or description forward to
   step 4, the same "stop and explain" discipline step 1 already applies to a diverged main.
3. **Ask worktree or plain branch**: `AskUserQuestion` — "Create a plain branch, or a separate worktree
   for this?" See `references/worktree-decision.md` for the tradeoffs to mention if the user wants
   guidance rather than a snap decision.
4. **Create**:
   - Plain branch: `git checkout -b <type>/<description>`.
   - Worktree: compute a default sibling path following `git-worktrees`' own naming convention
     (`../<repo-dir-name>-<description>`), show it to the user for confirmation or override. If the user
     supplies an override, constrain it: letters, digits, hyphens, underscores, forward slashes, and
     periods only (no shell metacharacters), it must not contain a `..` path segment, and it must resolve
     to a location alongside or below the repo's parent directory — not step 2's kebab-case rule, which
     is stricter than a filesystem path needs to be. If the override doesn't meet this, tell the user why
     and ask again rather than passing it through. Then `git worktree add -b <type>/<description> <path>`.
5. **Report**: the branch (or worktree path) just created, current location, and — for a worktree —
   that `cd`-ing into the worktree path is needed before working there. Mention `git-worktrees` has
   further operations (compare, merge, cleanup) if multiple worktrees end up in play.

## Testing & Validation

**Verify this skill activates on:**
- "start a new branch for the auth refactor"
- "create a branch for X" / "sync main and branch off"
- "set up a worktree for this feature"

**Verify it does NOT activate on:**
- "sync my current branch with main" → `/sync-branch`
- "rename this branch to match what it does now" → `/update-branch-name`
- "I just merged, clean this up" → `finishing-work`

**Quality gates:**
- [ ] Step 1 never fast-forwards a diverged local `main` silently — always stops and tells the user
- [ ] Step 2 never hardcodes the branch-type list — always points at `commit`'s own convention section
- [ ] Step 2 never passes an invalid type/description forward — always re-asks on validation failure
- [ ] Step 3's worktree-vs-branch question always uses `AskUserQuestion`, never assumed
- [ ] Step 4 never passes an unconstrained worktree-path override to `git worktree add` — always
      validates the character class and rejects any `..` path segment
- [ ] A dirty working tree at step 1 always stops the flow with a pointer to `commit`, never proceeds

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/worktree-decision.md` | Worktree-vs-plain-branch tradeoffs, and the branch-off-a-branch escape hatch for stacking work on top of an open PR |
