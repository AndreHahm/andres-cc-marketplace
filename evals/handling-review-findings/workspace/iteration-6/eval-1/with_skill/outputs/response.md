## Part 1: The exact next action

I dispatch the `commit` skill, explicitly requesting the push:

```
Skill(commit, args: "--push")
```

(using the bare, unprefixed skill name — not `git-kit:commit` — per this repo's own
`route-through-git-kit-lifecycle-skills.md` dispatch-name note, which states that in this repo's dev
sessions git-kit's skills resolve under their bare name via the `.claude/`-mirrored copy, and that
`Skill(git-kit:commit)` fails with `Unknown skill: git-kit:commit`.)

**Why this exact form:**

- Workflow step 4 (Fix path) of `handling-review-findings` is explicit: once verification of the fix
  passes, "commit via `Skill(commit)` with `--push` (never a raw `git commit` — see
  `.claude/rules/route-through-git-kit-lifecycle-skills.md`), explicitly requesting the push so it isn't
  left to `commit`'s own default `AskUserQuestion` (`commit_auto_push` defaults to `false`)."
- The reply-with-SHA/resolve steps that come after are conditional on the push having actually landed —
  "Reply-with-SHA is conditional on the push having actually landed" — so requesting `--push` explicitly
  (rather than letting `commit` default to no-push and asking separately) is required to keep the
  workflow's next step (reply to the thread with the fixing commit's SHA, then resolve it) valid.
- A raw `git commit`/`git push` is disallowed here — the skill's own tool-routing rule
  (`route-through-git-kit-lifecycle-skills.md`) requires the lifecycle skill specifically because the raw
  command skips staging review, sensitive-file scanning, and message confirmation that `commit` adds.

## Part 2: If `Skill(commit, args: "--push")` errored out (e.g. "Unknown skill: X")

Per this skill's own text, I do **not** fall back to hand-rolling the commit/push myself. The SKILL.md
states this directly, in its own opening section (not just by cross-reference):

> "A task inside 'When to Use' below is never triaged by hand instead of through this skill. If
> dispatching this skill fails (e.g. `Skill(handling-review-findings)` errors — check the exact form
> your own session's available-skills listing uses; see
> `.claude/rules/route-through-git-kit-lifecycle-skills.md`'s dispatch-name note), stop and report the
> failure to the user rather than manually narrating this skill's own procedure from memory. A
> hand-rolled reimplementation looks identical in its output to a real run but silently drops whatever
> this skill's own round/dedup budgeting, severity-gate discipline, or marker-handshake step was meant
> to enforce (issue #367)."

Applying that same principle to the nested `Skill(commit)` dispatch specifically (the cross-referenced
`route-through-git-kit-lifecycle-skills.md` rule, which `handling-review-findings` explicitly points to
for exactly this situation, states it for any of the six lifecycle skills, `commit` included):

> "Never silently substitute a manual reimplementation for a failed or skipped dispatch. If a `Skill()`
> call to one of these six lifecycle skills errors (e.g. `Unknown skill: ...`), or if a task squarely
> inside one of their documented 'When to Use' lists is about to proceed via raw `git`/`gh` commands
> instead of the skill, stop and report the dispatch failure or the decision to skip it to the user —
> never fall back to manually narrating or reimplementing the skill's own documented procedure (marker
> handshakes, staging review, round/dedup budgets, reply-then-resolve discipline) as a silent
> substitute."

So concretely, on an "Unknown skill: X" error I would:

1. First check whether I used the exact dispatch form this session's own available-skills listing shows
   (bare `commit`, not a `git-kit:`-prefixed or otherwise-scoped form) — the dispatch-name note is the
   first thing to verify, since a wrong prefix is a known, specific cause of this exact error.
2. If the correctly-named dispatch still errors, **stop** and report the failure to the user plainly —
   I do not proceed to run a raw `git add`/`git commit`/`git push` myself as a substitute, even though
   the fix is already verified and ready to ship. I would not reply to or resolve the review thread
   either, since Workflow step 4 makes reply/resolve conditional on the push having actually landed via
   the proper path.
3. I would not narrate or fake having run `commit`'s own staging-review/sensitive-file-scan/message-
   confirmation sequence from memory — a hand-rolled version "looks identical in its output to a real
   run but silently drops" those safeguards, which is precisely the failure mode both cited passages
   warn against.
