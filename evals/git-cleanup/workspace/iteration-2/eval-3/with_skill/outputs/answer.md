# /git-cleanup — Phase 4 (Dirty State Detection), simulated

Session cwd: `/repo` (primary checkout, on `main`). Simulated: no command below was actually run.

## Inputs

`git worktree list`:

```
/repo                          33ff1155 [main]
/repo/.claude/worktrees/alpha  1a2b3c4d [feat/alpha]
/repo/.claude/worktrees/beta   5e6f7a8b [fix/beta]
```

Targets for Phase 4: the two linked worktrees (`alpha`, `beta`) plus the current directory (`/repo`,
which is also the primary worktree entry, so the plain current-directory check covers it — no separate
`git -C /repo` call is needed).

## Commands, in order (exactly as typed)

Per the skill: always `git -C <worktree-path>`, never `cd` into a worktree (a `cd` rebinds this session
to that worktree and would break the rest of `/git-cleanup`, which must operate from the primary checkout).

```bash
# 1. Uncommitted changes (tracked + untracked-not-ignored)
git -C /repo/.claude/worktrees/alpha status --porcelain
git -C /repo/.claude/worktrees/beta status --porcelain
git status --porcelain

# 2. Gitignored content (status --porcelain never lists ignored files)
git -C /repo/.claude/worktrees/alpha status --porcelain --ignored
git -C /repo/.claude/worktrees/beta status --porcelain --ignored
git status --porcelain --ignored

# 3. Session-lock check (starting-work locks every worktree it creates)
git worktree list --verbose
```

Not run: `git clean` (destructive, no place in an analysis-only phase; `--ignored` is read-only and
sufficient), and no `cd` of any kind.

## Results (per the scenario: every status command prints nothing)

| Location | `status --porcelain` | `status --porcelain --ignored` | Verdict |
|---|---|---|---|
| `/repo/.claude/worktrees/alpha` (`feat/alpha`) | empty | empty | clean — no uncommitted or gitignored content |
| `/repo/.claude/worktrees/beta` (`fix/beta`) | empty | empty | clean — no uncommitted or gitignored content |
| `/repo` (current dir, `main`) | empty | empty | clean |

Because the `--ignored` output is also empty, there is nothing to filter out under the
`.claude/settings.local.json` / `**/CLAUDE.local.md` exclusion, and no "Ignored (will also be deleted)"
block to show. No WARNING block is displayed for any location.

Lock status: depends on the `git worktree list --verbose` output (the plain `git worktree list` above does
not show lock reasons, which is why the verbose form is run). If either `alpha` or `beta` shows
`locked: <reason>` and is later recommended for removal, I note it against that worktree now so Gate 2
includes `git worktree unlock <path>` immediately before the plain worktree removal (never the force flag
as a substitute for unlocking, since that also bypasses the dirty-worktree safeguard).

## What I tell the user (folded into the Gate 1 analysis)

> **Worktrees — dirty-state check:** all clean.
> - `/repo/.claude/worktrees/alpha` (feat/alpha): no uncommitted changes, no gitignored files.
> - `/repo/.claude/worktrees/beta` (fix/beta): no uncommitted changes, no gitignored files.
> - Current directory `/repo` (main): clean.
>
> Removing either worktree would not lose any uncommitted or gitignored data. Whether a worktree is
> actually recommended for removal still depends on its branch's category from Phases 1–3 (merged /
> squash-merged / active work) — a clean worktree is not by itself a reason to delete it. Any worktree
> shown as locked will get an unlock step before removal.

Nothing is deleted at this point; the workflow continues to GATE 1 (AskUserQuestion with the full
analysis), and nothing destructive happens until GATE 2's explicit confirmation.
