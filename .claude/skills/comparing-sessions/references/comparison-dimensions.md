# Comparison Dimensions

What counts as a meaningful comparison point between two sessions' reports:

- **Component verdicts** — did the same skill/agent/rule get a different SWOT verdict or suggestion severity between the two reports?
- **Suggestion recurrence** — does a suggestion from the prior report appear again (in substance, not necessarily identical wording) in the current one? This is the strongest signal that a suggestion wasn't acted on.
- **Tool/framework detection stability** — if both reports include tool or framework findings, did the detected framework or tool set change? An unexpected change is worth flagging even if neither report calls it out.
- **Metric direction** — for any numeric metric present in both reports (a count, a score), note the direction of change, not just the raw numbers.

## Recommendation Realized Impact (Optional, Phase 4)

Only relevant when a recommendation registry is available. For each `recommendation_id` matched between
the registry and this comparison's scope (matched by the stable ID only — see "What Isn't a Meaningful
Comparison" below), the comparable fields are:

- **Expected Effect** — the registry's own `expected_effect` field, recorded at `accepted`/`implemented`
  time.
- **Before Evidence** — the prior report's own finding this recommendation traces back to, or the
  registry's `evidence` field at `proposed`/`accepted` time if the prior report itself doesn't state it.
- **After Evidence** — the registry's own `observed_effect` field if a `measured` event exists for this
  ID; otherwise, whatever the current report's own findings for the same subject area actually show.
- **Impact Verdict** — one of `improved`, `unchanged`, `regressed`, `not_measurable`. Use
  `not_measurable` whenever After Evidence isn't actually adequate to support a verdict — never force
  `unchanged` as a default when the honest answer is "can't tell from what's available."

## What Isn't a Meaningful Comparison

- Two reports covering entirely different scopes (different components, different date ranges) with no actual overlap — note this and stop rather than forcing a comparison.
- Formatting or section-naming differences between skill versions — these show up in the structural diff but aren't content findings.
- A registry entry and a report finding that merely *sound* related — realized-impact matching is by
  stable `recommendation_id` only; a wording match with no exact ID match is not a comparison point.
