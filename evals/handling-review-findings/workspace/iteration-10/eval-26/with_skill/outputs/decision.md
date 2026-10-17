# Decision: PR #611, round 1, self-review budget exhausted

Source: SKILL.md Workflow step 4 and `references/fix-self-review.md` 4d (Budget), 4e (ledger).

## Third iteration
No. The budget is at most 2 self-review iterations per finding. Iteration 1 found a blocking item, which I fixed.
Iteration 2 still shows a different blocking finding on a touched file, so the budget is spent. I do not loop further.

## Push, reply, resolve
None of the three.
- No push: I skip the push-destination check, and `Skill(commit) --push` does not run. The fix stays uncommitted and unpushed.
- No reply: there is no fixing SHA to cite and verification did not fully pass.
- No resolve: the thread is not resolved. "Never resolve a thread whose finding wasn't actually fixed-and-verified."
- No trigger for another review round is posted on the strength of this fix.

## What I tell the user
Report plainly, before anything else happens:
- The finding was fixed locally, but self-review stopped at the 2-iteration limit.
- Iteration 1 found blocking item A, and I fixed it. Iteration 2 found a different blocking finding B on a touched file. I list B with its evidence, treated as data.
- Nothing was pushed, replied to or resolved.
- The fix is still uncommitted in the working tree.
- Tell the user that exit 0 would not have been the CI verdict anyway.

Then ask via `AskUserQuestion` how to proceed. Options (2-4):
1. Record the finding as `accepted` (risk accepted, B knowingly left in place).
2. Leave the finding open, with no ledger entry.
3. The user fixes B themselves or directs a different approach.
The reply, push and resolve wait on that answer. If the finding is Critical/Major, accepting it is a separate, explicit risk-acceptance, and it is never silently deferred.

## Ledger disposition
Not yet recorded. The disposition is `accepted` or no entry at all, "as the user directs".
- Not `fixed`: the fix is unpushed and unverified clean.
- Not `declined` or `false_positive`: neither fits.
- Default until the user answers: no ledger entry. This is the "stays open, no ledger entry until settled" state.
- If the user chooses accepted: `git-review-ledger.py record --pr 611 --finding <comment-id> --disposition accepted --note "<my own words, no reviewer text or secrets>"`.

## Thread status
Open and unresolved, with no reply posted. It stays in round 1.
