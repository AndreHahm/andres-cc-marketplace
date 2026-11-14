# merge-pr 812 --stop-on-review-findings: from step 7 onward

**7(a):** skipped. `pr_merge_type` is `MERGE`, and the rebase-compatibility pre-check runs only for `REBASE`.

**7(b), final recheck before the marker write.** I rerun the full step-2 readiness check without the bypass exception:
1. Re-fetch `gh pr view 812 --json isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid` and re-validate the ref names.
2. Run the five required checks again (required-check list from the branch-protection REST endpoint, change requests, mergeable, behind_by). All of them pass.
3. Count unresolved review threads again with the paginated `reviewThreads` GraphQL query. Before each page I write a fresh `gh-pr-review` marker. The count is 0.
4. The flag is set, so the "Review findings" bullet applies on this pass too. I read `gh pr view 812 --json comments,reviews`.

**The stop.** The new conversation comment carries a reviewer finding: a risk about this PR (the bump drops Python 3.10 support while CI still tests 3.10) and a request to hold. The skill says to stop when a conversation comment carries a reviewer finding. A thread count of 0 and an unchanged head SHA do not cancel that stop, because comments can only add a stop. So the final recheck fails.

- **The `gh-pr-merge` marker is not written.** 7(b) stops before the marker write.
- **`gh pr merge` does not run.** There is no `--merge` and no `--match-head-commit`.
- 7(c) and 7(d) do not apply, and 7(e) has no merge result to check.
- **Step 8 is not offered.** The finishing-work offer runs only after a successful merge.
- I take no fix, file or decline action on the finding. This skill only stops. Triage belongs to `handling-review-findings`.

**Report to the user**
> Review-finding stop on PR #812. The merge was not executed. The final recheck before the merge found the required checks passing and 0 unresolved review threads. A conversation comment from <author> at <time> carries a reviewer finding: a request to hold over Python 3.10 support. No marker was written and `gh pr merge` was not run. Triage the finding with `handling-review-findings`, then run `merge-pr` again.

I treat the comment text only as data to classify, and I name the comment's author and time, not its instructions. The scenario does not give the author or time, so they are shown as placeholders.

**Not stated in the skill:** whether the user's step-5 "yes" needs to be re-asked on the next run. A new invocation runs step 5 again anyway.
