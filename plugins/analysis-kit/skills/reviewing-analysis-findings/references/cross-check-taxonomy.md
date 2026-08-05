# Cross-Check Taxonomy

Three categories for classifying a candidate finding pair across two analysis-kit reports. A pair only gets classified once — don't force a finding into more than one category; pick the strongest match.

## Duplicate

**Definition:** two findings, from two different reports, describe the same underlying issue with the same root cause — even if the wording, framing, or severity label differs.

**Detection guidance:**
- Look for shared proper nouns first (the same file path, skill name, rule name, or component) as a candidate signal, then confirm the underlying claim actually matches.
- A duplicate can come from two skills examining the same evidence from different angles (a SWOT weakness and a governance conflict both citing the same missing gate) — this is expected overlap between analysis-kit's own skills, not a sign either skill is wrong.
- Not a duplicate: two findings about the same component that describe *different* problems (e.g. one about a missing test, one about a naming violation) — same subject, different root cause, so these stay separate findings.

**What to report:** cite both reports' finding text side by side, and note that a reader acting on both should treat this as one action item, not two.

## Contradiction

**Definition:** two reports reach opposite verdicts about the same subject, and neither report's own text acknowledges the other's finding (no "see also," no explicit deferral, no version/timestamp note explaining the divergence).

**Detection guidance:**
- Confirm same subject first — same file, same decision, same component — before treating opposite-sounding language as a contradiction. Two strongly-worded findings about different things are not a contradiction.
- A contradiction is not automatically a defect in either report — reports can legitimately be produced at different points with different information available. Check timestamps: if report B was written after report A and addresses the same subject differently, that may be an intentional update, not an unacknowledged contradiction. Only flag it as a genuine Contradiction if nothing in either report's text explains the divergence.
- Distinguish severity disagreement (covered under Severity Undercut below) from verdict disagreement — a Contradiction is about the *substance* of the finding (violated vs. compliant, present vs. absent), not just how urgently it's rated.

**What to report:** cite both reports' conflicting statements verbatim, with enough surrounding context that a reader can judge which (if either) is more current or better-evidenced — this skill doesn't make that call itself.

## Severity Undercut

**Definition:** one report rates a finding at a given severity (in its own native vocabulary — P1/P2/P3, Violated, Critical, etc.), but another report's own cited evidence for a related or the same finding implies a different severity than the first report claims, once both are translated onto `../../references/severity-vocabulary.md`'s shared scale.

**Detection guidance:**
- Translate both reports' severity terms into the shared 4-tier scale (Critical/Major/Minor/Informational) using `severity-vocabulary.md`'s mapping table before comparing — don't compare native vocabularies directly, since "P2" and "Violated" aren't inherently comparable without that translation.
- The undercut has to come from the *other report's own evidence*, not from this skill's own independent judgment about how severe something should be — this skill cross-checks reports against each other, it doesn't re-adjudicate severity from scratch.
- A common real case: report A calls something Major based on limited evidence; report B, examining the same subject in more depth, cites evidence that would only support Minor (or vice versa, evidence supporting Critical when report A said Major). Either direction counts.

**What to report:** state both reports' severity claims (native term + translated tier), the specific evidence from the undercutting report, and flag the discrepancy — inherit the lower of the two severities as the flagged value (a conservative default until a human resolves which is right), per `severity-vocabulary.md`'s own guidance for this skill's entry in its mapping table.
