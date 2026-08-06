# Severity Vocabulary

Shared across the `analysis-kit` skills that actually rate findings by severity — the first reference file in this plugin that lives outside any single skill's own `references/` directory, since its whole purpose is to be readable by more than one skill. Not every skill has a severity-rated vocabulary to ground: `analyzing-actor-behavior`, `mining-recurring-patterns`, and `comparing-sessions` report findings without a severity scale, and `generating-analysis-recommendations` rates complexity/risk/benefit into priority buckets (Quick Win/Strategic Investment/Nice-to-Have/Reconsider) — a different axis, not a severity scale. `starting-an-analysis` produces no findings of its own at all — it's a dispatcher, not an analysis skill. Those five skills have no mapping row below because they have nothing to map, not because of an oversight.

This does **not** replace any skill's existing severity terms (P1/P2/P3, Compliant/Violated/Ambiguous, and so on) — each skill keeps its own vocabulary, since that vocabulary is shaped by what the skill actually classifies. This file exists so a reader (or `reviewing-analysis-findings`, comparing two reports from different skills) can ground two differently-worded severity claims on one consistent scale, without either skill having to rename its own terms.

## The Four Tiers

| Tier | Meaning |
|---|---|
| **Critical** | Breaks behavior outright, bypasses a safety/governance boundary, or corrupts authoritative state. Not a matter of degree — something that should not happen at all. |
| **Major** | Materially degrades quality, correctness, or scope compliance, but doesn't break the component or bypass a boundary. The kind of thing that should get fixed before the next release, not necessarily before the next commit. |
| **Minor** | A real but low-impact issue — a local inefficiency, a polish item, a deviation that doesn't change outcomes. |
| **Informational** | Not itself a defect — a useful observation, a pattern worth tracking, a note for context. Doesn't require a fix to close. |

This is a 4-tier scale, not the 5-tier model some external session-analysis concepts use (which adds a separate `blocking` tier between Critical and Major). That distinction wasn't judged worth a separate tier at analysis-kit's current scope — a finding that blocks a gate or a trustworthy analysis is, in practice, Critical here.

## Mapping Existing Per-Skill Terms

| Skill | Term | Maps to |
|---|---|---|
| `analyzing-plugin-components` | P1 (breaks behavior) | Critical |
| `analyzing-plugin-components` | P2 (degrades quality) | Major |
| `analyzing-plugin-components` | P3 (polish) | Minor |
| `comparing-session-to-specification` | Violated ("must"/"will" language) | Major, sometimes Critical if the violated section is a safety/scope boundary |
| `comparing-session-to-specification` | Violated ("should"/"may" language) | Minor |
| `comparing-session-to-specification` | Extra implementation | Minor, unless the added scope itself crosses a stated non-goal — then Major |
| `comparing-session-to-specification` | Ambiguous, Unaddressed, Compliant | Not a severity — these are verdicts about evidence, not findings to rate |
| `analyzing-governance-and-conflicts` | Any of the four conflict categories | Major by default; Critical only if the contradiction involves a safety/governance boundary |
| `analyzing-governance-and-conflicts` | Recurring error taxonomy (Phase 4) | Follows the error's own category severity, not a fixed mapping — a `permission_denial` that blocked progress reads differently than a `user_correction` on phrasing |
| `analyzing-tool-and-framework-use` | Framework role-conformance authority-check violations | Critical (these are governance-boundary crossings by definition) |
| `analyzing-tool-and-framework-use` | Framework role-conformance process/artifact-check violations | Major |
| `reviewing-analysis-findings` | Severity-undercut findings | Inherits the lower of the two reports' own severities for that subject, flagged as a discrepancy rather than silently resolved |

When a skill's own term isn't listed here, use the tier definitions above directly — don't leave severity ungrounded just because this table doesn't happen to name that skill's exact wording yet.

## Using This File

Read it when a finding's severity needs to be compared against a finding from a *different* skill's report — most relevantly in `reviewing-analysis-findings`' Severity Undercut check, but also whenever a human reader is trying to judge two analysis-kit reports' relative urgency side by side. For a single skill's own report in isolation, that skill's own native vocabulary (P1/P2/P3, Violated/Compliant, etc.) is sufficient — there's no need to translate into this scale just to read one report.
