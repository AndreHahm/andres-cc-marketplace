# What Gate 1 does when Phase 1 (Conceive) classifies the concept as Enhance

Source: `plugin-lifecycle-upstream/workflows/design-a-plugin.md`, "GATE 1" section (lines 19-28), and `SKILL.md` line 83 / the Phases table (line 73).

## Step 1 — Present the artifact link first

Gate 1 always opens with the artifact link line, regardless of classification:

```
📄 Conception Brief written: `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`
```

Then it presents the brief's classification and rationale (here: **Enhance**, plus `plugin-conception`'s stated reasoning for why this is a modify-existing-component case rather than a new-component case).

## Step 2 — Branch on classification

Gate 1 branches on the Conception Brief's classification:

- **If Create:** ask via `AskUserQuestion` (proceed to Ideate / revise the concept / stop) and only continue into Phase 2 on explicit approval.
- **If anything else — Enhance, Repair, Consolidate, Reposition, Retain, Reject/Defer:** the pipeline is creation-only and **stops at Gate 1**. No `AskUserQuestion` proceed/revise/stop prompt is used in this branch — there's nothing to gate into, since there's no Phase 2 to proceed to.

Since the classification here is **Enhance**, the second branch applies.

## Step 3 — What "stops here" concretely means

Per `workflows/design-a-plugin.md`'s Gate 1 text and `SKILL.md`'s "Conceive is a qualifier, not an interview" section:

1. The pipeline **does not proceed to Phase 2 (Ideate)** — Enhance is never forced through Ideate/Plan/Design/Build.
2. It **states `plugin-conception`'s own hand-off target plainly** — one of:
   - `plugin-planning` directly (skip straight to planning the modification, bypassing Ideate since there's no new concept to ideate)
   - `plugin-lifecycle-downstream`'s Phase 8 Consolidated Fix (route the enhancement through downstream's fix pipeline instead)
   - a clean stop, with rationale, if neither applies
3. It **points the user there** so they can continue in the right place instead of being left in this pipeline.

## Why this design

`plugin-lifecycle-upstream` is documented as creation-only (see SKILL.md's "When NOT to Use": *"Just want the Create/Enhance/Repair/.../Reject-Defer classification itself... use `plugin-conception` directly"*). Phase 1 dispatches to `plugin-conception` purely as a classifier/qualifier — it never runs `plugin-ideation`'s interactive interview itself. A Create result feeds the light brief into Phase 2 as if it were a rough idea; any non-Create result (including Enhance) means there's no new component to design, so the seven-phase build pipeline (Ideate → Plan → Design → Build → Self-Review → Test) has nothing to do and exits at the first gate rather than being forced through motions that don't apply.

## Testing & Validation coverage

This exact scenario is explicitly covered by the skill's own test plan (SKILL.md, Testing & Validation item 1b): *"Conceive, non-Create classification — Phase 1 classifies the idea as Enhance/Repair/Consolidate/Reposition/Retain/Reject-Defer; confirm the pipeline stops at Gate 1, states `plugin-conception`'s own hand-off target plainly, and never proceeds into Phase 2."* It's also a standing quality gate: *"A non-Create classification from Phase 1 always stops the pipeline at Gate 1 — never forced through Phase 2 onward."*

## Summary

For the described situation (Conception Brief produced, classification = Enhance), Gate 1:
1. Prints the `📄 Conception Brief written:` artifact-link line.
2. Presents the classification (Enhance) and `plugin-conception`'s rationale.
3. Stops the pipeline immediately — no Phase 2 dispatch, no `AskUserQuestion` proceed/revise/stop prompt.
4. States plainly which hand-off target `plugin-conception` recommends (`plugin-planning` directly, `plugin-lifecycle-downstream`'s Phase 8 Consolidated Fix, or a clean stop with rationale) and directs the user there.
