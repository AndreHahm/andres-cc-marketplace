# Which Step 1 branch applies, and what plugin-planning should do differently

## Answer: Branch 2 — "Conception Brief found under `.claude/output/plugin-conception/`"

The input path is:

`C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-conception\.claude\output\plugin-conception\plugin-foo-testing-validation-section-2026-08-25T16-34-49Z.md`

That's under `.claude/output/plugin-conception/`, and the document itself is titled "Conception Brief" with `Concept type: Enhance`. Step 1's own branch text describes exactly this case:

> **Conception Brief found** under `.claude/output/plugin-conception/` instead (an Enhance/Consolidate/Reposition-classification brief reached without ever touching `plugin-ideation`) → `Read` it in full; note in the plan that this concept came directly from `plugin-conception`, not `plugin-ideation` — its own Existing-Component Baseline section covers the compatibility contract `plugin-ideation` would otherwise have produced. Its Marketplace Integration section's overlap check stays shallow (repository-metadata depth only, per `plugin-conception`'s own Step 3) — **not** the exhaustive per-component/name-collision search `plugin-ideation` runs; note in the plan that this narrower overlap check is what's actually behind this concept, not a full ideation-depth search.

Branch 1 (Concept Card under `.claude/output/plugin-ideation/`) doesn't apply — this file isn't a Concept Card and isn't in that directory. Branch 3 (neither found, treat `$ARGUMENTS` as a raw problem statement) doesn't apply either — a Conception Brief *was* found.

## What plugin-planning does differently than for a plain Concept Card

1. **Read the Brief, not a Card, and say so in the plan.** The plan must explicitly note the concept came directly from `plugin-conception`, bypassing `plugin-ideation` — a reader of the plan needs to know the provenance differs from the normal Card path.

2. **Inherit the compatibility contract instead of expecting one from ideation.** A Concept Card doesn't carry an "Existing-Component Baseline" — that's a Conception Brief structure. For this brief, Step 1 should treat its `## Existing-Component Baseline` section (Behavior to preserve / Verified deficiency / Proposed delta / Affected surfaces) as *already* supplying the compatibility contract plugin-ideation would otherwise have had to establish. Concretely here: "all of plugin-foo's existing SKILL.md content... stays unchanged — this is a purely additive documentation change" is the constraint plugin-planning carries forward, not something it re-derives.

3. **Discount the overlap check's depth, don't inherit it at face value.** The brief's own `Marketplace Integration → Overlap check` table says "None found elsewhere in the marketplace that duplicates this specific gap," but per `plugin-conception`'s Step 3 that check is repository-metadata depth only — not the exhaustive per-component/name-collision search `plugin-ideation` runs. The plan must flag this explicitly (e.g. "overlap check inherited from plugin-conception is shallow; not equivalent to an ideation-depth search") rather than silently treating "None found" as ideation-strength evidence.

4. **A Concept Card is presumptively "accepted" and implies new/restructured components; this Brief is neither.** Two things worth surfacing rather than mechanically proceeding through Steps 2–5:

   - **Status/Decision state:** the brief's Metadata shows `Status: Draft` and `Decision: Pending`, with two explicitly open decisions (A1/A2 — the literal `plugin-foo` target is unresolved) still gating Planning: *"Whether to proceed straight to Fix, or re-run completeness-reviewer first... Required by gate: Conception (this gate)."* plugin-planning's own "When to Use" language assumes "an *accepted* Conception Brief" — this one hasn't cleared its own Conception gate yet. Per `disclose-before-overriding-decisions.md`, that's a checkpoint state to surface to the user, not to silently treat as accepted.

   - **No new/restructured components are implied at all.** The brief's own `Provisional naming` section says: *"Not applicable — Enhance modifying an existing component's existing file; no new component name is implied."* And its own `Handoff` table already names the downstream route as **Fix — `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix)**, not Planning, because plugin-conception's Step 7 routes a "no-new-component Enhance outcome" straight to Fix. Mechanically running plugin-planning's Step 2 (Decide Component Types and Counts) over this concept would yield zero planned components — there's no new skill/agent/command/hook, just one additive section inside an existing skill's SKILL.md — and Step 3's depth-tier allocation has nothing to attach to (depth tiers are for *planned* skills, not a documentation delta on an existing one).

   Put together: for a plain Concept Card, Step 1 simply reads and moves on to Step 2 assuming components are implied. For *this* Brief, the substantively correct behavior is to read it (branch 2 fires as designed), but then recognize — and disclose to the user rather than paper over — that (a) it's still Draft/Pending on its own unresolved A1/A2, and (b) its content and its own Handoff section indicate it isn't actually a Planning-shaped concept at all; it's a single-file content addition that plugin-conception itself already routed to Fix. Producing a padded component inventory here (to make Steps 2–4 look non-trivial) would misrepresent the concept; the right output is to surface the mismatch/gating state via `AskUserQuestion` rather than silently forcing the brief through the full component-inventory machinery it doesn't need.

## Summary

- **Branch:** Step 1's second branch (Conception Brief under `.claude/output/plugin-conception/`) applies, based on the file's location and its "Conception Brief" / `Concept type: Enhance` framing.
- **Differences from Concept Card handling:** (1) plan must record the concept came from `plugin-conception`, not `plugin-ideation`; (2) the Brief's `Existing-Component Baseline` section stands in for the compatibility contract a Card would lack; (3) the Brief's overlap check is noted as shallow/repository-metadata-depth, not ideation-depth, and the plan must say so rather than reusing it as if it were a full search; (4) unlike a routine accepted Card, this specific Brief is still Draft/Pending on unresolved A1/A2 and its own content shows no new/restructured components are implied — its own Handoff already points to Fix (`plugin-lifecycle-downstream` Phase 8), not Planning — so the correct move is to disclose this mismatch to the user rather than mechanically generating a component inventory for a concept that doesn't call for one.
