## Summary
Accepted-findings waivers and maintainer confirmations are read once per workflow run and not re-checked when they are used, so one removed during the run can still apply

## Environment
- **Product/Service**: marketplace CI, `.github/workflows/marketplace-ci.yml` (Codex delta review) and `.github/workflows/claude-review-ci.yml` (Claude delta review)
- **Region/Version**: PR #822 head `f2db9f98ab6c2bcae455df0560c634dc5cd142c2` (issue #808)

## Reproduction Steps
1. A PR body lists a waiver for a security or gate-critical finding, and a maintainer posts the matching `- confirmed <rule> <path> @<fingerprint>` comment.
2. A Codex delta review run starts; `fetch-accepted-findings` (around `marketplace-ci.yml:1604`) reads the section and the confirmation keys into `accepted-findings.json`.
3. While the reviewers run, the maintainer deletes the confirmation comment (or the author removes the waiver line from the body).
4. The run finishes; the policy job publishes the result using the keys read in step 2.

The Claude delta review has the same shape: its publish step (`claude-review-ci.yml:604-605`) applies the `accepted-findings.json` the scope job read, and a body edit does not restart that workflow.

## Expected Behavior
A waiver or confirmation that no longer exists when the result is published does not waive a finding: the trusted policy job (and the Claude publish step) re-validates the waivers the result actually used, and blocks, or does not apply the waiver, when one is gone. An unchanged confirmation still passes.

## Actual Behavior
The run uses the state read at its start. Deleting a comment does not restart the workflow, and the policy job does not re-validate, so a run with no other blocking finding can pass on a confirmation that was withdrawn mid-run. The Claude review is advisory, so there it only mislabels a finding as waived.

## Error Details
~~~
None: the run succeeds.
~~~

## Visual Evidence
None.

## Impact
Medium. A time-of-check/time-of-use gap in a required gate. Exploiting it needs a maintainer's confirmation to exist first and to be withdrawn during a run, so it is a lapse window, not a bypass of the confirmation itself. Fixing it is a design change to the policy job (which needs a token to re-read comments) and is out of scope for PR #822.

## Additional Context
- Found in PR #822.
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/822
- Head SHA: `f2db9f98ab6c2bcae455df0560c634dc5cd142c2`
- Thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/822#discussion_r4655074277 (CodeRabbit, Major, `marketplace-ci.yml:1604`)
- Also: CodeRabbit's review body on PR #822, outside-diff comment on `claude-review-ci.yml:604-605` (Minor)
- Reviewers: CodeRabbit
- Severity: Major (Codex policy job), Minor (Claude publish, advisory)
- Related: #808, #832.
