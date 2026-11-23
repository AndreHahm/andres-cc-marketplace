## Summary
Marketplace CI: carried jobs expose a read token to later PR-code steps

## Environment
- **Product/Service**: Marketplace CI (`.github/workflows/marketplace-ci.yml`), the carry step from #706
- **Region/Version**: branch `fix/merge-pr-readiness-and-ci-reruns`

## Reproduction Steps
1. Read the five carrying jobs in `.github/workflows/marketplace-ci.yml`: `python-quality`,
   `review-helpers-windows`, `node-tests`, `marketplace-parity`, `prefix-permanence`.
2. Each one grants `actions: read`, `issues: read` and `pull-requests: read` for the carry lookup.
3. The later steps of the same job run PR code (tests, linters).

## Expected Behavior
Steps that run PR code have no token scopes beyond what the job's checks need.

## Actual Behavior
The carry step gets the token only in its own environment, but a later step of the same job can still
read the job token from the runner. So PR code in these five jobs can read Actions, issue and PR data
with that token. `docs/ci.md` ("Carried results on a description edit") already states this.

## Error Details
~~~
None: a security-review finding (m-B3/m-B4), not a runtime error.
~~~

## Visual Evidence
None.

## Impact
**Low** - read-only scopes, and only for same-repository PRs, whose authors already have write access.
It still widens what PR code can read in five jobs.

## Additional Context
Proposed fix: move the carry decision into a separate job that checks out no PR code. That job holds the
read scopes and passes only its verdict to the five jobs, which then drop the extra permissions.

Files: `.github/workflows/marketplace-ci.yml`, `scripts/marketplace_ci/prior_result.py`, `docs/ci.md`.
Follow-up to #706.
