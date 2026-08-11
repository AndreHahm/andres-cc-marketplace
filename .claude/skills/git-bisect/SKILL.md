---
name: git-bisect
description: >-
  Guides an automated or manual git bisect session to find the exact commit that introduced a regression, running a test command at each step or walking the user through manual good/bad decisions. Use when hunting for the commit that broke a test, a feature, a build, or introduced a performance regression.
allowed-tools: Bash(git bisect start:*), Bash(git bisect good:*), Bash(git bisect bad:*), Bash(git bisect log:*), Bash(git bisect reset:*), Bash(git show:*), Bash(git branch:*), Bash(git status:*), Bash(npm:*), Bash(yarn:*), Bash(pnpm:*), Bash(pip:*), Bash(pytest:*), Bash(cargo:*), Bash(go:*)
argument-hint: [good-commit] [bad-commit] | --auto [test-command] | --reset | --continue
---

# Git Bisect Helper

Guide a git bisect session to find the commit that introduced a regression. $ARGUMENTS selects the mode: a good/bad commit pair for manual guided bisect, `--auto [test-command]` for automatic bisect, `--continue` to resume, or `--reset` to abort and clean up.

**On the git bisect grant:** scoped to exactly the 5 subcommands this skill's modes document —
`start`/`good`/`bad`/`log`/`reset` — each its own explicit `Bash(git bisect <subcommand>:*)` entry rather
than a blanket `Bash(git bisect:*)`. Corrected 2026-08-11: an earlier version of this note claimed the
blanket grant "couldn't be narrowed further," which was wrong — `Bash(git bisect:*)` also permits
`git bisect run <command>`, letting a bisect session execute an arbitrary command per commit, which this
skill never documents or uses.

## Instructions

1. **Check current state**: run `git status`, `git branch --show-current`, and `git bisect log 2>/dev/null || echo "No active bisect session"` to see if a session is already in progress.
2. **Create a backup branch** before starting a new session (`git branch bisect-backup-<timestamp>`), so the original position is always recoverable.
3. Dispatch to the mode selected by `$ARGUMENTS`:

### Automatic bisect (`--auto [test-command]`)

1. `git bisect start`, then mark the given good/bad commits (or ask the user for them if not supplied).
2. At each bisect step, run the given test command via `Bash`.
3. Mark the commit `git bisect good` (exit code 0) or `git bisect bad` (non-zero).
4. Repeat until `git bisect` reports the first bad commit, then report it with its message, author, date, and changed files.

**Test-command scope**: `allowed-tools` only covers `npm`/`yarn`/`pnpm`/`pip`/`pytest`/`cargo`/`go`. If the user's test command needs a different tool (e.g. `bundle`, `mvn`, `gradle`), tell them explicitly that this skill can't run it under its current tool scope, and either ask them to run that step manually and report good/bad themselves, or fall back to Manual Guided Bisect.

### Manual guided bisect (`[good-commit] [bad-commit]`)

1. `git bisect start`, then `git bisect good <good-commit>` and `git bisect bad <bad-commit>`.
2. At each step, show the current commit (`git show --name-only --pretty="%H %s (%an, %ar)" HEAD`) and the changed files.
3. Ask the user via `AskUserQuestion` whether this commit is good or bad, then run `git bisect good`/`git bisect bad` accordingly.
4. Repeat until bisect reports the first bad commit.

### Continue (`--continue`)

Run `git bisect log` to show progress so far, then resume whichever mode (automatic/manual) the in-progress session appears to be using, based on what's already been marked.

### Reset (`--reset`)

Run `git bisect reset` to end the session and return to the original branch. Report the backup branch created in step 2 (if any) so the user can delete it once they've confirmed everything is fine.

## Reporting the result

Once the first bad commit is found, report: the commit hash, author, date, message, and changed files. Suggest recovery commands as text for the user to run themselves (this skill does not execute them): `git revert <bad-commit>` to undo it, or `git cherry-pick` to selectively keep the good parts of a mixed commit.

## Safety

- Always create a backup branch (step 2) before starting — a bisect session moves `HEAD` repeatedly via `git checkout`, and the backup is the recovery path if anything goes wrong.
- Never mark a commit good/bad without either a test result (automatic mode) or explicit user confirmation via `AskUserQuestion` (manual mode) — don't guess.
- If `git bisect` reports the range doesn't reproduce the regression (the given "bad" commit tests good, or vice versa), stop and tell the user rather than continuing with a broken range.

## Testing & Validation

**Verify this skill activates on:**
- "find the commit that broke the login test"
- "bisect this regression"
- "--auto npm test" / "run an automatic bisect with pytest"
- "which commit introduced this performance regression"

**Verify it does NOT activate on:**
- "rebase my branch onto main" → `git-rebase-sync`
- "add a note to this commit about the test results" → `git-notes`
- "start a new branch to investigate this bug" → `starting-work`
- "compare these two branches side by side" → `git-worktrees`

**Quality gates:**
- [ ] Step 1 always checks for an in-progress bisect session (`git bisect log`) before starting a new one
- [ ] Step 2 always creates a backup branch before `git bisect start` runs
- [ ] Automatic mode never marks a commit good/bad without an actual test-command exit code — never guesses
- [ ] Automatic mode never silently runs a test command outside the `npm`/`yarn`/`pnpm`/`pip`/`pytest`/
      `cargo`/`go` scope — always tells the user and offers manual mode or a self-run step instead
- [ ] Manual mode never marks a commit good/bad without explicit `AskUserQuestion` confirmation
- [ ] `--reset` always runs `git bisect reset` and reports the backup branch — never deletes it automatically
- [ ] A bisect range that doesn't reproduce the regression always stops and reports to the user rather than
      continuing with a broken range
- [ ] The `git bisect` grant stays as 5 explicit per-subcommand entries (`start`/`good`/`bad`/`log`/`reset`)
      — never collapsed back to a blanket `Bash(git bisect:*)`, which would also permit `git bisect run`
