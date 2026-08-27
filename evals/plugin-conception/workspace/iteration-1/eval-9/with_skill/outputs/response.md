# plugin-conception — Standalone Run: skill-tester Quick Workflow False-Pass Behavior Fix

## Input

Session evidence: `skill-tester`'s Quick Workflow silently produces false-pass results when a smoke
test script crashes mid-run instead of failing loudly. Explicitly framed as friction with an existing
skill, not a new-plugin request, and explicitly stated to imply no new or restructured components — a
targeted behavior fix to `skill-tester`'s own error handling.

Invocation: standalone (directly by the user), Entry Route B (recent-session evidence), not nested
inside `plugin-lifecycle-upstream` or `plugin-lifecycle-maintenance`.

## Trace Through the Procedure

- **Entry Route B** (`## Entry Route B: Start From Recent-Session Evidence`) applies: the input is
  session evidence of friction with an existing skill, not a from-scratch idea. Per the route's own
  text, this is treated as "a seed, not the scope" — evidence handling follows
  `references/evidence-routing.md`'s 6-step procedure (identify source, recheck currency, separate
  symptoms from underlying need, merge duplicates, discard stale/non-actionable, obtain explicit
  approval before promoting to a planned change).
- **Step 1** builds the problem frame (problem, target user/scenario, desired outcome, evidence,
  constraints/non-goals, success signals), labeling assumptions and verifying the claim against current
  repo state rather than trusting the session evidence unverified.
- **Step 2** classifies. Per the task's own assumption, this lands on **Enhance** ("Preserve an existing
  component and add or improve behavior"), not Repair, Create, or Consolidate — consistent with the
  classification table's Enhance row.
- **Step 3** (shallow overlap check) is assumed, per the task, to confirm the classification and settle
  on the "no new or restructured components implied" branch — i.e., overlap is not "Full" (which would
  push toward Retain), so the skill proceeds past Step 3's stop gate to Step 4.
- **Steps 4-6** produce the full Conception Brief (all 12 sections, since Enhance is not the
  narrow-repair bypass case) — value proposition, baseline contract, implementation plan, etc.
- **Step 7** presents the completed brief via `AskUserQuestion` (approve and proceed / revise / merge /
  defer / reject). Per the task's assumption, the answer is "approve and proceed."

## Step 7's Hand-off Table

Per Step 7's own hand-off table:

> **Enhance / Consolidate / Reposition →** `plugin-planning` if new or restructured components are
> implied, otherwise directly to `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix).

Since the task explicitly stipulates "no new or restructured components implied," the destination is
**`plugin-lifecycle-downstream`'s Phase 8**, not `plugin-planning`.

## What the Skill Actually Does at the Phase 8 Hand-off (Standalone Invocation)

The skill does **not** attempt to invoke `plugin-lifecycle-downstream` directly, and does not invoke it
at all in this run. Two passages in Step 7 govern this, and both apply here:

1. The general Phase 8 constraint (applies regardless of standalone vs. nested):

   > **Phase 8 needs a findings bundle, not a brief — this skill never invokes it directly.**
   > `plugin-lifecycle-downstream`'s Phase 8 external-entry contract accepts only a schema-validated
   > findings bundle (`plugin-rulebook/references/evidence-schema.md`'s Finding/Report-Revision shape,
   > with a `baseline_commit` and scope manifest) and refuses anything else — a Conception Brief path
   > does not satisfy it, and this skill has no `Bash(git log:*)` grant to produce `baseline_commit`
   > even if it tried. Where Phase 8 is named as the destination above, the reformatting-and-invoking
   > step belongs to whichever orchestrator called this skill (e.g.
   > `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` Step 4 already does this
   > conversion) — never to this skill itself.

2. The standalone-specific instruction, which is the one that actually governs this run (since the
   input specifies standalone invocation, not nested inside an orchestrator):

   > **Standalone invocation:** for a `plugin-ideation`/`plugin-planning` hand-off, ask via
   > `AskUserQuestion` before invoking the target — never invoke it silently. For a Phase 8
   > destination, there is no orchestrator present to do the conversion: state the classification and
   > that a findings-bundle conversion is needed before Phase 8 can be reached, and stop — never
   > attempt to invoke `plugin-lifecycle-downstream` directly.

## Plain Answer

After the brief is approved, the skill does **not** attempt to invoke `plugin-lifecycle-downstream`
directly with the Conception Brief's path — that would violate its own explicit instruction ("never
attempt to invoke `plugin-lifecycle-downstream` directly"), and in any case a Conception Brief file
does not satisfy Phase 8's external-entry contract (which requires a schema-validated findings bundle
with a `baseline_commit` and scope manifest, not a brief).

Instead, since this is a **standalone** invocation with no orchestrator present to perform the
brief-to-findings-bundle conversion, the skill:

1. Writes the Conception Brief (all 12 sections) to
   `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md` and presents the artifact link
   plus summary, as Step 7 requires for every non-Retain/Reject/Defer outcome.
2. States the classification (Enhance) and that a findings-bundle conversion is needed before Phase 8
   can be reached.
3. **Stops there** — it does not invoke `plugin-lifecycle-downstream`, does not attempt any
   reformatting of the brief into a findings bundle itself, and leaves that conversion step for the
   user (or a future orchestrator run) to perform, per the skill's own stated division of
   responsibility ("the reformatting-and-invoking step belongs to whichever orchestrator called this
   skill ... never to this skill itself").

So the correct characterization is: the skill reports the classification and brief, explicitly flags
that a findings-bundle conversion is the blocking prerequisite for reaching Phase 8, and halts — it
never attempts a direct `plugin-lifecycle-downstream` invocation in the standalone case.
