# R21 results for Skills A, B and C

Source: `SKILL.md` R21 and `references/size-rules.md`. Thresholds: `description` is OK at 80-1018 chars. `when_to_use` is OK at 506 chars or fewer. Combined length is OK at 1524 chars or fewer. The split-hint ADVISORY applies when a `description` is over 900 chars, carries a "Use when..." clause, and has no `when_to_use` field.

| Skill | Finding? | Severity | Recommendation |
|---|---|---|---|
| A (desc 950, "Use when", no when_to_use) | Yes, split hint | ADVISORY (non-blocking) | Consider moving the "Use when..." clause into a new `when_to_use` field (cap 512 chars). That keeps `description` short. |
| B (desc 880, "Use when", no when_to_use) | No | None (PASS) | No action. 880 is not over 900, so the hint is never raised. |
| C (desc 950, "Use when", when_to_use 200) | No | None (PASS) | No action. The hint needs "no when_to_use", and C has one. Combined length is 1150, under 1524. |

Details:
- **A:** 950 is within the OK band (80-1018), so there is no size Warning or Critical. The only item is the ADVISORY. It is never blocking. The docs weight `description` more than `when_to_use` for invocation, so the move is a tradeoff, not a defect. The user may decline it.
- **B:** 880 is at or under the 900 hint threshold, and a description at or under 900 is never flagged.
- **C:** 950 is within the OK band. `when_to_use` is 200, which is under 506. The combined length is 1150, which is under 1524. No Warning or Critical applies. The hint is not triggered because the clause already has a home in `when_to_use`.

Overall severity: no Critical or Warning for any of the three. Only A carries an ADVISORY.
