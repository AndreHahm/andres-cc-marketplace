# Always Call starting-work Before the First Shippable Change

## When this applies

The moment a session is about to make its first shippable edit of a new piece of work — the first
`Edit`/`Write` to a tracked file that isn't pure investigation/reading — and no branch has been created
for that work yet, especially right after returning to `main`/`master` (e.g. immediately after
`finishing-work` completes a prior merge).

## Rule

Always invoke `Skill(git-kit:starting-work)` before making the first shippable change of a new piece of
work — never start editing files directly on `main`/`master` and only create a branch retroactively once
partway in. This applies even when the change looks small enough to "just start," and even when a prior
piece of work just finished and the natural next step feels like a continuation rather than a new task.

`starting-work` is the single place that syncs `main`, validates the branch name, and asks worktree vs.
plain branch — skipping it doesn't just skip branch creation, it skips all three checks at once, silently.

## Why

**Incident:** a real session began new work (porting a skill into a different plugin) immediately after
`finishing-work` returned the checkout to `main` post-merge, without invoking `starting-work` first. The
commit-message confirmation was also hand-rolled via a bare `AskUserQuestion` instead of routing through
`Skill(git-kit:commit)`, bypassing that skill's own step-3 main-branch check — the exact safeguard that
exists to catch this. The mistake was caught only by `starting-work`'s own incidental dirty-tree check
(triggered by an unrelated stash) and the user's direct, explicit intervention — no agent or skill logic
independently flagged it. `route-through-git-kit-lifecycle-skills.md` and
`one-session-one-topic-one-worktree.md` both already named this exact scenario before this incident, and
neither prevented it — a rule with no independent trigger of its own is easy to route around the moment a
session is already "just continuing" from a prior task rather than consciously starting a new one. This
rule exists to give that specific transition point (main → first edit) its own explicit, memorable
checkpoint, rather than relying on the broader routing rule's coverage being noticed in the moment.
