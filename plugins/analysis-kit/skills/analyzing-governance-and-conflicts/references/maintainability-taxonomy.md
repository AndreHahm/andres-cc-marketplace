# Maintainability Taxonomy

The eight dimensions Phase 5's maintainability/change-impact analysis inventories against.

1. **Duplication** -- the same fact, procedure, or value is stated in more than one place, so a future
   change to one copy risks leaving the others stale. This plugin's own `references/date-range-scope-
   convention.md` and `references/report-discovery-convention.md` are worked examples of the pattern
   itself: each maintains its own "Sites That Restate This"/"Sites That Restate These Facts" section
   precisely because the fact it defines is duplicated inline across sibling skills -- read either file's
   own site list directly for the current count rather than restating a number here, which would go stale
   the next time a skill is added or removed (see `change-impact-checklist.md`'s Consolidation section
   for the full worked example).
2. **Coupling** -- a change in one component requires a corresponding change in another for correctness,
   without that dependency being explicitly documented. Distinct from duplication: coupling is a
   behavioral dependency, not a copied fact.
3. **Canonical-fact drift** -- a value that has one designated source of truth has actually diverged
   between the source and one or more of its restatements (a stricter, already-manifested case of
   duplication -- the copies no longer agree).
4. **Stale mirrors** -- a file that's supposed to be an exact or near-exact copy of another (e.g. a
   `.claude/`-mirrored plugin file) has fallen out of sync with its canonical source.
5. **Documentation drift** -- human-facing documentation (README, a component count, a capability list)
   no longer accurately describes the actual current state of the code/components it documents.
6. **Ownership** -- it's unclear, or actually contested, which component/team/file is responsible for
   maintaining a piece of shared logic or a shared fact going forward.
7. **Blast radius** -- how many sites, components, or downstream consumers a given change or drift
   actually touches -- the scope of "how much has to be fixed together" for one root cause.
8. **Verification surface** -- whether the change actually has a test/check that would catch a future
   regression in this same spot, independent of whether one exists today.

## Local vs. Cross-Component Scope

This phase is not a general code-quality or style review -- a locally ugly but self-contained function
with no external consumers is out of scope. The dimensions above all describe risk that crosses a
boundary: between two files, two components, or between documentation and the code it describes. If a
session's change stays entirely local with no duplicated fact, no coupling, and no consumer to keep in
sync, there is legitimately nothing to report here.
