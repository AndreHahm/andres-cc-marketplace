# fix(ci): a run converted to draft fails Publish Codex policy result, R14 says it passes as skipped

## Summary
A Marketplace CI run that started on a ready PR fails `Publish Codex policy result` when the PR is converted to draft before the Codex call. R14 says a draft passes as skipped, whatever the event.

## Environment
- **Product/Service**: `marketplace-ci.yml`, jobs `codex-review` ("Codex delta review") and `publish` ("Publish Codex policy result")
- **Region/Version**: `main` as of 2026-11-20
- **Browser/OS**: GitHub-hosted `ubuntu-latest`

## Reproduction Steps
1. Open a ready PR that is not bypass-eligible, so `codex-review` runs.
2. While that run waits or runs, convert the PR to draft (`converted_to_draft` starts no new run).
3. The step "Make no Codex call if the PR was converted to draft" re-reads the draft flag, finds `true`, and fails `codex-review`.
4. `publish` then fails.

## Expected Behavior
Per `docs/ci-codex-review-user-requirements.md` R14: "While a pull request is a draft, the Codex delta review does not run, whatever the event. `Publish Codex policy result` passes as skipped."

## Actual Behavior
`codex-review` fails and `publish` fails. `docs/ci.md`'s Drafts bullet describes this failure as intended. The requirements doc does not, and by its own precedence rule ("where the two disagree, this document states the intent") one of the two must change.

## Error Details
~~~
::error::the PR is a draft now (or its draft state could not be read): no Codex call -- marking it ready re-runs the review
~~~

## Visual Evidence
None.

## Impact
**Low** - a draft cannot be merged, and marking it ready reviews the whole PR (R14). The gap is between the documented intent and the behavior, not a merge risk.

## Additional Context
- Found by an R1-R15 audit of the Codex delta review during issue #793's work (2026-11-20).
- Direction: decide which side changes. Either amend R14 to accept the failing check for this case (and keep `docs/ci.md`), or make the draft check exit without failing and let `publish` treat it like the draft skip.
- Related wording issue in the same bullet: `docs/ci.md` says `compute-scope` reports eligible on a draft "without a lookup". The lookup subcommand is still invoked and returns early (`scripts/marketplace_ci/review.py`, `find_review_anchor`), and the carry step still runs with an empty anchor.
