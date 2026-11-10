# PR #612, finding 9001: steps before push

## Ordered steps

1. **Workflow step 1, re-check live state.** Re-fetch `gh pr view` (headRefOid, url, state), `gh pr checks`, and `git-review-api.py list-comments`. Confirm HEAD equals headRefOid and the repo identity matches the PR's base repository. The handoff line "verified: smoke_test.py 6/6, targeted rulebook re-check, mirrors identical" is prior-session evidence and does not stand in for any step below.
2. **4a, verifiers on the fix's own diff.** Already run this session, exit 0, nothing ungraded (per the scenario). The user's "Run" answer covers this run, so no new question. The launcher identity check (4a step 3) applies only if `CLAUDE_PLUGIN_ROOT` is empty.
3. **4b, sibling sweep.** Not yet run. Grep the rest of the same reference file for the wording anti-pattern that finding 9001 names, and fix any identical instance.
4. **4c, fix-diff review.** Not yet run. The fix is already committed (abc1234), so use `python3 -I "${CLAUDE_PLUGIN_ROOT}"/scripts/git-review-fix-diff.py --base <parent of abc1234>` and read the diff. A new defect in the touched file is blocking.
5. **4d, budget.** The pass above is iteration 1. If 4b or 4c finds a blocking item, fix it, re-run 4a-4c once (iteration 2), and stop if that still blocks. If neither finds anything, no iteration 2 is needed.
6. **Push-destination check.** `git-review-api.py push-destinations` must exit 0, print at least one line, and every line must equal the PR's `headRepositoryOwner/headRepository` (from `gh pr view`). Any mismatch stops the push.
7. **Push.** Push through `Skill(commit)` with `--push`, never a raw `git push`. Confirm the push actually landed on the remote before any reply.
8. **4e, ledger.** After the fix is settled, `git-review-ledger.py record --pr 612 --finding <9001 comment id> --disposition fixed` with a note the agent writes itself. Promotion waits until step 8 of the Workflow ends with no trigger posted, so do not promote now.
9. **Reply, then resolve.** Immediately before each call, write a fresh `gh-pr-review-wrapper` marker, then `git-review-api.py reply` with the SHA and verification line, then `resolve` on thread 9001 only after the push is confirmed. Never resolve an unverified or unpushed fix.

## Verification line for the thread 9001 reply

Under the stated assumption (only 4a re-run this session), the line I would post, once the push has landed:

> Verified: the verifiers re-ran on this fix's own diff (commit abc1234, against its base branch) and exited 0 with no ungraded paths. Pushed to `<owner>/<repo>` on `<branch>`.

Caveats:
- This line claims only 4a. It is accurate only under that assumption. Steps 3 and 4 (4b and 4c) have not run, and the reply must not be posted until they have, or it must say they were skipped.
- Do not cite the handoff's smoke_test 6/6 or rulebook re-check as verification for this push.
- Do not write "verifiers passed" for any path listed as ungraded, and do not claim a clean result if the launcher identity check differed.
- Do not post the reply or resolve the thread if the push has not landed.
