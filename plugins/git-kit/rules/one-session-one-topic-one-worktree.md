# One Session, One Topic, One Worktree

## When this applies

Starting any new piece of work through `starting-work`; deciding whether to keep working in a session's
already-bound worktree versus starting something unrelated in it; or deciding whether to open a *second*
worktree for a new topic while an earlier topic's worktree from the same session is still open.

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

The symmetric, session-level half of the Rule — don't leave one topic's worktree open while starting a
second, unrelated one under the same session — exists for a different reason: the Stop exit-guard
(`guard-dirty-worktree-exit.sh`) checks only the worktree the session's current working directory is
actually in at the moment the agent's turn ends, not every worktree that session has ever locked. If a
session locks worktree A for one topic, then moves into worktree B for a second, unrelated topic without
finishing A first, a Stop event fired while sitting in B checks only B — A's dirty or unmerged state goes
unchecked at that moment, even though A is still locked and still at risk. Finishing one topic (and
leaving its worktree) before starting the next keeps the guard checking the worktree that's actually in
flight, rather than leaving an earlier one silently unprotected.
