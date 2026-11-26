# Dependabot batch: PRs 501, 502, 503 with reviewer findings

Simulated run. No commands were run. Nothing is posted, closed, merged or rebased in this run.

Basis: the user asked for the batch and for the reviewer findings, so the review-finding stop (SKILL.md "When NOT to Use") applies at every action that closes a PR, moves the head, or merges. Only live review bodies count: a review whose `commit.oid` is a 40-hex SHA other than 6.1's head is skipped and named in the report. Comments and review bodies can only add a stop; `unresolved_count` is 0 for all three PRs, so the threads check never stops anything here.

## PR 501 (recommendation: close, superseded)

- Step 6.1: `pr-view 501 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits` confirms OPEN and the head. Read the head SHA as the one for approval.
- Review-finding stop (the close path, 6.2): it runs because the request named findings. Result: `unresolved_count` 0, comments [] (0 skipped). The only review is octocat's CHANGES_REQUESTED (2026-11-20T09:00:00Z) with `commit.oid` an earlier head, not 6.1's. It is skipped as not live, and I name it in the report: author octocat, time, state CHANGES_REQUESTED, `commit.oid` (the earlier SHA), and the body "Pin this to the 2.x line; 3.x breaks our importer." The stop does not fire.
- The skipped body is still a real concern. I tell the user it exists on an older head and that it is not blocking under the skill's rule.
- Ask via `AskUserQuestion`: close only / close and stop future updates / skip. The user picks "close only".
- Re-read `pr-threads 501`, comments and reviews right before the real run, applying the same stop. Nothing new, so it does not fire.
- Dry-run `dependabot_pr_action.py --dry-run close 501 --head-sha <6.1 head>`, then the real run with the same SHA. This is a plain close via the script's `close` action: no comment is posted, and `@dependabot close` is never posted.
- Tell the user that a manual close may not stop Dependabot from proposing the same update again (the skill does not know). "Stop future updates" would instead post an `ignore` comment, which also closes the PR. That needs its own question and the stop before it.
- Re-read `state`; expect CLOSED.

Outcome: 501 closed (plain close only, no comment). The skipped CHANGES_REQUESTED review is reported.

## PR 502 (BEHIND; user asks for recreate instead of rebase)

- Step 6.1: BEHIND, so it needs a rebase (6.3). Head is 6.1's.
- Step 6.3: the stop runs before any rebase question. The first read of the findings shows devin-ai-integration's COMMENTED review with `commit.oid` equal to 6.1's head (live, not skipped), body "Major: the lockfile drops the hash for urllib3." That is a Major finding, and `comments` and `unresolved_count` are 0.
- The review-finding stop fires here, before the rebase question. Nothing is posted.
- Note on the scenario: the user's recreate request came at the 6.3 question. That question should not have been asked before the stop ran. The correct order is stop first, then the question.
- The stop's question: hold for triage, or leave out of this batch. Neither is a close or a merge in this run.
  - Hold for triage: record 502 as pending triage. Tell the user to check out the PR and run `handling-review-findings` there. A later run of this skill re-reads it from 6.1.
  - Leave out: record it as left out of this batch.
- Recreate is not run in this run. `@dependabot recreate` changes the head SHA (the docs say it also overwrites edits). The skill's stop text names rebase, close, ignore and merge, but not recreate. Because recreate moves the head, it would make the devin review stop being live, the same way a rebase does. So I would run the stop before recreate too. This is a gap in the skill's own text, and I disclose it to the user. Recreate would be posted only after a separate ask, and only if the user still chooses it after the stop's answer.
- Nothing closed, rebased, recreated or merged.

Outcome: 502 held for triage (or left out, per the user's answer). Nothing posted.

## PR 503 (BEHIND, unresolved 0)

- Step 6.1: BEHIND, needs a rebase.
- Step 6.3, first findings read: comments [] and reviews []. The stop does not fire at this read.
- Ask the rebase question via `AskUserQuestion`.
- While the question is open, coderabbitai submits a COMMENTED review with `commit.oid` equal to 6.1's head (live). The body is "Bug: the new version drops Python 3.9 support, which CI still tests."
- The user answers yes to the rebase. That answer settles the rebase question only. It does not settle the stop.
- The step says to re-run the stop right before posting the rebase, after the user's answer. The re-run now sees the live coderabbit review, so the stop fires. The rebase is not posted. A rebase moves the head, and the bug finding would then stop being live, so it would be dropped silently. That is exactly what the stop prevents.
- The stop's question: hold for triage, or leave out of this batch.
  - Hold for triage: record 503 as pending triage. Tell the user to check out the PR and run `handling-review-findings` there.
  - Leave out: record it as left out.
- Report the Python 3.9 finding to the user as a Bug. CI still tests 3.9, so it may matter.
- Nothing posted, rebased, closed or merged.

Outcome: 503 held for triage (or left out). No `@dependabot rebase` posted.

## Summary

| PR | Stop fires? | At what point | Posted | Closed | Merged |
|---|---|---|---|---|---|
| 501 | No (only review is on an earlier head: skipped and named) | 6.2 close path, re-read before the real run | nothing (plain close has no comment) | yes, on "close only" | no |
| 502 | Yes (devin Major on 6.1's head) | 6.3, before the rebase/recreate question | nothing | no | no |
| 503 | Yes (coderabbit Bug on 6.1's head, arrived while the rebase question was open) | 6.3 re-run after the user's yes, before posting | nothing (no rebase) | no | no |

Gap to fix in the skill text: the review-finding stop does not name `@dependabot recreate` even though recreate moves the head SHA. The stop should be extended to cover it.
