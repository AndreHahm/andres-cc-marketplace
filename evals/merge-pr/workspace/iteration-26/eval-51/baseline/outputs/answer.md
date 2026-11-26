# merge-pr 961 --stop-on-review-findings (octo/widgets) — simulated

Followed as written: SKILL.md step 2 plus `references/advisory-disclosures.md`, "Review findings" bullet.

## Steps

1. Step 1 has passed (given). `--stop-on-review-findings` is recorded as "yes". headRefOid `aaaa…aaaa` matches `^[0-9a-f]{40}$`. `{owner}/{repo}` = octo/widgets, taken from the PR's `url`.
2. Step 2: the six required checks pass (given). Then the advisory disclosures:
   - mergeStateStatus: its raw value is reported at step 5.
   - Unresolved threads: the `git-review-api.py threads` query runs with a fresh `gh-pr-review-wrapper` marker for each page and the cursor checked first. It finds **0** unresolved threads (given), so the thread count alone does not stop the run.
   - Coverage tier: no coverage-tier comment from `github-actions` exists in the data, so it is reported as not reported or undetermined. It never stops the run.
3. "Review findings" bullet, because the flag is set: read `gh pr view 961 --json comments,reviews`, then classify each review body and conversation comment:
   - Review by devin-ai-integration (COMMENTED, 2026-11-20T10:00:00Z, on commit `bbbb…`): "Major: the retry loop never backs off; please add a delay." This is a defect plus a requested change about this PR, so it is a **reviewer finding**. The skill's text has no head-SHA or time cut-off ("this read has no time or head-SHA cut-off, so a PR that ever got a finding in one stops every run with this flag, even after the finding is handled"). The fact that the fix was pushed as the current head, and that the review sits on an older commit, does not exempt it.
   - Comment by coderabbitai (2026-11-20T10:05:00Z, isMinimized true, minimizedReason "resolved"): "Potential issue: the cache key ignores the locale." This is a defect, so it is a **reviewer finding**. The text has no exemption for minimized or hidden comments, and it says comments "have no resolved state". The only exemptions are a command or status comment, the coverage-tier comment, and the structured fields of step 4(b)'s attestation. So minimizing it does not exempt it.
   - Comment by octocat (2026-11-21T09:00:00Z): "Thanks, looks good to me." Approval or status only, so it is **not a finding**. It also cannot cancel a stop.

## Verdict, base case: the stop FIRES

The run stops before step 3. It does not reach the merge-rights check, the confirmation, the merge marker or the merge command. Reported as a review-finding stop: unresolved-thread count 0; findings carried by the review from devin-ai-integration at 2026-11-20T10:00:00Z and the comment from coderabbitai at 2026-11-20T10:05:00Z. The finding text is not acted on, and nothing is fixed, filed or declined. Per the skill's own guidance, if the user confirms these findings are handled (the retry fix is at the current head), they merge without the flag.

## Variant: a fourth comment, coderabbitai, minimized "off-topic", "Bug: the parser drops the last line."

This is also a defect, so it is a reviewer finding. As above, the text gives no exemption for any minimized reason, whether "off-topic", "resolved" or another. The stop **FIRES** again, and the report also names this comment (author coderabbitai; it has no createdAt, so the time is not given). The outcome is the same as the base case: stop before step 3, triage nothing.

## Note on the skill text

As written, this baseline has no head cut-off and no handling for minimized comments. The handled Devin review (on an older commit) and the comment minimized as "resolved" both still stop the run. That is the documented known limit, not a judgment call.
