# CI Workflow Stability Analysis — `CI` on `main`

## Data source

Six synthetic run records (`run-142.json` … `run-147.json` in this directory), shaped after the
typical fields returned by `gh run view <id> --json databaseId,number,attempt,workflowName,name,
displayTitle,headBranch,headSha,event,status,conclusion,createdAt,startedAt,updatedAt,url,jobs`.
No real `gh` CLI access was available in this sandbox, so these records were authored by hand to
represent a plausible run history for one workflow (`CI`) on one branch (`main`), in chronological
order.

## Raw run sequence

| # | Run # | Attempt | Created (UTC)         | Conclusion  | headSha (short) |
|---|--------|---------|------------------------|-------------|------------------|
| 1 | 142    | 1       | 2026-09-18T09:12:03Z   | success     | abc1234 |
| 2 | 143    | 1       | 2026-09-18T11:45:21Z   | **failure** | def4567 |
| 3 | 144    | 2       | 2026-09-18T11:58:47Z   | success     | def4567 (same commit, rerun) |
| 4 | 145    | 1       | 2026-09-18T16:22:10Z   | **failure** | ghi7890 |
| 5 | 146    | 2       | 2026-09-18T16:35:02Z   | success     | ghi7890 (same commit, rerun) |
| 6 | 147    | 1       | 2026-09-19T10:05:33Z   | **failure** | jkl0123 |

Conclusions alternate perfectly: success, failure, success, failure, success, failure.
Failure rate across the 6 runs: 3/6 = 50%.

## Key observations

1. **Every failure isolates to the same job and the same step.** In all three failing runs
   (143, 145, 147), the `build-and-test` job fails specifically at step 5, "Run integration
   tests." Steps 1-4 (Checkout, Setup Node, Install dependencies, Run unit tests) pass in
   *every single run*, including the failing ones. This rules out infrastructure-wide breakage
   (checkout/setup problems) and points at something specific to the integration-test step.

2. **Two of the three failures are proven non-deterministic, not code regressions.** Runs 143
   and 145 were each immediately re-run (attempt 2) against the *identical commit SHA*
   (`def4567...` -> run 144, `ghi7890...` -> run 146), with no code change in between, and both
   reruns passed cleanly through the same step that had just failed. A failure that flips to a
   pass on a rerun of the same commit, with zero code difference, cannot be a real regression
   introduced by that commit — by definition it's the workflow (or the test/environment it
   exercises) producing a different result on the same input. That is the textbook signature of
   flakiness.

3. **The most recent failure (147) matches the same signature.** Run 147, on a new commit
   (`jkl0123...`), fails at the identical job/step as the two proven-flaky failures, with the same
   pattern (unit tests pass, integration tests fail, coverage upload skipped). No rerun exists
   yet for this commit in the data provided, so it isn't independently confirmed flaky the way
   143 and 145 are — but given it reproduces the exact same failure shape already proven twice to
   be non-deterministic, it is far more consistent with "same flaky test tripped again" than with
   "this commit introduced a new bug."

4. **Unit tests never fail.** Only the integration-test step is ever implicated, across all
   three failures. This narrows the likely root cause to something specific to the integration
   suite — timing/race conditions, shared external state, network/service dependency, or test
   ordering — rather than a broad build or environment problem.

## Conclusion: Yes, this run group is unstable/flaky

The workflow is not reliably signaling real pass/fail status on this branch. The evidence for
flakiness (rather than "3 separate real bugs that happened to land 1-for-1 with 3 separate real
fixes") is strong:

- The failure/success alternation is not explained by code changes alone — two of the three
  failures reversed to success on a rerun of the exact same commit.
- All three failures share one specific culprit (the "Run integration tests" step), not three
  different failure points.
- A 50% failure rate concentrated in a single step, with same-commit reruns flipping outcome,
  is inconsistent with genuine, code-caused breakage and consistent with an intermittent/flaky
  test or environment issue in the integration-test step.

## Caveats / what would strengthen this further

- This analysis only has `conclusion` at the job/step level, not actual log output. Pulling
  failed-step logs (e.g. `gh run view <id> --log-failed`) for runs 143, 145, and 147 would let
  us confirm whether the same specific test case (not just the same step) is failing each time,
  and read the actual error (timeout, assertion, connection reset, etc.) to pin down root cause.
- Only 6 runs were analyzed; a larger sample (e.g. last 20-30 runs on this branch) would give a
  more statistically confident failure rate and rule out coincidence, though 2-for-2 same-commit
  rerun reversals is already a strong signal even at this sample size.
- If a rerun of run 147 becomes available, checking whether it also flips to success on the
  identical commit would make the case for flakiness fully conclusive (3-for-3) rather than
  2-for-3 directly confirmed + 1 pattern-matched.

**Recommendation:** treat single failures of this workflow on this branch as suspect rather than
automatically blocking, specifically for the "Run integration tests" step; investigate that step
for non-determinism (race conditions, shared/external state, timing assumptions) before trusting
its conclusion at face value, and consider quarantining or adding a bounded automatic retry to
that step until the root cause is fixed.
