# Step 4(c), PR 933: wait or capture the baseline

Each poll: `gh pr view 933 --json headRefOid,statusCheckRollup`, then step 2's
`git-required-checks.py`; 15 seconds apart, at most 40 attempts. The wait ends only when, on two
consecutive polls, both hold (and the head is still 1111111111111111111111111111111111111111):

- A: no `CheckRun` with `workflowName` `Marketplace CI` is other than `COMPLETED`;
- B: the script reports no required context pending or missing, except that
  `Publish Codex policy result` may be missing (not pending).

A failing context does not keep the wait going: only pending/missing do.

| Poll | A | B | Decision |
|---|---|---|---|
| 1 | no | yes (missing is the permitted exception) | keep waiting |
| 2 | no | no (pending) | keep waiting |
| 3 | yes | yes | keep waiting: first qualifying poll (1 of 2) |
| 4 | yes | yes | go on: second consecutive qualifying poll |

**Poll 1: wait.** `Codex delta review` is IN_PROGRESS, so a Marketplace CI run is in flight. It has not
created its policy job yet, which is why no required context shows it. The missing
`Publish Codex policy result` alone would be allowed, but A fails. A baseline taken now would let this
run's stale policy result land after it and be read in (d) as the bypass failing. Consecutive count: 0.

**Poll 2: wait.** `Publish Codex policy result` is IN_PROGRESS, so A fails, and the script reports it
pending, so B fails: the exception covers only missing. Count: 0.

**Poll 3: wait one more poll.** Both conditions hold; the failing policy result is the expected
pre-label failure the bypass is for. But one qualifying poll is not enough. Count: 1.

**Poll 4: go on.** Both conditions hold on two consecutive polls (3 and 4). Now, before touching the
label, run `gh pr view 933 --json statusCheckRollup` and record the `startedAt` of the
`Publish Codex policy result` `CheckRun` (the latest one if several) as the baseline. An entry exists,
so the rollup-wide fallback is not used. Then verify the label exists in the repo, check the PR's
labels, and apply it (remove and re-add if already present). Step (d) accepts only a `COMPLETED`
entry whose `startedAt` is strictly later than this baseline.

At any poll: a different `headRefOid` stops the run (report both SHAs); script exit `2` stops the run;
40 attempts used up stops it, reporting the pending contexts and non-`COMPLETED` entries. Script exit
`1` at polls 1-4 is only the reported non-passing states, not a stop here.
