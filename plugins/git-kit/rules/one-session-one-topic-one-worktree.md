# One Session, One Topic, One Worktree

## When this applies

Starting any new piece of work through `starting-work`, or deciding whether to keep working in a
session's already-bound worktree versus starting something unrelated in it.

## Rule

A worktree created for a session is scoped to one topic. Once `starting-work` has created a worktree for
a piece of work, don't start a second, unrelated piece of work in that same worktree — run `starting-work`
again for the new topic, which creates its own worktree. Symmetrically, a session shouldn't keep working
across worktrees for unrelated topics; when the current topic is done, finish it (`finishing-work` /
`/git-cleanup`) before starting the next one rather than accumulating multiple open topics in flight under
one session.

This is a convention for how `starting-work`-created worktrees get used, not a mechanical lock — nothing
in git-kit enforces "topic" the way a file lock enforces exclusive access, since there's no way to check
whether two pieces of work are actually the same topic from git state alone.

## Why

A worktree that accumulates unrelated work becomes hard to clean up safely: `git-cleanup` has to reason
about whether *all* the work in it is done, not just the piece you're thinking about right now, and a
worktree with mixed topics is more likely to get force-deleted along with unrelated in-progress changes
by mistake. One worktree per topic keeps `git-cleanup`'s merged/unmerged/dirty analysis meaningful — it
can trust that "this worktree's branch merged" means "this worktree is done," which isn't true if a
second, unrelated topic is still active in the same directory.
