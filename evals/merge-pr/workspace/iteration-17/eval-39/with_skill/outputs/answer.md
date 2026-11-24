# Step 7(c): squash disclosure for PR 941

`pr_merge_type` is already `SQUASH`, so 7(a) does not apply and the disclosure comes in 7(b), after the final readiness recheck and before the marker and the merge command.

1. Before 7(b) writes its marker (the next Bash call consumes a marker), I run exactly:

   ```
   gh api repos/octo/widgets/pulls/941/commits --paginate --jq '.[].sha' | wc -l
   ```

   Not `gh pr view --json commits`, which returns at most 100 and would report 100 here.
2. It returns `137`. I disclose: "Squashing collapses 137 commits into one; the individual fix-round/review-commit granularity is lost on the base branch." I state it even though squash is the configured strategy.
3. Then I write the `gh-pr-merge` marker and run `gh pr merge 941 --squash --match-head-commit <verified headRefOid>`, plus `--delete-branch` if `merge_auto_delete_branch` is true.

**Had it returned 250:** the endpoint returns at most 250 commits, so the true number may be higher. I would say: "**At least 250** commits collapse into one; the individual fix-round/review-commit granularity is lost on the base branch."

(On `0` or an error from `gh`, I would say the number could not be determined.)
