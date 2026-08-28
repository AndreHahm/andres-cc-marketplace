# Read and Re-Trace Skill Chains Before Finalizing

## When this applies

Two related situations inside a multi-skill lifecycle chain (e.g.
`starting-work → commit → create-pr → merge-pr → finishing-work`, or any workflow skill that dispatches
other skills in sequence):

1. A fix changes *where* (cwd/worktree) or *when* (before/after another call) a step in the chain runs.
2. Writing an instruction that invokes another skill (`Skill(X)`) as part of that chain.

## Rule

**Re-trace the whole chain, not just the step you fixed.** When a fix changes the timing or location of
one step in a multi-skill chain, re-simulate the *entire* chain end-to-end — one call at a time, tracking
cwd/branch/captured-variable state at each point — before considering the fix done. A chain that was just
edited is exactly the chain most likely to have a second broken link nearby; patching only the symptom
just found leaves the same root cause free to resurface downstream.

**Read `Skill(X)`'s actual current SKILL.md before writing the call.** Before writing an instruction that
invokes another skill inside a lifecycle sequence, read that skill's full SKILL.md (not just its
argument-hint or one-line description) and check specifically for:
- Any `AskUserQuestion` it fires unconditionally after success — these silently branch the calling
  skill's own flow.
- Any assumption about current branch/cwd.
- Any argument whose omission falls back to "current branch" or similar ambient state, which can
  silently resolve to the wrong thing.

Both checks apply together: a chain re-trace that doesn't also re-read each dispatched skill's *current*
instructions can still miss a nested ask or cwd assumption that was already there, just never traced.

## Why

**PR #54** (`running-a-full-retrospective` Phase 5 redesign, 7 Codex review rounds) is the concrete case
this rule generalizes from. Round 1 fixed "the worktree never closes" by adding a
`commit → create-pr → merge-pr → finishing-work` chain. Round 2's own fix (an explicit `cd` into the
worktree) broke `finishing-work`'s precondition, caught in round 3. Round 3's fix (`cd` back before
`finishing-work`) needed a `Bash(cd:*)` grant, missing until round 4 — round 4 also found the "confirm
worktree closed" claim was false for the pipeline hand-off path. Round 6 found `finishing-work` was still
being invoked bare, so `gh pr view` resolved the wrong branch's PR. Round 7 found two more
nested-dispatch collisions in the same chain. Six of seven review rounds were ripple effects of one
original design gap, each caught one link at a time instead of all at once.

Separately, rounds 4, 6, and 7 all trace back to writing `Skill(git-kit:X)` without first reading X's own
SKILL.md — a bare `finishing-work` call resolving the wrong branch's PR, a stale cache-glob issue, and
two nested-dispatch collisions (`commit`'s own Auto-PR step, `merge-pr`'s own post-merge-sync prompt)
firing unexpectedly. [[recheck-state-before-side-effecting-action]] already covers a narrower, related
piece of this — re-checking external async state immediately before a side effect — but says nothing
about re-tracing a chain's own cwd/branch/variable state after a timing fix, or about a `Skill()`
dispatch by name resolving to the *primary checkout's* copy of a skill, never a session's own unmerged
worktree edit to it, even mid-session while actively editing that exact component. This rule states the
general authoring discipline both patterns draw on: a multi-skill chain that was just edited needs a
full re-trace, and a skill about to be dispatched needs its current instructions actually read first.
