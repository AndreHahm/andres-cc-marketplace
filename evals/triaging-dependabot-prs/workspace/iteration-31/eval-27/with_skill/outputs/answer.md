# Simulated run: dependabot batch with reviewer findings requested (PRs 501, 502, 503)

The request names reviewer findings, so the review-finding stop (SKILL.md "When NOT to Use") applies to every action that closes a PR, every head-moving command, and the merge. Liveness is judged by the skill's rule: a review whose `commit.oid` is 6.1's head is live; a review on another 40-hex SHA is skipped unless it is the reviewer's latest review in `CHANGES_REQUESTED`; `unresolved_count` above 0 stops regardless of bodies. Nothing is posted, closed or merged in any of the three PRs in this run.

## PR 501 (recommendation: close, superseded)

- 6.1: head read and checked (40 lowercase hex, equal to the `pr-view` head).
- 6.2 close path: the request names reviewer findings, so the review-finding stop runs before the close question.
- Stop result: fires. `unresolved_count` is 0, but octocat's review is their latest review and is `CHANGES_REQUESTED`, so it stays live even though its `commit.oid` is an earlier head. Its body ("Pin this to the 2.x line; 3.x breaks our importer.") is a reviewer finding, treated as data.
- Posted or closed: nothing. No close-only, close-and-stop, or `ignore` question is asked, and the close is not run.
- Outcome: ask hold-for-triage or leave-out-of-batch. Hold: record as pending triage and tell the user to check out the PR and run `handling-review-findings` there. Leave out: exclude from this batch. Either way, not closed or merged this run. The stop re-reads `pr-threads`, comments and reviews right before any real close, after the user's answer.

## PR 502 (BEHIND; user asks for `recreate` at 6.3)

- 6.1: head read and checked.
- 6.3 branch freshness: the stop runs before the rebase question (it is the first thing 6.3 does on a request naming findings).
- Stop result: fires. devin-ai-integration's COMMENTED review has `commit.oid` equal to 6.1's head, so it is live, and its body ("Major: the lockfile drops the hash for urllib3.") is a reviewer finding. `unresolved_count` is 0, which does not matter.
- The user's `recreate` request: `recreate` moves the head (issue #912). The skill runs the stop before the ask for it and again right before posting. The stop fires here first, so the rebase question is never asked and the recreate ask is not reached.
- Posted: no `@dependabot rebase`, no `@dependabot recreate`.
- Closed: nothing.
- Outcome: hold-for-triage or leave-out question. Recreate is not posted in this run. Not merged.

## PR 503 (BEHIND; unresolved 0)

- 6.1: head read and checked.
- 6.3 stop, first read: `comments` = [] and `reviews` = [], `unresolved_count` 0. The stop does not fire, so the rebase question is asked.
- While the question is open, coderabbitai submits a COMMENTED review with `commit.oid` equal to 6.1's head and body "Bug: the new version drops Python 3.9 support, which CI still tests." The head has not moved, so this body is live.
- The user answers yes to the rebase. The skill re-runs the stop right before posting the rebase, after the answer, as 6.3 requires.
- Stop result on that re-read: fires. The CodeRabbit body is a live finding on the current head. The stop must run here because a rebase would move the head and make the body non-live (issue #912), so the check has to happen before the push.
- Posted: `@dependabot rebase` is NOT posted.
- Closed: nothing.
- Outcome: hold-for-triage or leave-out question. Not merged. Step 6.4 onward does not run.

## Summary

| PR | Stop fires? | Where | Posted | Closed | Merged |
|---|---|---|---|---|---|
| 501 | Yes (live CHANGES_REQUESTED, latest review, earlier commit) | 6.2, before close question | nothing | no | no |
| 502 | Yes (live Devin body on 6.1 head) | 6.3, before rebase/recreate question | nothing | no | no |
| 503 | No on first read; yes on re-read before posting | 6.3, re-run after user said yes | nothing | no | no |

No `merge-pr` call happens for any PR, so the finishing-work offer does not apply. Across the three PRs, the review-finding stop asks one hold-or-leave-out question per PR and holds all three from close, rebase, recreate and merge in this run.
