## Summary
A finding on a file the PR deletes has no fingerprint, so its waiver can never be confirmed when it needs a maintainer's confirmation

## Environment
- **Product/Service**: marketplace CI waivers (R7), `scripts/marketplace_ci/review.py` (`find_waiver`, `fingerprint_at`) and `scripts/marketplace_ci/claude_review.py` (`head_line_reader`)
- **Region/Version**: PR #822 head `f2db9f98ab6c2bcae455df0560c634dc5cd142c2` (issue #808)

## Reproduction Steps
1. A PR deletes a file on a gate-critical path (or one a security finding names).
2. A reviewer reports a Critical/Major finding on that file at a line number.
3. The author adds the waiver line and a maintainer posts a confirmation.

## Expected Behavior
There is a documented way to waive and confirm such a finding, for example a fingerprint taken from the base side of the diff, or `@-` accepted for a deleted file.

## Actual Behavior
The flagged line cannot be read at the head (the file is gone), so the finding has no fingerprint. `find_waiver` accepts a confirmation only for a waiver with a fingerprint, so the waiver never applies and the finding keeps blocking. The review prompt (`.github/claude-review/prompt.md:26-27`) asks for a fingerprint the author cannot compute. It fails closed: nothing is wrongly waived.

## Error Details
~~~
"needs a maintainer's confirmation comment `- confirmed <rule> <path> @<fingerprint>`"
~~~

## Visual Evidence
None.

## Impact
Low. Edge case (a sensitive finding on a deleted file) that fails closed; the workaround is the Codex-review bypass attestation. Choosing which fingerprint a deleted line gets is a design decision for R7.

## Additional Context
- Found in PR #822.
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/822
- Head SHA: `f2db9f98ab6c2bcae455df0560c634dc5cd142c2`
- Thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/822#discussion_r4655038677 (`scripts/marketplace_ci/claude_review.py:444`)
- Reviewer: Devin
- Severity: Minor
- Related: #808.
