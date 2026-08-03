# Governance Conformance Checklist

For each rule found by `component_inventory.py`'s `rule` category entries:

- [ ] Was the rule's guidance actually followed in situations where it applied?
- [ ] Was there a situation where the rule should have applied but was never cited or considered?
- [ ] If the rule was followed, was it followed correctly (not just nominally referenced)?
- [ ] If the rule was violated, was the violation caught and corrected within the session, or did it ship uncorrected?

## Common Patterns

- **Silent non-application** — a rule exists and clearly applies to a situation, but nothing in the session shows it being consulted. This is the most common and easiest-to-miss governance gap, since there's no negative event to notice — only an absence.
- **Partial application** — a rule was consulted but only followed in part (e.g. a rule requiring both an X and a Y step, where only X happened).
- **Correct application under pressure** — a rule was followed even when following it cost time or required extra steps. Worth noting as a strength, not just a compliance checkbox.
