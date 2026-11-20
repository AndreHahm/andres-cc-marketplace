# fix(ci): the Codex review anchor relies on the GitHub API returning the newest run first

## Summary
`find_review_anchor` takes the first qualifying run in the order the GitHub runs API returns them and never sorts by `created_at`. R5 requires the newest qualifying run.

## Environment
- **Product/Service**: `scripts/marketplace_ci/review.py`, `find_review_anchor` (used by `compute-scope` and `codex-review` in `marketplace-ci.yml`)
- **Region/Version**: `main` as of 2026-11-20
- **Browser/OS**: n/a

## Reproduction Steps
1. Read `find_review_anchor`: the candidate list is built from `actions/workflows/.../runs?status=completed&per_page=30` in response order.
2. The loop over candidates returns the first one whose result or record qualifies.
3. No step sorts the candidates by `created_at`, and no test pins the order.

## Expected Behavior
Per `docs/ci-codex-review-user-requirements.md` R5: the anchor is the head of "the newest other Marketplace CI run for this pull request that was already complete when this run was created".

## Actual Behavior
Correct only while GitHub returns runs newest first. If that order changed, an older qualifying run could become the anchor: the reviewed delta would widen, and findings carried from the wrong run could be lost or kept.

## Error Details
~~~
None observed.
~~~

## Visual Evidence
None.

## Impact
**Low** - latent. No wrong anchor has been observed, but meeting the requirement rests on an unstated, untested assumption about the API's order.

## Additional Context
- Found by an R1-R15 audit of the Codex delta review during issue #793's work (2026-11-20).
- Direction: sort the candidates by `created_at`, newest first, before the loop, and add a test that feeds them out of order.
