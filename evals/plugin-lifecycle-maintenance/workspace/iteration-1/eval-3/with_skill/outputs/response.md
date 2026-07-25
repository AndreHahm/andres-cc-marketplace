# Acting on a plugin-foo retro — which workflow and what happens next

## 1. Workflow chosen: `improve-a-plugin.md`

The user just ran a retro on `plugin-foo` and wants to act on the findings. That's exactly the "retro-driven improvement" case the skill describes: findings come from `analyzing-sessions`, the human picks which to act on, then it hands off to `plugin-lifecycle-downstream`'s Fix phase.

Not `enhance-a-plugin.md` — that's for comparison-driven findings (`plugin-comparison` against another target), and there's no second target named here.

Not `modernize-plugin-dev.md` — that's specifically for keeping `plugin-devkit`'s own rules current against official Claude Code docs, unrelated to a general session retro.

## 2. Concrete next step (Step 1 → Step 2 of improve-a-plugin.md)

**Step 1: Retro.** Since the user says they "just ran" the retro, the report may already exist from that prior `analyzing-sessions` invocation — but per the workflow's own entry condition, I'd invoke `analyzing-sessions` (via `Skill`) scoped to `plugin-foo` (or the relevant session range) if I don't already have that report in hand, and wait for its grouped output: a SWOT per component, suggestions ordered P1→P3, and a Top 5 Actions list. Exit criteria: the report must contain at least one suggestion — if it's empty, I state that plainly and stop, since there's nothing to act on.

**Step 2: Human Decides.** I present the Top 5 Actions and the full P1→P3 suggestion list, then ask via `AskUserQuestion` (multiSelect) which suggestions to act on now — "none of these, stop here" is an explicitly valid answer. If the user wants any chosen suggestion expanded into a full WHAT/WHY/HOW plan before committing to it, I invoke the `enhancement-suggestor` agent against it first, rather than skipping straight to applying.

Only after that human-approved list is finalized does Step 3 reformat it into `plugin-grader`-shaped input and hand off to `plugin-lifecycle-downstream`'s Phase 3 (Fix) — entering directly at Phase 3, skipping Phases 1-2, since the findings already came from the retro rather than a fresh audit.

## 3. Human-decision gate before anything is applied?

Yes — mandatory. The skill's Boundaries section is explicit: "**Never decides what to fix.** Every workflow surfaces findings and stops for an explicit `AskUserQuestion` decision before anything is applied — no workflow auto-selects or auto-applies a suggestion, gap, or rule fix on its own judgment."

Concretely, Step 2 (`Human Decides`) is a hard gate between Step 1 (finding source) and Step 3 (apply/hand-off). Nothing gets applied to `plugin-foo` until the `AskUserQuestion` multiSelect returns a human-approved list — and an empty selection ("none of these") is a fully valid, workflow-ending answer. The skill does not auto-apply retro findings itself under any circumstance.
