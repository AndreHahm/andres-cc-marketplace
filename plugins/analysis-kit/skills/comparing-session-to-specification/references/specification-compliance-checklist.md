# Specification Compliance Checklist

For each section of the specification document:

1. Extract the section's actual claims — goals, non-goals, requirements, constraints.
2. Search conversation context and any in-scope persisted report for evidence touching this section's subject.
3. Classify:
   - **Compliant** — evidence found, and it aligns with the section's claims.
   - **Violated** — evidence found, and it contradicts the section's claims.
   - **Unaddressed** — no evidence either way; the session had no occasion to touch this.
   - **Ambiguous** — evidence exists but doesn't clearly resolve compliant vs. violated, or the spec's own wording is unclear.

## Severity Guidance for Violated Findings

- A violated **non-goal** (something the spec explicitly says should NOT happen) is more severe than a violated **should**-level guideline.
- A violation caught and corrected within the same session is less severe than one that shipped uncorrected.
- A violation of a section using "must"/"will" language is more severe than one using "should"/"may" language — the spec's own modal verb is a severity signal, not just style.

## Common Mistakes

- Treating "the session didn't mention this" as "Violated" — that's Unaddressed, not Violated. A violation requires actual contradicting evidence, not just silence.
- Skipping ambiguous spec language rather than flagging it — an ambiguous spec section is itself a finding worth surfacing (possibly one for `analyzing-governance-and-conflicts` to track as a rule-quality issue, if the spec functions like a project rule).
