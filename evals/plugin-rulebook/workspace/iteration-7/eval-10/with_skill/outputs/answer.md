# R36 (Reciprocal Exclusions) check for `deep-review`

R36 is ADVISORY, judgment-based, forward-looking, never blocking. It applies when A's `## When NOT to Use` names B and the two domains genuinely overlap (a request could plausibly match either description). Pure delegation to a differently-scoped helper is not a finding. If it is a finding, it is reported against B (B should name A back).

## (a) "Reviewing a single skill's structure -> use skill-quick-check instead"

- **Finding: YES**, reported against `skill-quick-check`.
- **Severity: ADVISORY** (R36 is never blocking; not a FAIL).
- **Overlap judged:** both are review skills covering skill structure, so a request to review one skill could match either. A request landing on `skill-quick-check` has nothing telling it to defer to `deep-review`.
- **Fix:** add to `skill-quick-check`'s `## When NOT to Use` (or `description`) a line naming `deep-review` and stating skill-quick-check's own half of the distinguishing criterion, e.g. "Deeper, multi-aspect/whole-plugin review beyond a single skill's structure -> use `deep-review` instead." Per `.claude/rules/resolve-activation-overlap-bidirectionally.md`: name the specific sibling, state the criterion, do it in both directions. Only B's half of the criterion is needed, not a copy of A's.

## (b) "Saving the reviewed changes to version control -> use save-changes instead"

- **Finding: NO.**
- **Severity: none** (no finding to grade).
- **Reasoning:** this is plain delegation to a differently-scoped helper. `save-changes` records changes to version control; nobody asks it for a review, so a review request would never plausibly land on it. It does not need to name `deep-review` back. (Same logic as `cross-model-review` saying committing is `commit`'s job.) The reference notes that flagging every one-way pointer would be mostly noise (161 of 512 same-plugin pointers measured).
- **Fix:** none required. Optionally state the judged non-overlap in the report so the maintainer can disagree.
