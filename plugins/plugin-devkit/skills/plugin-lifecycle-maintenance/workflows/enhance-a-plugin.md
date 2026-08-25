# Enhance a Plugin: Comparison-Driven Enhancement

The complete Comparison → Human Decision → Conceive → Fix → Test → Self-Review → Document → Commit → optional Handover procedure. Same shape as `improve-a-plugin.md`, with `plugin-comparison` as the finding source instead of `analyzing-sessions`.

## Step 1: Comparison

**Entry:** `$ARGUMENTS` names both targets — the plugin being enhanced, and the comparison target (another internal component, an installed plugin, a local path, or a GitHub reference).

**Actions:**
1. Invoke `plugin-comparison` (via `Skill`) with both targets from `$ARGUMENTS`. If either is missing or ambiguous, let `plugin-comparison`'s own Steps 1-2 target-resolution logic handle it; Step 3 is a separate, later step (the detail-level question only, no target-resolution role) — do not pre-resolve targets here.
2. Wait for its written report at `.claude/output/plugin-comparison/comparison-<timestamp>.md`.

**Exit criteria:** The report exists with a non-empty "Unique to B", "Notable Differences", or "Recommendation" section. If all three are empty (the two targets are equivalent), state this plainly and stop — there is nothing for this workflow to act on.

Present the artifact link before anything else:

```
📄 Comparison Report written: `.claude/output/plugin-comparison/comparison-<timestamp>.md`
```

## Step 2: Human Decides

Present the report's "Unique to B", "Notable Differences", and "Recommendation" sections. Ask via `AskUserQuestion` (multiSelect) which deltas to act on — "none of these, stop here" is a valid answer.

For anything worth a full WHAT/WHY/HOW plan before deciding further, invoke `enhancement-suggestor` (via `Agent`) against the written comparison report — this mirrors `plugin-comparison`'s own Step 7 offer; do not skip past it if the user wants it.

**Exit criteria:** A final, human-approved list of deltas to act on (possibly empty — if empty, stop here).

## Step 3: Conceive

Invoke `plugin-conception` (via `Skill`) **once per approved delta from Step 2**, never once for the whole batch — same placement and one-candidate-per-invocation contract as `improve-a-plugin.md` Step 3 (immediately after the pick, before Step 4's routing), with each approved delta passed as Entry Route B evidence (source: `plugin-comparison`) instead of session-analysis suggestions.

Same bypass and full-brief behavior as `improve-a-plugin.md` Step 3: a narrow, already-known Repair with an already-accepted finding takes the bypass path; every other classification gets the full Conception Brief first. `plugin-conception`'s own Step 7 brief-content approval still runs per candidate, but its hand-off invocation does not — this workflow owns routing (Step 4 below), same as `improve-a-plugin.md` Step 3.

Present each written brief's artifact link as it's produced:

```
📄 Conception Brief written: `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`
```

**Exit criteria:** Every approved delta has either a recorded bypass or a written Conception Brief, each carrying its own classification.

## Step 4: Route by Classification, Then Hand Off to Fix

Same routing rule as `improve-a-plugin.md` Step 4 — do not send the whole batch to Fix unconditionally:

- **Repair (bypassed or full-brief), or Enhance/Consolidate/Reposition with no new components implied** → include in this step's Fix bundle, below.
- **Enhance/Consolidate/Reposition implying a new or restructured component** → this workflow has no Design/Build capability, matching `plugin-conception`'s own Step 7 table, which routes this case to `plugin-planning`. Present the written Conception Brief and state plainly that this delta needs `plugin-planning` instead, using the brief directly as its Step 1 input. Exclude from the Fix bundle.
- **Retain / Reject / Defer** → not actionable work. Exclude from the Fix bundle; report the classification and rationale.

For every candidate landing in the Fix bundle, reformat it (via its Conception Brief, where Step 3 produced one, or directly for a bypassed narrow repair) into the shared Finding schema (`plugin-rulebook/references/evidence-schema.md`) — same reshaping as `improve-a-plugin.md` Step 4, with `source: plugin-comparison` and `id: plugin-comparison:<local-id>`.

If the Fix bundle is empty, state this plainly and skip the `plugin-lifecycle-downstream` invocation below.

Otherwise, invoke `plugin-lifecycle-downstream` (via `Skill`) targeting the plugin being enhanced, using its documented external Phase 8 (Consolidated Fix) entry (see `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md` Phase 8's Entry condition) with this findings bundle plus a minimal scope manifest, same reasoning as `improve-a-plugin.md` Step 4 — skip Phases 1-7, and declare in the input contract that this workflow owns Phase 9 (Documentation), same as `improve-a-plugin.md` Step 4. Do not reimplement apply → re-verify → commit here — nor its Open-PR/Branch-scope pre-flight checks, which downstream's own Phase 8 already runs via its Mutation-and-Confirmation preflight.

**Exit criteria:** Every candidate has an explicit disposition (bundled-and-applied, redirected to `plugin-planning`, or excluded as Retain/Reject/Defer). For any bundled candidates, downstream's Phase 8 reports all approved deltas applied and independently re-verified (fully or partially), with its own commit(s) already made.

## Step 5: Test and Self-Review

Same reuse as `improve-a-plugin.md` Step 5 — downstream's Phase 8 hand-off in Step 4 already re-runs each originating check plus regression checks as part of its own verification, folding what the old pipeline ran as two separate automatic phases into one. This step exists to give that coverage its own place in this workflow's numbering; do not re-invoke or duplicate it.

**Exit criteria:** Downstream's Phase 8 verification result, already surfaced as part of Step 4's hand-off — or explicitly stated as skipped, if Step 4 applied nothing.

## Step 6: Document

See `SKILL.md`'s "The Document Step" section — identical procedure for all 4 workflows. Run it now, after Step 4's fix commit(s) and Step 5's results are surfaced. This is the ownership Step 4 declared to downstream — downstream's own Phase 9 was skipped precisely so this step is the one place Documentation actually runs.

## Step 7: Handover (Optional)

Same as `improve-a-plugin.md` Step 7 — ask before a fresh downstream QA pass, only if Step 6 changed anything.
