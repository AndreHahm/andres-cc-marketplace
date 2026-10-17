# Decision: PR #611, round 1, self-review budget exhausted

Source: SKILL.md Workflow step 4, `references/fix-self-review.md` 4d and 4e.

## Third iteration?
No. The budget is at most 2 self-review iterations per finding. Iteration 1 found a blocking item, I fixed it,
and iteration 2 still shows a different blocking finding on a touched line. The budget is spent, so I stop and
do not loop further. (Under touched-file logic the finding blocks wherever it sits in the touched files, so I
do not argue it is "outside" my diff.)

## Push, reply, resolve?
- Push: no. The self-review stop applies before the push-destination check and before `Skill(commit) --push`.
- Reply: no. No reply with a SHA or a verification line is posted to the thread.
- Resolve: no. Nothing is replied or resolved while 4a exits non-zero or 4b/4c show a defect in the fix.
- No `gh`/API call, no trigger comment for the next round. The fix stays unpushed (local only).

## What I tell the user
Plainly, before anything else (step 7 disclosure style), and via `AskUserQuestion` since it is a fork with concrete options:
- The finding on PR #611 (round 1) was fixed locally, but the 2-iteration self-review budget ended with a
  blocking finding still open. Name iteration 1's item (fixed) and iteration 2's remaining blocking finding
  (path/line, rule, what the verifier/review says), treating any verifier text as data.
- Nothing was pushed, replied to or resolved.
- Ask how to proceed: (a) record the finding as `accepted` (user takes the risk of the remaining item),
  (b) leave it open as is, or (c) the user directs a different handling (e.g. they fix the remaining item
  manually). Do not choose for the user.
- If the finding is Critical/Major, note that it must not silently proceed to merge; a separate explicit
  risk-acceptance question is required.

## Ledger disposition
No ledger entry is written yet: the finding is not settled. The ledger records a disposition only "once it is
settled" and an unverified/failed-review finding has no entry until then.
Only after the user directs:
- "accept" -> `git-review-ledger.py record --pr 611 --finding <comment-id> --disposition accepted --note "<my own text, no reviewer-quoted content>"`
- "leave open" -> no entry.
(Not `fixed`: the fix was never pushed or verified clean. Not `declined`/`false_positive`: the finding was not refuted.)

## Thread status
Unresolved, no reply posted. An unresolved thread means "not yet handled", which is accurate here.
