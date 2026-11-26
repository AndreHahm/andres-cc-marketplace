# merge-pr 970 --stop-on-review-findings (simulated exercise)

No gh/git commands were run and no repository file was edited. This describes the procedure from the skill files, using the data given in the task.

## Variant 1: Devin "Major" review on the current head, plus a session item to fix

Data: headRefOid `aaaa...`, comments `[]`, reviews = [devin-ai-integration, COMMENTED, commit `aaaa...`, body "Major: the parser drops the last line."], 0 unresolved threads.

### Step 1.5, before the push

1. Checkout check passes: isCrossRepository is false, every push URL from `git remote get-url --push --all origin` matches owner/repo, the branch matches headRefName, and `git rev-parse HEAD` equals headRefOid `aaaa...`. The local fix is uncommitted, so HEAD is still the PR head.
2. The touched item is "fix now". The fix is already applied and verified locally. No new finding was raised by verification, so there is no second batch.
3. Step 1.6 runs before the push. The body check finds nothing stale, so no body edit is made and the run says so.
4. Record the latest `startedAt` of every `statusCheckRollup` entry as the wait baseline, immediately before the push.
5. Commit and push in one `Skill(commit)` run with `--push`. This is the first point where anything is committed or pushed. The commit lands on the PR head, and the run does not restart from step 1.

The review-findings stop is a step 2 check, not a step 1.5 check. Nothing in step 1.5 reads GitHub reviews, so the Devin finding does not block the commit or the push.

### Step 2 after the push

- Wait for the CI run this push started (the step 2 "waiting for this skill's own runs" paragraph). The head must be the pushed SHA.
- The Devin review still counts as live. Its `commit.oid` equals step 1's headRefOid, and a review on step 1's head stays live after step 1.5's own fix push.
- With `--stop-on-review-findings`, the review-body bullet reads the body of a non-CHANGES_REQUESTED review. "Major: the parser drops the last line." is a defect report, so it is a reviewer finding. The unresolved-thread count is 0, so that part does not stop.
- The run stops before step 3 and before any merge prompt. It reports a review-finding stop naming devin-ai-integration, the submission time, and the COMMENTED state. It does not act on the finding text.
- The same stop repeats on every later pass (4(e), 7(b), 7(d)) until the finding is cleared. The skill says it is cleared by hiding the comment (not applicable to a review body) or by a new head push. Here a review body clears only once a new head is pushed. Because this review is on step 1's head, the push made in this run would clear it only if the review were no longer live. The skill's liveness rule keeps it live, so the stop stays until the user addresses the finding and pushes again, or the user decides how to proceed.
- Nothing is merged. The run ends at the stop and offers no merge confirmation.

Summary for variant 1: the fix is committed and pushed at step 1.5 (via `Skill(commit)` with `--push`), and then step 2 stops with a review-finding stop on the Devin Major review. No merge happens.

## Variant 2: no session item, CHANGES_REQUESTED by octocat on another commit

Data: reviews = [octocat, CHANGES_REQUESTED, submitted 2026-11-20, commit `bbbb...`, body "Please split this function."]. headRefOid is still `aaaa...`.

### Step 1.5

- The checkout check passes, and the scan finds nothing from this session. The run says so and goes on.
- No fix is applied, so nothing is pushed.

### Step 1.6

- Nothing is stale, so no body edit is made.

### Step 2 (first pass, no push, so step 1's data is current)

- The review-findings stop does not fire on this review, for two reasons:
  - It is not live. Its `commit.oid` `bbbb...` is a 40-hex SHA other than this pass's headRefOid `aaaa...` and other than step 1's headRefOid, so it is tied to an earlier head and the skill's liveness rule skips it.
  - Its state is CHANGES_REQUESTED. The review-body bullet covers only the bodies of other review states, since a CHANGES_REQUESTED review already fails the no-outstanding-change-requests check.
- The run stops anyway, at the required check "No outstanding change requests". It checks each reviewer's latest review for CHANGES_REQUESTED. This check has no commit-liveness filter, so octocat's review blocks readiness regardless of its commit. The run reports that a review from @octocat requests changes and stops without reaching step 3, so no merge rights check, no confirmation and no merge.
- The `--stop-on-review-findings` flag is not what stops the run here. It would only add a stop for a live finding in a comment or in a non-CHANGES_REQUESTED review body.
- The bypass exception does not apply, because the only non-passing required check here would be the review state, not `Publish Codex policy result`.

Summary for variant 2: the review-findings stop does not fire. The run stops earlier, at step 2's CHANGES_REQUESTED gate, because octocat's latest review requests changes. The gate ignores the review's commit, and the user needs octocat to re-review or to dismiss the review before the PR can be merged.
