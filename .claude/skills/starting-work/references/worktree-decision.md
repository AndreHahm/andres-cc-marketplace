# Worktree vs. Plain Branch, and the Branch-Off-a-Branch Case

## When a worktree beats a plain branch checkout

Prefer a **worktree** when the current working directory needs to stay untouched while the new work
happens in parallel — e.g. reviewing someone else's PR without disturbing in-progress local changes,
running a long build/test in one branch's state while continuing to edit another, or comparing two
branches' files side by side. `git-worktrees` (this plugin's other skill) covers the deeper patterns
once a worktree exists — comparing, selectively merging, and cleaning up.

Prefer a **plain branch** (`git checkout -b`) for the common case: one person, one branch, linear work,
no need to keep another branch's files simultaneously on disk.

## Branching off a branch, not off main

Step 1 defaults to syncing and branching from `main`, but sometimes that's wrong on purpose — e.g.
stacking a follow-up change on top of work still in an open PR, where basing off `main` would lose the
dependency and create a merge conflict once both land. In that case the user should choose "base off the
current branch" at step 1's prompt; `starting-work` skips the `main` sync/checkout entirely and creates
the new branch (or worktree) directly from the current `HEAD`.

This is a deliberate escape hatch, not the common path — most new work should start from a synced
`main`, so `main` stays the default answer at step 1's prompt.
