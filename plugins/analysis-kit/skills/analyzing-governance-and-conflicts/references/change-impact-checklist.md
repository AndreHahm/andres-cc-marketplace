# Change-Impact Checklist

The affected-site inventory format Phase 5 uses for every duplication/drift finding, and the
consolidation discipline that keeps one root cause from becoming N separate findings.

## Affected-Site Inventory Format

Every duplication/drift finding states:

- **Canonical source** -- the one place (file + section, or a stated "no canonical source exists yet"
  when the drift is that no single source of truth was ever designated) that should be treated as
  authoritative.
- **All known consumers** -- every other site that restates, mirrors, or depends on the canonical
  source's value, found by an actual search (`Grep`/`Glob` across the repo for the fact's own distinctive
  text or the mirrored file's path), not just the one site the session happened to touch.
- **Current state per consumer** -- for each consumer, whether it currently matches the canonical source
  or has already drifted.

## Consolidation: One Root Cause, One Finding

When a session's change touches one restatement of a fact that's duplicated in N places, the correct
finding is **one** entry naming the canonical source and listing all N consumers with their current
state -- not N separate findings, one per site. A worked example from this plugin's own history: this
plugin's own scope-resolution and discovery-glob conventions are each restated inline across a growing
set of sibling skills -- read `date-range-scope-convention.md`'s or `report-discovery-convention.md`'s
own "Sites That Restate This"/"Sites That Restate These Facts" section directly for the current count
rather than citing a number here, since the count has already changed more than once as new skills were
added and would go stale again. The pattern is one root cause (the convention lacks single-source
enforcement), reported once, with every restating skill named as a consumer -- exactly the shape
`report-discovery-convention.md`'s own "Sites That Restate
These Facts" section already uses to track this same class of fact in this plugin.

**Verify the consolidation, don't assume it.** Before finalizing a Phase 5 finding, re-read it and confirm
it isn't accidentally a second, near-duplicate finding for a root cause already reported elsewhere in the
same report -- two findings that turn out to share one canonical source should be merged into one.

## Ownership and Verification Surface

For a finding that also touches the Ownership or Verification Surface dimensions, state explicitly: who
(or what convention/rule) is supposed to keep the consumers in sync going forward, and whether any
existing check (a smoke test, a CI step, a rule) would actually catch a future drift at this exact spot.
"No such check exists" is itself a valid, reportable finding under Verification Surface -- don't leave it
implicit.
