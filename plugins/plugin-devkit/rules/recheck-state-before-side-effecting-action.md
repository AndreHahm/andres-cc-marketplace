# Re-Check State Before a Side-Effecting Action

## When this applies

Any skill, workflow, hook, or script that (a) observes external async state it doesn't fully
control (a CI run's conclusion, a bot's reaction, a PR's head SHA, whether a workflow run exists
yet, another maintainer's action) and (b) then takes an irreversible or side-effecting action
(posting a comment, rerunning a workflow, merging, resolving a review thread) based on that
observation.

## Rule

Before any side-effecting action whose correctness depends on previously-observed external state,
re-check that state immediately before the action fires — not a check inherited from an earlier
step, however recent. Apply this as one explicit design pass per skill, not a per-incident patch
added reactively each time a reviewer finds the next stale window:

1. List every side-effecting call in the skill.
2. For each one, name what external state it depends on, when that state was last observed, and
   whether the gap between observation and action is long enough for the state to have changed —
   a network round-trip, a `Skill()`/`Agent()` dispatch, a human confirmation step, or another step
   doing unrelated work in between are all long enough.
3. For any call whose dependency isn't re-checked immediately before it fires, add the re-check.
4. Enumerate the full state space of whatever's being observed rather than assuming a binary — a
   GitHub Actions run conclusion has at least
   success/failure/cancelled/timed_out/neutral/action_required, not just pass/fail.

This formalizes what the Master pre-push checklist already asks per side-effecting call
(`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`, lines 567-569): *"Does this skill/workflow observe
external async state ... and then take a side-effecting action on it? Does every such action have
its own immediate re-check right before it fires, not a check inherited from an earlier step?"*
This rule turns that checklist line into an upfront design pass run once per skill, rather than a
question answered reactively after a reviewer has already found the next stale window.

## Why

PR #51 (`codex-review-recovery`) is documented in `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` as the
richest PR in the review dataset — 7-8 Codex rounds, ~15 findings — and the same underlying shape
recurred in a new place almost every round: the skill observed some external state (a PR's head
SHA, a workflow run's conclusion, whether a run exists yet) and then took an irreversible action
based on a check that had already gone stale by the time the action executed. This is a textbook
TOCTOU (time-of-check-to-time-of-use) class. Five distinct occurrences are documented across
rounds 2, 4, 5 (twice), 6, and 7 — each its own re-check window found and closed independently,
because each fix addressed only the one instance a reviewer happened to flag that round, rather
than being applied as a systematic principle across every side-effecting step in the skill.

This is the TOCTOU class recurring at the skill-authoring level, not just the code level —
[[verify-tool-behavior-before-instructing]] catches "does this tool/API behave the way I assumed
it does," but says nothing about "has the state I already correctly observed changed by the time I
act on it." The two failure modes are independent, and both showed up repeatedly in the same PR.
