---
name: starting-work
description: >-
  Sync local main, then create a properly named branch (or worktree) to start new work. Use when
  starting new work, asked to "start a new branch", "create a branch for X", "sync main and branch
  off", or "set up a worktree for this feature" — before any commits happen. Validates the branch name
  against git-kit's <type>/<description> convention and offers a worktree as an alternative to a plain
  branch checkout.
argument-hint: (optional) branch type and description, e.g. "feature add-user-auth"
allowed-tools: Bash(git fetch:*), Bash(git checkout:*), Bash(git pull:*), Bash(git status:*), Bash(git branch:*), Bash(git worktree:*)
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
   If not already on `main`, ask via `AskUserQuestion` — "Base the new branch off `main`, or off the
   current branch (`<name>`)?" — default `main`. If basing off `main`: `git checkout main`, then
   `git pull --ff-only`. If that fails (diverged local main), tell the user exactly why and stop rather
   than force anything. If basing off the current branch, skip the checkout/pull — see
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
   there instead of guessing or duplicating the list.
3. **Ask worktree or plain branch**: `AskUserQuestion` — "Create a plain branch, or a separate worktree
   for this?" See `references/worktree-decision.md` for the tradeoffs to mention if the user wants
   guidance rather than a snap decision.
4. **Create**:
   - Plain branch: `git checkout -b <type>/<description>`.
   - Worktree: compute a default sibling path following `git-worktrees`' own naming convention
     (`../<repo-dir-name>-<description>`), show it to the user for confirmation or override, then
     `git worktree add -b <type>/<description> <path>`.
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
- [ ] Step 3's worktree-vs-branch question always uses `AskUserQuestion`, never assumed
- [ ] A dirty working tree at step 1 always stops the flow with a pointer to `commit`, never proceeds
