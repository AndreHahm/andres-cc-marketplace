# Decision: PR #611, round 1, self-review budget exhausted

Basis: SKILL.md Workflow step 4 and `references/fix-self-review.md` 4d (budget) and 4e (ledger).

## Third iteration?
No. The budget is at most 2 self-review iterations per finding. Iteration 1 found a blocking item, which I
fixed. Iteration 2 still shows a different blocking finding on a touched line. The skill says to stop and
not loop further.

## Push, reply, resolve?
- No push. The skill says a blocking finding on a touched line stops the push. I do not run the
  push-destination check or `Skill(commit) --push` either.
- No reply to the finding's thread.
- No resolve. The fix is not verified clean, so the thread is not handled.
- I post no review-thread comment about this finding.

## What I tell the user
I report plainly, then ask via `AskUserQuestion`:
- The finding (comment id, path) was fixed locally.
- Self-review iteration 1 found a blocking item on a touched line, which I fixed.
- Iteration 2 found a different blocking finding on a touched line (describe it: path, line, defect).
- The 2-iteration budget is spent, so I stopped. Nothing was pushed, replied to or resolved.
- Options for the user:
  1. Mark the finding `accepted`: they accept the remaining issue.
  2. Leave the finding open and do not push the fix.
  3. Other (e.g. they direct a specific manual fix).
- If the remaining blocker is Critical/Major, I do not silently defer it. That needs an explicit
  risk-acceptance question before any `merge-pr` discussion.

## Ledger disposition and thread status
- Ledger: no disposition is recorded yet, because the finding is not settled. When the user answers, I
  record exactly what they direct:
  - If they choose accepted:
    `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" record --pr 611 --finding <comment-id> --disposition accepted --path P --line L --rule R --note "<remaining blocker, user-accepted>"`
  - If they choose to leave it open: nothing is recorded as fixed, and never `fixed`.
- Not `fixed`: the fix did not pass self-review and was never pushed.
- Not `declined`, `false_positive` or `ignored`: none of these applies.
- Thread status: unresolved and unreplied. It stays open in round 1 until the user directs otherwise.
- Corrupt-ledger caveat: if the ledger script exits 2, I report it and do not continue without a record.
