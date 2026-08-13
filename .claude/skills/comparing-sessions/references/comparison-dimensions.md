# Comparison Dimensions

What counts as a meaningful comparison point between two sessions' reports:

- **Component verdicts** — did the same skill/agent/rule get a different SWOT verdict or suggestion severity between the two reports?
- **Suggestion recurrence** — does a suggestion from the prior report appear again (in substance, not necessarily identical wording) in the current one? This is the strongest signal that a suggestion wasn't acted on.
- **Tool/framework detection stability** — if both reports include tool or framework findings, did the detected framework or tool set change? An unexpected change is worth flagging even if neither report calls it out.
- **Metric direction** — for any numeric metric present in both reports (a count, a score), note the direction of change, not just the raw numbers.

## What Isn't a Meaningful Comparison

- Two reports covering entirely different scopes (different components, different date ranges) with no actual overlap — note this and stop rather than forcing a comparison.
- Formatting or section-naming differences between skill versions — these show up in the structural diff but aren't content findings.
