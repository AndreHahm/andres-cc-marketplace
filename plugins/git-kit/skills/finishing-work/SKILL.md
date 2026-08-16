---
name: finishing-work
description: >-
  Sync back to a clean, current main after a PR merges — confirm the merge landed, switch to main,
  fast-forward pull, prune remote-tracking branches, and verify a clean repo state. Use when finishing
  work, asked to "I just merged, clean this up", "sync back to main after merge", "finish this branch",
  or "get back to a clean main". Never deletes branches or worktrees itself — hands off to `/git-cleanup`
  for that.
argument-hint: (optional) PR number or URL — defaults to the current branch's PR if omitted
allowed-tools: Bash(gh pr view:*), Bash(gh repo view:*), Bash(git checkout:*), Bash(git pull:*), Bash(git fetch:*), Bash(git status:*), Bash(git worktree list:*), Bash(git branch --show-current:*), Bash(git symbolic-ref refs/remotes/origin/HEAD:*), Bash(git ls-remote --heads origin:*), Bash(gh api -X DELETE repos/*/git/refs/heads/*:*), Bash(uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/remap-handoff-shas.py":*), Read
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

1. **Confirm the PR actually merged**: capture the current branch with `git branch --show-current` (used
   only to detect the mismatch below — step 4's own worktree check uses `headRefName`, not this value).
   Run `gh pr view $ARGUMENTS --json state,mergedAt,headRefName,url`. If `state` isn't `MERGED` (still
   open, or closed without merging), tell the user exactly which state it's in and stop — don't sync
   main on an assumption. If `$ARGUMENTS` was given, check whether the returned `headRefName` differs
   from the branch just captured, or the returned `url`'s `<owner>/<repo>` segment differs from
   `gh repo view --json nameWithOwner --jq .nameWithOwner` (the current repository) — on either
   mismatch, stop and ask via `AskUserQuestion` whether to proceed anyway rather than silently
   continuing on an unrelated PR's merge state.
1.5. **Ensure the remote branch was actually deleted** (only when the intent was to delete it): read
   `merge_auto_delete_branch` (default `true`) the same way `commit`/`merge-pr` do —
   `.claude/git-kit.local.json` if it exists and sets the field, else the git-tracked
   `${CLAUDE_PLUGIN_ROOT}/git-kit.settings.json` default. If `false`, skip this step entirely — a
   surviving remote branch is intentional in that case. If `true`, check whether `origin/<headRefName>`
   (from step 1) still exists: `git ls-remote --heads origin <headRefName>`. Empty output means it's
   already gone — nothing to do. Non-empty output means `gh pr merge --delete-branch` didn't finish its
   job: that command deletes the local and remote branch together, but its local half needs to check out
   the default branch first, which fails with `fatal: '<default>' is already used by worktree ...`
   whenever the default branch is already checked out elsewhere — near-guaranteed if the merged branch had
   its own worktree, since the primary checkout almost always has the default branch checked out. When
   that local checkout fails, `gh` silently skips the remote deletion too (confirmed live, 2026-08-16,
   against this repository's real PR #41: the remote branch was still present days after the merge). Finish
   the job it should have done: validate `headRefName` against `^[A-Za-z0-9._/-]+$` (git ref names can
   otherwise contain shell metacharacters — same check `merge-pr`'s own manual-delete path applies before
   this exact command) — stop and report if it doesn't match, don't proceed. Otherwise delete it directly:
   `gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<headRefName>` (owner/repo from step 1's
   `nameWithOwner` check). Report plainly that this fallback ran and why — never a silent extra deletion.
2. **Return to main**: resolve the actual default branch rather than assuming `main` —
   `git symbolic-ref refs/remotes/origin/HEAD` (falling back to `main` if that fails, e.g. no `origin`
   remote configured), then `git checkout <resolved-branch>`, then `git pull --ff-only`. If the checkout
   or pull fails, tell the user why and stop rather than force anything — three distinct reasons, not just
   one: a diverged local branch; the resolved branch already checked out in another worktree (git refuses
   with "already used by worktree"); or **this session is itself sandboxed to a worktree checkout** rather
   than the primary checkout — a worktree-sandboxed session cannot `cd` out to the primary repo root, so
   even a successful-looking checkout here would switch the *worktree's own* branch, not the primary
   checkout's, leaving the actual goal (a synced primary `main`) unmet. Tell the user plainly which of the
   three applies, and — for the sandboxed case specifically — that they need to run `finishing-work` (and
   subsequently `/git-cleanup`) from a session started in the primary checkout instead. `allowed-tools`
   grants `Bash(git checkout:*)` broadly for this step since the resolved branch name is dynamic and can't
   be statically pinned — this skill never runs the file-restore form (`git checkout -- <path>`), only
   branch checkout.
3. **Prune**: `git fetch --prune` to drop stale remote-tracking refs for branches deleted on the remote.
4. **Remap stale build-handoff-writer SHAs** (this repository only — a no-op if `.claude/output/` doesn't
   exist here): a PR merged via GitHub's rebase-merge or squash-merge rewrites every commit hash, which
   silently breaks any `.claude/output/**/*.md` report (chiefly `build-handoff-writer`'s own reports) that
   recorded the pre-merge SHAs — they end up pointing at commits unreachable from `main`. Run
   `uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/remap-handoff-shas.py" --pr <PR number from step 1> --repo-root <repo root> --base <resolved default branch from step 2>`
   and report its output as-is: which SHAs it remapped (and in which report files), and which it could not
   resolve (no unique commit-message or patch-id match — these are left untouched, never guessed). This
   only ever writes to gitignored `.claude/output/` content, never a tracked file, so it needs no commit
   or confirmation gate of its own — just report the result.
5. **Verify clean state**: `git status --porcelain` on the current worktree must come back empty. Also
   run `git worktree list` and compare against the PR's `headRefName` from step 1 (not the
   `git branch --show-current` value, which only served step 1's own mismatch check) — if another
   worktree is still checked out on that specific branch, flag it (especially if it has uncommitted
   changes) without touching it.
6. **Hand off**: tell the user local `main` is synced and current, and that `/git-cleanup` is the next
   step to review and delete the merged branch (and worktree, if any). Never invoke `git-cleanup`
   automatically — it has `disable-model-invocation: true` by design and only runs on direct user
   invocation. **If this session is sandboxed to a worktree checkout**, remind them here too:
   `/git-cleanup` needs to run from a session started in the primary checkout, not from inside the
   worktree — the same constraint step 2 above stops on, not a separate one.

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
- [ ] Step 1 always binds the merge confirmation to a specific branch and repository (`headRefName`,
      `nameWithOwner`) — never assumes `$ARGUMENTS` refers to the current branch/repo without checking,
      and always stops to ask on a mismatch rather than continuing silently
- [ ] Step 6 always tells the user to run `/git-cleanup` themselves — never invokes it via `Skill()`
- [ ] A session sandboxed to a worktree checkout is told plainly, at both step 2 and step 6, that it
      cannot complete the sync/hand-off from there — never left to discover the `cd` failure on its own
- [ ] A diverged local default branch at step 2 always stops rather than force-syncing
- [ ] Step 4 always runs `remap-handoff-shas.py`, even when the merge preserved SHAs unchanged (a regular
      merge commit) — the script itself detects the no-op case and exits cleanly; the skill never tries to
      pre-guess whether a remap is needed
- [ ] Step 4's script never touches a tracked file — only `.claude/output/**/*.md`
- [ ] An unresolved commit (no unique message or patch-id match) is always reported to the user, never
      silently dropped or guessed at
- [ ] Step 1.5 always skips when `merge_auto_delete_branch` is `false` — a surviving remote branch is
      never "fixed" when the setting says not to delete it
- [ ] Step 1.5 never assumes the remote branch is gone — always checks with `git ls-remote --heads origin`
      rather than trusting `gh pr merge --delete-branch`'s exit code or the PR's `MERGED` state alone
- [ ] Step 1.5 always validates `headRefName` against `^[A-Za-z0-9._/-]+$` before the `gh api -X DELETE`
      call, and skips with a report (never proceeds) on a name that fails this check

**Step 1.5 — verified live, 2026-08-16, against this repository's real stale remote branch:** PR #41's
`feat/plugin-auditor-codex-integration` remote branch was confirmed still present on `origin` (via
`git ls-remote --heads origin`) three days after the PR merged with `merge_auto_delete_branch: true` — the
exact failure this step exists to repair, root-caused to the worktree-checkout conflict described above.
Running step 1.5's exact procedure (ref-name validation, then `gh api -X DELETE
repos/AndreHahm/andres-cc-marketplace/git/refs/heads/feat/plugin-auditor-codex-integration`) deleted it
successfully; a follow-up `git ls-remote` confirmed it was gone.

**Step 4 (`remap-handoff-shas.py`) — verified live, 2026-08-16, against this repository's real PR #41**
(a rebase-merge where all 14 commits landed on `main` with new hashes): correctly identified all 14 as
unreachable from `main`, resolved every one via commit-message match, and updated every stale reference —
including narrative mentions outside the `## Commits` table itself — across the two affected
`build-handoff-writer` reports. A follow-up re-run against the same PR correctly reported nothing left to
remap (idempotent).
