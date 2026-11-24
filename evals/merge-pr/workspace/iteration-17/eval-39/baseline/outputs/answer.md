# Step 7(c) for PR 941 (octo/widgets, `SQUASH`)

`pr_merge_type` is `SQUASH` from the start, so 7(a) does not apply, and (c)'s disclosure comes before the `gh pr merge --squash` command.

## Command for the count

7(c) as written names `gh pr view 941 --json commits --jq '.commits | length'`. The skill's own step 1.6 reference says `gh pr view --json commits` returns at most 100 commits, so for 137 commits it would give 100. I would not disclose that number. I use the paginated endpoint that steps 1.6 and 7(a) already use, and tell the user about this departure from 7(c)'s literal command:

```
gh api repos/octo/widgets/pulls/941/commits --paginate --jq '.[].sha' | wc -l
```

It counts one line per commit across all pages. Expected result: 137.

## Disclosure (returned 137)

> Squash-merging PR 941 collapses 137 commits into one on the base branch. Individual fix-round/review-commit granularity is lost there. `REBASE` or `MERGE` would preserve it.

This is stated even though squash is the configured default. Then, in this order:

1. 7(b)'s full step-2 recheck, without the bypass exception.
2. The SHA checks and the `gh-pr-merge` marker. The disclosure is already done, so nothing runs between the marker and the merge.
3. `gh pr merge 941 --squash --match-head-commit <verified headRefOid>`, plus `--delete-branch` if `merge_auto_delete_branch` is `true`.

## Had it returned 250

The endpoint returns at most 250 commits (step 1.6's reference), so 250 is a cap and not a confirmed total:

> Squash-merging PR 941 collapses at least 250 commits into one. The endpoint I count with returns at most 250, so the exact number is unverified and may be higher. Individual fix-round/review-commit granularity is lost on the base branch.

I would not say "exactly 250". The cap does not block the merge; the disclosure is still made.
