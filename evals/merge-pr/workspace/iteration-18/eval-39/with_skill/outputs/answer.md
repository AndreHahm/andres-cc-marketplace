Step 7(c), run before 7(b) writes its marker. `pr_merge_type` is `SQUASH`, so 7(a) does not apply.

Command (one unpaginated request; its count is not capped):

```
gh api -X GET repos/octo/widgets/pulls/941 --jq .commits
```

I do not use `gh pr view --json commits` (at most 100) or count lines of the commits endpoint (at most 250).

- Here (exit 0, prints `137`): "Squashing collapses 137 commits into one on the base branch; individual fix-round/review-commit granularity is lost there. That is a real tradeoff against what REBASE/MERGE preserve."
- Had it printed `312`: the same disclosure with "312 commits". The number is taken as is.
- Had it exited 1 with nothing usable: "The number of commits that will collapse into one could not be determined. Individual fix-round/review-commit granularity is still lost on the base branch." No number is guessed, none is reported as 0, and no other count command replaces it. The skill only requires saying this; it does not make it a stop.

Then 7(b): after the final full step-2 recheck passes and this disclosure is made, write the `gh-pr-merge` marker and, as the very next call, run `gh pr merge 941 --squash --match-head-commit <rechecked headRefOid>` (plus `--delete-branch` if configured). Then 7(e) checks the PR state.
