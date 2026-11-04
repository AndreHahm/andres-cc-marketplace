## Summary
The runtime of the `Codex delta review` CI job is no longer acceptable, and on PR #638 the job stayed `in_progress` after its last step finished, holding the required check back.

## Environment
- **Product/Service**: `.github/workflows/marketplace-ci.yml`, job `codex-review` (`Codex delta review`), and the `publish` job that needs it (`Publish Codex policy result`)
- **Region/Version**: GitHub-hosted `ubuntu-latest`, job timeout 45 minutes

## Reproduction Steps
Observed once so far, not yet reproduced on purpose.

1. Push a commit to an open same-repository PR. On PR #638 this was records-only: head `b0e89c0b` added one JSON file under `.claude/review-outcomes/`.
2. Watch run 41860977725.
3. Compare the job's status with its steps and the `codex-review-result` artifact.

## Expected Behavior
The job finishes soon after its result is uploaded, `Publish Codex policy result` then runs, and a change this small does not hold a PR for long.

## Actual Behavior
Measured on run 41860977725 (all times UTC, 2026-11-04):

| Time | Event |
|---|---|
| 15:45:05 | Run created |
| 15:47:14 | `Codex delta review` started |
| 15:50:40 | `codex-review-result` artifact uploaded |
| 15:50:45 | Run last updated; `Publish Codex policy result` queued |
| 16:06:02 | Job still `in_progress`, run still `queued`, publish still queued |

At 16:05:32 every step of the job, including `Complete job`, reported completed. The required check stayed queued, so the PR stayed `BLOCKED` for more than 15 minutes after the review result existed.

For comparison, earlier Marketplace CI runs on the same PR took about 5 to 6.5 minutes end to end: 41858609474, 41856581720 and 41830422080.

## Impact
**High** - `Publish Codex policy result` is a required check and `publish` needs `codex-review`, so time spent in this job holds every same-repository PR back from merging. The maintainer states the runtime is no longer acceptable.

## Additional Context
**Not known yet:**
- Whether the stall on run 41860977725 comes from GitHub's job finalization, a post step or the workflow. It may be a one-off.
- How the time splits across the job's steps: the API returned no step timestamps here.
- How much of the general runtime complaint is this stall rather than the normal run length.

**To investigate:**
1. Where the job's time goes, step by step and across recent runs.
2. Why the job stayed `in_progress` after its last step completed.
3. Whether a records-only change needs all four reviewers, or review scope can skip or shrink it. A commit like the one above still moves the head SHA and re-runs the review.

**Related, not duplicates:** #541 (review scope in `cross-model-review`), #568 (reviewer refactor), #525 (blocking scope), #471 (`CODEX_KIT_REVIEW_TIMEOUT_MS` has no effect).
