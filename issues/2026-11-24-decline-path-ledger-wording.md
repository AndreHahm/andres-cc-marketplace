## Summary
handling-review-findings: the Decline path says "no tracking artifact", but the outcomes ledger wants a disposition for every finding, `declined` included

## Environment
- **Product/Service**: git-kit plugin, `handling-review-findings` (`SKILL.md` step 6, `references/fix-self-review.md` 4e)
- **Region/Version**: `main` at `46fb706a`
- **Browser/OS**: any

## Reproduction Steps
1. Read `SKILL.md` step 6, the Decline path (line 107).
2. Read `references/fix-self-review.md` 4e.
3. Follow step 6 for a Minor finding with `review_findings_severity_gate: true`.

## Expected Behavior
Both texts say the same thing about a declined finding: either it gets a ledger entry, or the ledger's "per finding" instruction names declined findings as an exception.

## Actual Behavior
- Step 6 says to reply and leave the thread unresolved, "with no tracking artifact".
- Section 4e says "Record one disposition per finding" and lists `declined` as a disposition.
- A reader who follows step 6 literally records nothing, so the declined finding is missing from the ledger and the outcomes corpus.

## Error Details
~~~
None: the step is skipped without an error.
~~~

## Visual Evidence
None.

## Impact
**Low** - "tracking artifact" may mean only a GitHub issue, so some readers will record the entry anyway. The cost is incomplete outcomes data.

## Additional Context
Reported independently by `skill-reviewer` and `plugin-rulebook-checker` at commit `4d205310` in a reviewer comparison run for #862; the owner labelled both findings as real. Re-read on `main`: both texts are still there. Nothing was executed.

Fix shape: state in step 6 that a declined finding still gets a `declined` ledger entry (4e), and that "no tracking artifact" means no issue.
