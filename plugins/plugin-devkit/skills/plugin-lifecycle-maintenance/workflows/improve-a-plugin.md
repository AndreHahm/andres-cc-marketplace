# Improve a Plugin: Retro-Driven Improvement

The complete Retro → Human Decision → Fix → Test → Self-Review → Document → Commit → optional Handover procedure.

## Step 1: Retro

**Entry:** `$ARGUMENTS` names a plugin/session-range, or the current conversation is the implicit scope.

**Actions:**
1. Invoke `analyzing-sessions` (via `Skill`) scoped to the session range or target given in `$ARGUMENTS` (default: "this conversation" if unspecified).
2. Wait for its grouped report — SWOT per component, suggestions in P1→P3 order, Top 5 Actions.

**Exit criteria:** The report exists with at least one suggestion (P1, P2, or P3). If it has none, state this plainly and stop — there is nothing for this workflow to act on.

Present the artifact link before anything else:

```
📄 Session Analysis Report written: `.claude/output/analyzing-sessions/<scope-slug>-<timestamp>.md`
```

## Step 2: Human Decides

Present the report's Top 5 Actions and the full P1→P3 suggestion list. Ask via `AskUserQuestion` (multiSelect) which suggestions to act on now — "none of these, stop here" is a valid answer.

For any chosen suggestion the user wants expanded into a full WHAT/WHY/HOW plan before deciding further, invoke `enhancement-suggestor` (via `Agent`) against it — this mirrors `analyzing-sessions`' own "Suggested next step" offer; do not skip past it if the user wants it.

**Exit criteria:** A final, human-approved list of suggestions to apply (possibly empty — if empty, stop here).

## Step 3: Hand Off to Fix

Reformat the approved suggestions into a list matching `plugin-grader`'s real `prioritized_next_steps` schema — each entry: `rank`, `action`, `dimension` (if one clearly applies, else omit), `points_gain_estimate` (a rough estimate is fine — this list didn't come from a real audit, so treat this field as advisory), `lifts_gate` (always `null` — nothing here came from a `plugin-grader` gate).

Invoke `plugin-lifecycle-downstream` (via `Skill`) targeting the same plugin, using its documented **external Phase 3 entry** (see `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md` Phase 3's Entry condition) with this list — skip Phases 1-2 (they would just re-derive a `plugin-grader` score this workflow doesn't need; the findings already came from the retro, not from a fresh audit). This is the reuse point: do not reimplement apply → re-validate → commit here, that is exactly what downstream's Fix phase already does, including its own commit confirmation — and, as of downstream's own "Pre-Flight Checks (Before Fix Only)", its Open-PR and Branch-scope checks too. Do not run a separate copy of either check here. Downstream's Phase 3 also continues automatically into its own Phase 4 (Test) and Phase 5 (Self-Review) whenever it applies at least one change — its own Entry conditions for those two phases don't distinguish a normal Phase 3 entry from this workflow's external one — so this single hand-off already covers Steps 4-5 below without a second invocation.

**Exit criteria:** Downstream's Phase 3 reports all approved fixes applied and re-validated (fully or partially — partial application is fine, per its own exit criteria), with its own commit(s) already made.

## Step 4: Test

Downstream's Phase 3 hand-off in Step 3 above already ran its own Phase 4 (Test) automatically once Phase 3 applied at least one change — per `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md`'s Phase 4 Entry condition. This step exists to give that coverage its own place in this workflow's numbering, not to re-invoke or duplicate it: do not run a second copy of Phase 4's per-type smoke checks from here, and do not reimplement its `smoke-tester`-pending-fallback handling.

**Exit criteria:** Downstream's Phase 4 result (per-touched-component pass/fail/skipped), already surfaced as part of Step 3's hand-off — or explicitly stated as skipped, if Step 3 applied nothing.

## Step 5: Self-Review

Same reuse as Step 4 — downstream's own Phase 5 (Self-Review) ran automatically as part of the Step 3 hand-off, scoped to only the component(s) Step 3's approved suggestions actually touched. See `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md`'s Phase 5 for the procedure; this workflow never re-dispatches the type-matched `*-reviewer` agent(s) itself.

**Exit criteria:** Downstream's Phase 5 findings, already surfaced as part of Step 3's hand-off — or explicitly stated as skipped, if Step 3 applied nothing.

## Step 6: Document

See `SKILL.md`'s "The Document Step" section — identical procedure for all 4 workflows. Run it now, after Step 3's fix commit(s) and Steps 4-5's results are surfaced.

## Step 7: Handover (Optional)

If Step 6 applied any doc change, ask via `AskUserQuestion`: "Run a final downstream QA pass to confirm the doc changes didn't break anything?" — options "Yes — run downstream QA" / "No — stop here". If yes, invoke `plugin-lifecycle-downstream` (via `Skill`) for a fresh Validate+Audit pass (Phases 1-2 this time, a full check). Never invoke without asking first.

If Step 6 made no changes, skip this step — there is nothing new to QA.
