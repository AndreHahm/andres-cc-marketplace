Context: steps 1-6 of `codex-review-recovery` have already completed for PR #77 — the `Await Codex review`
check was found in `fail` state, the human confirmed on Codex's own dashboard that the review actually
finished, the PR head hadn't moved since the initial check, `@codex review` was posted, and the single
matching failed run (`databaseId 300`) was re-run via `gh run rerun 300 -R "<owner>/<repo>"`. Continuing
now with step 7 (poll and report), polling that exact run.

Simulated tool calls, in order:

1. Bash: gh run view 300 -R "<owner>/<repo>" --json status,conclusion
   Result: {"status": "completed", "conclusion": "failure"}
   → No `queued`/`in_progress` status has been observed on any earlier poll yet, so per step 7 this
     `completed`/`failure` result is treated as the stale pre-rerun state (GitHub hasn't propagated the
     fresh rerun attempt yet), not as this retry's real outcome. Not reported. Continue polling.

2. Bash: gh run view 300 -R "<owner>/<repo>" --json status,conclusion
   Result: {"status": "in_progress"}
   → This confirms the fresh rerun attempt has actually started. Continue polling — the next `completed`
     result will be genuine.

3. Bash: gh run view 300 -R "<owner>/<repo>" --json status,conclusion
   Result: {"status": "completed", "conclusion": "success"}
   → `in_progress` was already observed on the prior poll, so this `completed`/`success` result is genuine
     — it reflects this retry's real outcome. Report success.

Final response to the user:

The retried "Await Codex review" check for PR #77 has passed. Run 300 finished with `status: completed`,
`conclusion: success` — the first poll still showed the old pre-rerun `failure` result (GitHub hadn't yet
propagated the fresh attempt), the second poll showed `in_progress` confirming the rerun had actually
started, and the third poll's `success` is the genuine outcome of this retry. No further action needed —
the check is green and the recovery is complete.
