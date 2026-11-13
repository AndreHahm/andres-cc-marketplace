# finishing-work: steps 5 and 6 (simulated)

Context: the session runs in the primary checkout `/repo`. PR #716 is MERGED, and `headRefName` is
`fix/ledger-outcomes`, which passed step 1's `^[A-Za-z0-9._/@+=-]+$` validation. Steps 1 to 4 are done.

## Step 5: Verify clean state

Commands, in order, all run from `/repo`. No `cd` is used anywhere:

```bash
git status --porcelain
git worktree list
git -C /repo/.claude/worktrees/ledger-outcomes status --porcelain
git -C /repo/.claude/worktrees/ledger-outcomes status --porcelain --ignored
```

Reasoning:

1. `git status --porcelain` in `/repo` comes back empty, so the current (primary) worktree is clean.
2. I compare the `git worktree list` output against the PR's `headRefName` from step 1
   (`fix/ledger-outcomes`), not against `git branch --show-current`, which is now `main`.
   `/repo/.claude/worktrees/ledger-outcomes` is still checked out on `[fix/ledger-outcomes]` and is
   marked `locked`. That is the merged PR's branch, so I flag it.
3. I check that worktree with `git -C <worktree-path> status --porcelain` and never `cd` into it, not even
   in a chained command. A `cd` would rebind this session to the worktree, and `/git-cleanup` would then
   refuse to run from this session. The status prints ` M notes.md`, an uncommitted modification. The
   `--ignored` variant lists gitignored content as well. Per the scenario it also prints ` M notes.md`,
   with no ignored entries beyond that.
4. I only flag it. I don't modify, stash, discard, unlock or remove anything in that worktree.

## Step 6: Hand off

What I tell the user:

> PR #716 (`fix/ledger-outcomes`) is confirmed merged. Local `main` in `/repo` is synced with the
> remote, remote-tracking refs are pruned, and the primary checkout is clean (`git status --porcelain`
> is empty).
>
> **Heads-up: a leftover worktree.** `/repo/.claude/worktrees/ledger-outcomes` is still checked out on
> the merged branch `fix/ledger-outcomes`. It is **locked**, and it has an **uncommitted change**:
> ` M notes.md`. I haven't touched it. Before you delete it, check whether `notes.md` holds anything
> you want to keep. The PR is already merged, so you'd need to copy it out or commit it on a new branch.
> Removing the worktree would discard that change, and because the worktree is locked a plain remove
> won't work without unlocking it first.
>
> **Next step:** run `/git-cleanup` yourself to review and delete the merged branch
> `fix/ledger-outcomes` and its worktree. I won't invoke it for you: it only runs when you call it
> directly. This session started in the primary checkout (`/repo`) and never `cd`'d into the
> worktree, so `/git-cleanup` can run from right here.

Notes:
- I don't invoke `git-cleanup` (no `Skill()` call). It has `disable-model-invocation: true`.
- This session isn't sandboxed to a worktree (it is in `/repo`), so the reminder to switch to a
  primary-checkout session doesn't apply.
- I run no `git worktree remove`, `git worktree unlock`, `git branch -d`, `git stash` or
  `git checkout -- notes.md` commands. Deleting the branch and the worktree is `/git-cleanup`'s job.
