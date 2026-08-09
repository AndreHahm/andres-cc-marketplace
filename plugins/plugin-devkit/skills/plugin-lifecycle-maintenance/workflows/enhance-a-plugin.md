# Enhance a Plugin: Comparison-Driven Enhancement

The complete Comparison → Human Decision → Fix → Test → Self-Review → Document → Commit → optional Handover procedure. Same shape as `improve-a-plugin.md`, with `plugin-comparison` as the finding source instead of `analyzing-sessions`.

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

## Step 3: Hand Off to Fix

Reformat the approved deltas into a list matching `plugin-grader`'s real `prioritized_next_steps` schema — same reshaping as `improve-a-plugin.md` Step 3 (`rank`, `action`, `dimension` if one applies, `points_gain_estimate` as a rough estimate, `lifts_gate` always `null`).

Invoke `plugin-lifecycle-downstream` (via `Skill`) targeting the plugin being enhanced, using its documented external Phase 3 entry (see `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md` Phase 3's Entry condition) with this list — skip Phases 1-2, same reasoning as `improve-a-plugin.md` Step 3. Do not reimplement apply → re-validate → commit here — nor its Open-PR/Branch-scope pre-flight checks, which downstream's own Phase 3 already runs. Downstream's Phase 3 also continues automatically into its own Phase 4 (Test) and Phase 5 (Self-Review) whenever it applies at least one change, same as `improve-a-plugin.md` Step 3 — this single hand-off already covers Steps 4-5 below without a second invocation.

**Exit criteria:** Downstream's Phase 3 reports all approved deltas applied and re-validated (fully or partially), with its own commit(s) already made.

## Step 4: Test

Same reuse as `improve-a-plugin.md` Step 4 — downstream's own Phase 4 (Test) already ran as part of the Step 3 hand-off, once Phase 3 applied at least one change. This step exists to give that coverage its own place in this workflow's numbering; do not re-invoke or duplicate it.

**Exit criteria:** Downstream's Phase 4 result, already surfaced as part of Step 3's hand-off — or explicitly stated as skipped, if Step 3 applied nothing.

## Step 5: Self-Review

Same reuse as `improve-a-plugin.md` Step 5 — downstream's own Phase 5 (Self-Review) already ran as part of the Step 3 hand-off, scoped to only the component(s) Step 3's approved deltas actually touched. This workflow never re-dispatches the type-matched `*-reviewer` agent(s) itself.

**Exit criteria:** Downstream's Phase 5 findings, already surfaced as part of Step 3's hand-off — or explicitly stated as skipped, if Step 3 applied nothing.

## Step 6: Document

See `SKILL.md`'s "The Document Step" section — identical procedure for all 4 workflows. Run it now, after Step 3's fix commit(s) and Steps 4-5's results are surfaced.

## Step 7: Handover (Optional)

Same as `improve-a-plugin.md` Step 7 — ask before a final downstream QA pass, only if Step 6 changed anything.
