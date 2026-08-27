# Resweep Closed Scope Lists on New Components

## When this applies

A new `plugin-devkit` skill or agent is added whose function includes inspecting, enumerating, or
reconciling a plugin's or the marketplace's own real on-disk component/manifest structure — the same
criterion [[test-against-example-plugin]] uses to decide its own in-scope list.

## Rule

The change that adds such a component must, in the same commit/session, re-examine every existing closed
enumerated component-scope list that uses this same criterion — today: just
[[test-against-example-plugin]]'s in-scope/excluded tables, but this rule is written generically since a
future rule could add another such list — and either add the new component with stated reasoning, or
explicitly exclude it with stated reasoning. A closed list's silence must never stand in for a decision.

## Relationship to R20 (Duplicate Fact Sweep)

Deliberately not folded into `plugin-rulebook`'s R20. R20 catches a canonical *value* (an enum, a
threshold) drifting once changed; this catches a *new member* that should have been added to an
already-existing enumerated scope but never was, because nothing re-triggers the check when the new
candidate ships later rather than at the moment the list itself was written. Distinct failure mode, so a
distinct rule rather than an R20 config addition.

## Trigger

"Before finalizing" cadence, same as `.claude/rules/plugin-rulebook-enforcement.md` and
[[test-against-example-plugin]] itself — after the last modification in a creation sequence that adds a
new structure-reading component, not per-intermediate-edit.

## Enforcement

Policy gate, no backing hook — same disclosed-limitation model [[test-against-example-plugin]] already
uses for itself. Whether a new component actually "meets the same criterion" as an existing scope list is
a semantic judgment, not something a mechanical hook can verify; compliance depends on author/reviewer
attention at "before finalizing" time.

## Why

`marketplace-inventory` and `plugin-inventory` shipped 2026-08-25, one day after
[[test-against-example-plugin]]'s original component enumeration (2026-08-24), and were absent from both
its in-scope and excluded lists until a 2026-08-26 review caught it. Nothing had structurally prompted a
re-check in between — the list was simply never revisited once a new qualifying skill shipped. This rule
closes that gap: a closed enumerated list is only as good as the discipline that keeps it current, and
without an explicit trigger tied to "a new component just shipped that meets this list's own criterion,"
that discipline has already failed once in this repo's own history.
