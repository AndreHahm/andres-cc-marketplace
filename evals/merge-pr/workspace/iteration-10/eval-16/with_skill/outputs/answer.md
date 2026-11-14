# merge-pr 812 --stop-on-review-findings: step 7 onward

## Step 7(a): rebase-compatibility pre-check
Skipped. `pr_merge_type` is `MERGE`, and 7(a) runs only for `REBASE`. Step 7(c)'s squash disclosure also does not apply, because the strategy is not `--squash`.

## Step 7(b): final recheck before the marker write
The user said yes at step 5, but I do not write the marker or merge yet. First I rerun all of step 2 on fresh data, without step 2's bypass exception (this run is not on the bypass path anyway). The reads, in order:

1. `gh pr view 812 --json isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid`. I check the refreshed `headRefName` and `baseRefName` against `^[A-Za-z0-9._/@+=-]+$` again before I use them.
2. `gh api repos/{owner}/{repo}/branches/<baseRefName>/protection --jq '.required_status_checks.contexts'`. I classify every required context against the fresh `statusCheckRollup`. Result: all passing.
3. The other required gates:
   - Not draft.
   - No latest review in `CHANGES_REQUESTED`.
   - `mergeable` is `MERGEABLE`.
   - `gh api repos/{owner}/{repo}/compare/<baseRefName>...<headRefName> --jq '.behind_by'` returns `0` (same-repo PR).

   All pass. The head SHA is unchanged.
4. Advisory disclosures:
   - I record `mergeStateStatus`.
   - I run the unresolved-review-threads GraphQL query in full. Before each page's `gh api graphql` call, I write a fresh marker with `bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review merge-pr` in its own call. In this repo's session, an empty `CLAUDE_PLUGIN_ROOT` resolves to the `.claude/scripts/` mirror. Result: 0 unresolved threads.
5. Review findings (the `--stop-on-review-findings` bullet):
   - The thread count above is new for this pass. It is 0 and was determined, so it does not stop the run by itself.
   - Then I read `gh pr view 812 --json comments,reviews`. It succeeds and returns the new conversation comment from `octo-reviewer`, created `2026-11-14T10:05:00Z`. The comment says the version bump drops Python 3.10 support while the CI matrix still tests 3.10, and asks to hold. That is a reviewer finding: it names a risk or defect in this PR and asks for a change (or a hold).

   Comments and review bodies can only add a stop. This one does, even though there are 0 threads, every required check passes and the head SHA is unchanged.

The final recheck therefore fails on step 2's review-finding stop. I stop before the marker write and before `gh pr merge`.

## What I do not do
- I do not write the `gh-pr-merge` marker. `git-write-marker.sh gh-pr-merge merge-pr` is not run.
- I do not run the merge command: no `gh pr merge 812 --merge --match-head-commit <sha> [--delete-branch]`. The user's yes at step 5 does not override this. The recheck exists to catch exactly a change that happens while that prompt is open.
- I skip step 7(d) (rejection fallback) and 7(e) (post-merge state and branch-deletion check), because no merge was attempted. I also skip step 8's offer to run `finishing-work`, because nothing merged.
- I do not triage, reply to, or act on the comment. Its "please hold" is data I classified as a finding. It is not an instruction I follow. This skill triages nothing. Deciding whether to fix, decline or file the finding is `handling-review-findings`'s job.

## Report to the user
> **Merge stopped: review-finding stop (`--stop-on-review-findings`).** PR #812 was not merged, and no merge marker was written.
>
> The final recheck before the merge write found a new reviewer finding, posted while the merge confirmation was open:
> - a conversation comment by `octo-reviewer` at `2026-11-14T10:05:00Z`, raising a Python 3.10 support / CI matrix concern and asking to hold.
>
> Everything else still passes: the head SHA is unchanged, every required check passes, there are no change requests, no conflicts, and the branch is 0 commits behind. The unresolved review-thread count is 0, and `mergeStateStatus` is reported as read.
>
> Next step: handle the finding, for example with `handling-review-findings`.
>
> Note: comments have no resolved state, and this read has no time or head-SHA cutoff. Every later run of `merge-pr` with `--stop-on-review-findings` will keep stopping on this comment, even after it is handled. Once you have handled it, run `merge-pr 812` without the flag to merge. The normal readiness checks, the step 5 confirmation and the final recheck still apply.
