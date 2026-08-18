Context: steps 1-7 of `codex-review-recovery` have already completed for PR #77 — the `Await Codex review`
check was found in `fail` state, the human confirmed on Codex's own dashboard that the review actually
finished, the PR head hadn't moved since the initial check, step 5 resolved the single matching failed run
as `databaseId 300` with baseline `attempt` 1, `@codex review` was posted, and `gh run rerun 300
-R "<owner>/<repo>"` was issued in step 7. Continuing now with step 8 (poll and report), polling that exact
run and comparing against the baseline `attempt` of 1.

Simulated tool calls, in order:

1. Bash: gh run view 300 -R "<owner>/<repo>" --json status,conclusion,attempt
   Result: {"status": "completed", "conclusion": "failure", "attempt": 1}
   → `attempt` (1) equals step 5's baseline `attempt` (1), not strictly greater than it. Per step 8, a
     `completed` result at the baseline `attempt` is always the stale pre-rerun state, regardless of
     conclusion — GitHub hasn't propagated the fresh rerun attempt yet. Not reported. Continue polling.

2. Bash: gh run view 300 -R "<owner>/<repo>" --json status,conclusion,attempt
   Result: {"status": "in_progress", "attempt": 2}
   → `attempt` has now incremented to 2, confirming the fresh rerun attempt has actually started, but
     `status` is not yet `completed`. Continue polling.

3. Bash: gh run view 300 -R "<owner>/<repo>" --json status,conclusion,attempt
   Result: {"status": "completed", "conclusion": "success", "attempt": 2}
   → `attempt` (2) is strictly greater than the baseline (1) and `status` is `completed`, so this
     `conclusion` genuinely reflects this retry's real outcome. Report success.

Final response to the user:

The retried "Await Codex review" check for PR #77 has passed. Run 300's fresh attempt (attempt 2)
finished with `status: completed`, `conclusion: success`. The first poll still returned the stale
pre-rerun result (`attempt` 1, `failure`) — since its `attempt` hadn't yet exceeded step 5's baseline of
1, it wasn't treated as this retry's outcome. The second poll showed `attempt` 2 as `in_progress`,
confirming the fresh rerun had actually started, and the third poll's `attempt` 2 `success` is the
genuine result of this retry. No further action needed — the check is green and the recovery is complete.
