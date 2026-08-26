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

Invoke `plugin-conception` (via `Skill`) **once per approved suggestion from Step 2**, never once for the whole batch — `plugin-conception` classifies and briefs exactly one candidate per invocation; a multi-candidate pick from Step 2 is a sequence of separate invocations, not a single call with a list. This runs immediately after the pick and before Step 4's hand-off, never before the pick (classifying every unselected candidate suggestion would be wasted work). Pass each approved suggestion as Entry Route B evidence (source: `analyzing-sessions`).

For each suggestion, `plugin-conception` classifies it and, for a narrow, already-known Repair with an already-accepted finding, takes its own bypass path (Step 2's "Bypass for narrow repairs") straight through without producing the full brief — this is the common case for a small, well-understood retro fix. For an Enhance/Consolidate/Reposition suggestion, or a Repair that isn't narrowly scoped, it produces the full Conception Brief (baseline contract, implementation plan, risks). Its own Step 7 brief-content approval (approve/revise/merge/defer/reject) still runs per candidate — but its Step 7 **hand-off invocation** does not: this workflow, not `plugin-conception`, owns deciding where each classified candidate goes next (Step 4 below), so do not let `plugin-conception` separately ask or invoke a hand-off target from inside this workflow.

Present each written brief's artifact link as it's produced:

```
📄 Conception Brief written: `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`
```

**Exit criteria:** Every approved suggestion has either a recorded bypass (Repair, narrow, already-known fix) or a written Conception Brief, each carrying its own classification.

## Step 4: Route by Classification, Then Hand Off to Fix

Step 3 leaves every candidate in one of `plugin-conception`'s seven classifications. Route each candidate accordingly — do not send the whole batch to Fix unconditionally:

- **Repair (bypassed or full-brief), or Enhance/Consolidate/Reposition with no new components implied** → include in this step's Fix bundle, below.
- **Enhance/Consolidate/Reposition where the brief's classification implies a new or restructured component** → this workflow has no Design/Build capability to build one — matching `plugin-conception`'s own Step 7 hand-off table, which routes exactly this case to `plugin-planning`, never to `plugin-lifecycle-upstream` (that pipeline's own Gate 1 stops on any non-Create classification and never resumes into it). Do not force it into the Fix bundle. Present the written Conception Brief to the user and state plainly that this specific candidate needs `plugin-planning` instead, using the brief directly as `plugin-planning`'s own Step 1 input (it already accepts a Conception Brief path) — the brief this step already wrote is reusable, not wasted work. Exclude it from the Fix bundle below.
- **Create** → a retro suggestion can genuinely reclassify as Create (see `plugin-conception`'s own Step 2: "an apparent Enhance may turn out to be a genuine Create once the shallow check shows nothing adjacent actually exists"). This workflow has no Ideate/Design/Build capability either — matching `plugin-conception`'s own Step 7 hand-off table, which routes a Create classification to `plugin-ideation`. Present the written Conception Brief to the user and state plainly that this candidate needs `plugin-ideation` (and, from there, the rest of `plugin-lifecycle-upstream`) instead, using the brief directly as `plugin-ideation`'s own input. Exclude it from the Fix bundle below — never force a Create candidate into Fix.
- **Retain / Reject / Defer** → not actionable work. Exclude from the Fix bundle; report the classification and `plugin-conception`'s own rationale as the reason nothing was applied for that candidate.

For every candidate landing in the Fix bundle, reformat it (via its Conception Brief, where Step 3 produced one, or directly for a bypassed narrow repair) into the shared Finding schema (`plugin-rulebook/references/evidence-schema.md`) instead of `plugin-grader`'s `prioritized_next_steps` shape — each entry: `id` (`analyzing-sessions:<local-id>`, reusing the suggestion's own P1/P2/P3 tag), `source: analyzing-sessions`, `scope` (the component/file the suggestion targets), `severity` (map P1→major, P2/P3→minor — this list didn't come from a real audit, so treat severity as advisory, not a rubric verdict), `status: open`, `evidence_before` (the suggestion's own WHAT/WHY, or the Conception Brief's Evidence section where one exists), `fix` (the suggestion's own HOW, or the Conception Brief's Proposed delta).

If the Fix bundle is empty (every candidate was excluded above), state this plainly and skip the `plugin-lifecycle-downstream` invocation below — there is nothing to hand off.

Otherwise, invoke `plugin-lifecycle-downstream` (via `Skill`) targeting the same plugin, using its documented **external Phase 8 (Consolidated Fix) entry** (see `plugin-lifecycle-downstream/workflows/run-qa-pipeline.md` Phase 8's Entry condition) with this findings bundle plus a minimal scope manifest (`baseline_commit` from `git log -1`, `scope_mode: named`, `included` listing exactly the components the bundled candidates target) — skip Phases 1-7 (they would just re-derive evidence this workflow doesn't need; the findings already came from the retro, not from a fresh audit). Declare in the input contract that this workflow owns Phase 9 (Documentation) — Step 6 below runs it separately — so downstream's hand-off skips its own Documentation phase and continues only through Phase 10 (Final Verification) and Phase 11 (Grading, still its own internally-gated ask) into Phase 12 (Handoff). This is the reuse point: do not reimplement apply → re-verify → commit here, that is exactly what downstream's Phase 8 already does, including its own commit confirmation and, per its own Mutation-and-Confirmation preflight, the Open-PR and Branch-scope checks too. Do not run a separate copy of either check here.

**Exit criteria:** Every candidate has an explicit disposition (bundled-and-applied, redirected to `plugin-planning`, redirected to `plugin-ideation`, or excluded as Retain/Reject/Defer) — never silently dropped. For any bundled candidates, downstream's Phase 8 reports all approved fixes applied and independently re-verified (fully or partially — partial application is fine, per its own exit criteria), with its own commit(s) already made.

## Step 5: Test and Self-Review

Downstream's Phase 8 hand-off in Step 4 above already re-runs each originating check against live files, plus relevant regression checks, as part of its own verification — the new pipeline folds what the old pipeline ran as two separate automatic phases (Test, Self-Review) into Phase 8's own re-verification instead of numbering them separately. This step exists to give that coverage its own place in this workflow's numbering, not to re-invoke or duplicate it: do not run a second copy of any per-type smoke check or type-matched reviewer dispatch from here.

**Exit criteria:** Downstream's Phase 8 verification result (per-fix applied/deferred/failed, plus regression-check outcome), already surfaced as part of Step 4's hand-off — or explicitly stated as skipped, if Step 4 applied nothing.

## Step 6: Document

**Entry:** if Step 4's Fix bundle was non-empty, run this step normally — see `SKILL.md`'s "The Document Step" section (identical procedure for all 4 workflows), after Step 4's fix commit(s) and Step 5's results are surfaced. This is the ownership Step 4 declared to downstream — downstream's own Phase 9 was skipped precisely so this step is the one place Documentation actually runs. **If Step 4's Fix bundle was empty** (every candidate was excluded or redirected), skip this step — there is nothing this run changed for `plugin-documentation` to reconcile against, and the branch-scope-check waiver in `SKILL.md`'s Pre-Flight Checks section only holds when Step 4 actually hands off to downstream.

## Step 7: Handover (Optional)

If Step 6 applied any doc change, ask via `AskUserQuestion`: "Run a fresh downstream QA pass to confirm the doc changes didn't break anything?" — options "Yes — run downstream QA" / "No — stop here". If yes, invoke `plugin-lifecycle-downstream` (via `Skill`) for a full Validate+Audit pass over the plugin's current state — broader than Step 4's own Phase 10 (Final Verification), which only re-checked evidence Phase 8 itself invalidated, not evidence Step 6's later doc edits might affect. Never invoke without asking first.

If Step 6 made no changes, skip this step — there is nothing new to QA.
