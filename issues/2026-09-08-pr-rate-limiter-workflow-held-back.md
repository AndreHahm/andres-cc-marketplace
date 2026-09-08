## Summary
Decide whether to ship the drafted `pr-rate-limiter.yml` workflow, held back from PR #294

## Environment
- **Product/Service**: `andres-cc-marketplace` repo tooling — `.github/workflows/` (PR/CI governance workflow set)
- **Region/Version**: N/A

## Reproduction Steps
N/A — this is a tracking issue for a deferred decision, not a bug.

## Expected Behavior
N/A

## Actual Behavior
N/A

## Error Details
~~~
N/A
~~~

## Visual Evidence
N/A

## Impact
**Low** — no functional impact; this is a scope decision, not a defect. Left untracked, the decision context and the drafted file's location would be lost once the current session ends.

## Additional Context
PR #294 (`feat/pr-ci-governance`) reviewed 5 drafted workflows from `.draft/_open/marketplace/ci/workflows/`:

- `pr-rate-limiter.yml` — **held back** (this issue)
- `pr-size-labeler.yml` — shipped
- `pr-size-labeler-batch-run.yml` — shipped
- `issue-opened-labeler.yml` — shipped
- `self-assign-issue.yml` — shipped (redesigned from an earlier drafted comment-driven `/assign` bot)

`pr-rate-limiter.yml` would cap the number of simultaneously open PRs (e.g. via `Homebrew/actions`' own `limit-pull-requests` action), but was explicitly held back rather than approved for this PR. The drafted file was still fixed and reviewed before the hold-back decision (kill-switch check and fork-safety step added; a fabricated SHA-pin version-tag comment corrected to an honest, verified reference) — it just was never committed to the repo.

The file currently sits at `.draft/_open/marketplace/ci/workflows/pr-rate-limiter.yml`, inside this repo's gitignored `.draft/` directory (local-only planning/draft space, per `.claude/rules/plugin-rulebook-enforcement.md`'s "Not in scope" note for that directory) — it has no other tracking anywhere in the repo.

Next step: revisit whether this workflow is still wanted, and if so, move it out of `.draft/` the same way the other 4 were.
