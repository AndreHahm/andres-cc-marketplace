# PR #612, finding 9001: pre-push self-review and reply line

## Steps to run before pushing (in order)

1. **4a, verifier re-run: already done this session.** The user answered "Run", which covers every fix in this run, so no new question. Exit 0 with nothing ungraded means no re-run is needed for this fix. A new edit made in 4b or 4c would need 4a run again.
2. **4b, sibling sweep: run now.** Grep the rest of the same reference file for the anti-pattern signature finding 9001 names. Fix any identical instance a few lines away.
3. **4c, fix-diff review: run now.** The fix is already committed locally as `abc1234`, so use `python3 -I "${CLAUDE_PLUGIN_ROOT}"/scripts/git-review-fix-diff.py --base <full id of abc1234's parent>`. Read the changed files. If the script exits 2, read each changed file by hand rather than treating the result as "no change".
4. **4d, budget: iteration 1.** If 4b or 4c finds a blocking defect, fix it and re-run 4a through 4c once (iteration 2). If iteration 2 still shows a blocking finding, stop: do not push, reply or resolve, and report to the user. If 4b and 4c are clean, no second iteration is needed.
5. **4e, ledger: record once settled, before the push.** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" record --pr 612 --finding 9001 --disposition fixed --note "..."`. The note is written by me, not copied from the comment. Promotion (`promote`) runs only if step 8 ends with no trigger posted. In that case the promoted file is staged with the final fix commit.

Then `Skill(commit) --push`, the push-destination check, and the reply/resolve on thread 9001, in the order the workflow states.

## Handoff claims not covered by 4a-4e

The handoff's "smoke_test.py 6/6, targeted rulebook re-check, mirrors identical" are results from an earlier session. The 4a-4e steps do not re-run them. They are not "run this session", so the reply must not present them as current. Either re-run `scripts/smoke_test.py` (cheap) and the mirror diff first, or label them as an earlier session's results.

## Exact verification line for the thread 9001 reply (post after the push lands)

> Verified this session: verifier self-review (4a) exit 0, no blocking findings, no ungraded paths, at base `<parent sha of abc1234>` against target branch `<base>`. Sibling sweep (4b) and fix-diff review (4c) found no further instance of the pattern in `<file>`. Carried over from the handoff, not re-run this session: smoke_test.py 6/6, targeted rulebook re-check, mirrors identical (earlier session's results).

This line is conditional. Use it only after 4b and 4c are actually run and come back clean. If either finds a defect, the fix is not yet ready to push, and the line changes or the reply is not posted.
