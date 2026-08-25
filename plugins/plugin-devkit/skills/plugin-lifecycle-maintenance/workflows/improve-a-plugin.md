# Improve a Plugin: Retro-Driven Improvement

The complete Retro → Human Decision → Conceive → Fix → Test → Self-Review → Document → Commit → optional Handover procedure.

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

## Step 3: Conceive

Invoke `plugin-conception` (via `Skill`) against the human-approved suggestions from Step 2 — this runs immediately after the pick and before Step 4's hand-off, never before the pick (classifying every unselected candidate suggestion would be wasted work). Pass the approved suggestions as Entry Route B evidence (source: `analyzing-sessions`).

`plugin-conception` classifies each approved suggestion and, for a narrow, already-known Repair with an already-accepted finding, takes its own bypass path (Step 2's "Bypass for narrow repairs") straight through to Step 4 below without producing the full brief — this is the common case for a small, well-understood retro fix. For an Enhance/Consolidate/Reposition suggestion, or a Repair that isn't narrowly scoped, it produces the full Conception Brief (baseline contract, implementation plan, risks) before Step 4 runs.

**Exit criteria:** Each approved suggestion has either a recorded bypass (Repair, narrow, already-known fix) or a written Conception Brief at `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`.

## Step 4: Hand Off to Fix

Reformat the approved suggestions (via their Conception Brief, where Step 3 produced one, or directly for a bypassed narrow repair) into the shared Finding schema (`plugin-rulebook/references/evidence-schema.md`) instead of `plugin-grader`'s `prioritized_next_steps` shape — each entry: `id` (`analyzing-sessions:<local-id>`, reusing the suggestion's own P1/P2/P3 tag), `source: analyzing-sessions`, `scope` (the component/file the suggestion targets), `severity` (map P1→major, P2/P3→minor — this list didn't come from a real audit, so treat severity as advisory, not a rubric verdict), `status: open`, `evidence_before` (the suggestion's own WHAT/WHY, or the Conception Brief's Evidence section where one exists), `fix` (the suggestion's own HOW, or the Conception Brief's Proposed delta).

Invoke `plugin-lifecycle-downstream` (via `Skill`) targeting the same plugin, using its documented **external Phase 8 (Consolidated Fix) entry** (see `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md` Phase 8's Entry condition) with this findings bundle plus a minimal scope manifest (`baseline_commit` from `git log -1`, `scope_mode: named`, `included` listing exactly the components the approved suggestions target) — skip Phases 1-7 (they would just re-derive evidence this workflow doesn't need; the findings already came from the retro, not from a fresh audit). Declare in the input contract that this workflow owns Phase 9 (Documentation) — Step 6 below runs it separately — so downstream's hand-off skips its own Documentation phase and continues only through Phase 10 (Final Verification) and Phase 11 (Grading, still its own internally-gated ask) into Phase 12 (Handoff). This is the reuse point: do not reimplement apply → re-verify → commit here, that is exactly what downstream's Phase 8 already does, including its own commit confirmation and, per its own Mutation-and-Confirmation preflight, the Open-PR and Branch-scope checks too. Do not run a separate copy of either check here.

**Exit criteria:** Downstream's Phase 8 reports all approved fixes applied and independently re-verified (fully or partially — partial application is fine, per its own exit criteria), with its own commit(s) already made.

## Step 5: Test and Self-Review

Downstream's Phase 8 hand-off in Step 4 above already re-runs each originating check against live files, plus relevant regression checks, as part of its own verification — the new pipeline folds what the old pipeline ran as two separate automatic phases (Test, Self-Review) into Phase 8's own re-verification instead of numbering them separately. This step exists to give that coverage its own place in this workflow's numbering, not to re-invoke or duplicate it: do not run a second copy of any per-type smoke check or type-matched reviewer dispatch from here.

**Exit criteria:** Downstream's Phase 8 verification result (per-fix applied/deferred/failed, plus regression-check outcome), already surfaced as part of Step 4's hand-off — or explicitly stated as skipped, if Step 4 applied nothing.

## Step 6: Document

See `SKILL.md`'s "The Document Step" section — identical procedure for all 4 workflows. Run it now, after Step 4's fix commit(s) and Step 5's results are surfaced. This is the ownership Step 4 declared to downstream — downstream's own Phase 9 was skipped precisely so this step is the one place Documentation actually runs.

## Step 7: Handover (Optional)

If Step 6 applied any doc change, ask via `AskUserQuestion`: "Run a fresh downstream QA pass to confirm the doc changes didn't break anything?" — options "Yes — run downstream QA" / "No — stop here". If yes, invoke `plugin-lifecycle-downstream` (via `Skill`) for a full Validate+Audit pass over the plugin's current state — broader than Step 4's own Phase 10 (Final Verification), which only re-checked evidence Phase 8 itself invalidated, not evidence Step 6's later doc edits might affect. Never invoke without asking first.

If Step 6 made no changes, skip this step — there is nothing new to QA.
