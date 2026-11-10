# PR #612, thread 9001: reply and follow-up (simulated, nothing executed)

## Preconditions (all satisfied per the scenario)

- Fix committed as `abc1234` in an earlier session (resumed fix). Per `references/fix-self-review.md`, a resumed
  fix still gets 4a-4d and 4e's `record` in this session; done: 4a exit 0 with nothing `ungraded`, 4b clean,
  4c clean (committed fix, so 4c reviewed the diff from `git-review-fix-diff.py --base <commit before abc1234>`),
  no second iteration needed (4d).
- Verification ran this session: `smoke_test.py` 6/6.
- Push-destination check passed and the push landed, so reply-with-SHA is allowed (SKILL.md step 4).

## Which verification claims the reply may make

The reply's verification line names only checks run **in this session** against the pushed fix. The handoff's
"targeted rulebook re-check" and "mirrors identical" were NOT re-run in this session, so they are either
re-run first or labeled as an earlier session's result. I did not re-run them, so the reply labels them as
carried over. The handoff's `smoke_test.py 6/6` is not cited from the handoff: it was re-run here (6/6), and
the reply cites this session's run.

## Exact reply text posted to thread 9001

> Fixed in abc1234.
>
> Verification (this session, against abc1234): `smoke_test.py` 6/6; fix self-review: the Phase 2 verifier
> re-run on the fix's diff exited 0 with no ungraded paths, the sibling-pattern sweep found no other instance,
> and a review of the committed fix diff found no new defect.
>
> From an earlier session, not re-run here: a targeted rulebook re-check and a check that the `.claude/`
> mirror is identical.

(If the 4a JSON's `checked` list had been empty, the verifier clause would instead say that no changed file
was a covered component, never "verifiers passed". The scenario reports exit 0 with nothing ungraded, so the
clause above is phrased as "exited 0", not as a CI verdict.)

## What I do, in order

1. Immediately before the reply, in its own Bash call: write a fresh marker
   `bash "$PWD/.claude/scripts/git-write-marker.sh" gh-pr-review-wrapper handling-review-findings`
   (mirror root substituted because `CLAUDE_PLUGIN_ROOT` is empty in this repo's sessions), then post the
   reply above with `git-review-api.py reply` (body from a scratchpad file) on comment 9001.
2. Confirm the reply posted. Only then resolve: fresh marker, `git-review-api.py threads` to map comment 9001
   to its review-thread node id; fresh marker again (single-use, 60 s), `git-review-api.py resolve` on that
   thread id.
3. Record the outcome in the ledger (4e):
   `python3 "$PWD/.claude/scripts/git-review-ledger.py" record --pr 612 --finding '9001' --disposition fixed --note "Wording fix in abc1234; smoke test re-run this session"`
   (note written by me, not copied from the comment).
4. Step 7: report plainly to the user: finding 9001 (Minor) fixed in abc1234, replied and resolved; nothing
   filed or declined; also say that the rulebook re-check and mirror check came from the handoff and were not
   re-run this session.
5. Step 8: re-fetch the comment list, count triggered cycles (8a). If the budget allows another cycle, ask the
   reviewer/mode `AskUserQuestion` (or reuse this conversation's earlier answer), validate candidates (8c),
   re-check live PR state (8d) and post the trigger. If step 8 ends with no trigger posted, run
   `git-review-ledger.py promote --pr 612` and commit `.claude/review-outcomes/pr-612.json` via
   `Skill(commit) --push` as a records-only commit (it changes the head SHA, so CI runs again).
6. Never merge or imply mergeability; that is `merge-pr`'s call.
