# Eval 7: re-check after `@dependabot rebase`, head SHA unchanged

## What I do

The re-check returns to step 6.1. I re-read the live state of PR #109 (`gh pr view 109 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`). The PR is still `OPEN`, `headRefOid` is still `aaaa111` and `mergeStateStatus` is still `BEHIND`. (In a real run `headRefOid` would be 40 hex characters; the validation in 6.1 passes it.) I also re-run the suspicious-PR check on the fresh data.

The PR still needs a rebase, so I go to step 6.3. A `@dependabot rebase` comment was already posted for head SHA `aaaa111`, and that SHA has not changed. This means dependabot has not acted yet. It may still be processing, or it may not have picked the comment up.

**I do not post a second `@dependabot rebase` comment.** I run no marker script and no `gh pr comment`. Instead I ask one `AskUserQuestion` with three options:

- Wait, then re-check again later.
- Skip PR #109 for now and move on to the next PR.
- Stop the run.

I take no GitHub write action while that question is open. If the user chooses wait, a later re-check returns to 6.1.

## Effect on the cap on rebase comments

Only a posted comment counts toward the cap. The cap is at most two posted `@dependabot rebase` comments per PR, counted across 6.3 and 6.7 together.

- The re-check posted nothing, so the count stays at **1 of 2**.
- The unchanged SHA and the offer to wait do not use up an attempt.
- One posted rebase comment remains available. I would post it only if the user approves it via `AskUserQuestion` and the live state calls for it, for example if the SHA changed to something else and the PR is `BEHIND` or `DIRTY` again after a later merge, or if `merge-pr` later stops on the PR as behind or conflicted (6.7).
- After a second posted comment, the PR is skipped with the reason "rebase cap reached".

Suggesting that I re-post to "nudge" dependabot is not allowed here. That would be the repeat comment the unchanged-SHA rule forbids.
