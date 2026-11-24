Command 7(a) runs (no pipe; I count the printed lines myself):

```
gh api repos/octo/widgets/pulls/946/commits --paginate --jq '.[] | select((.parents | length) > 1) | .sha'
```

What it reports: exit code 1 (HTTP 502 on page 2) and no stdout. With exit 0, no lines would mean zero merge commits. With a non-zero exit the count is unknown, and would be unknown even if some lines had been printed. Page 1 having no merge commit says nothing about page 2 and later. A pipe such as `| wc -l` would have hidden the failure and printed 0.

What happens next:
- I report: "The number of merge commits in PR 946 could not be determined: the commits request failed with HTTP 502 on a later page."
- I stop the run there. I never treat the count as zero and never go on to `--rebase`.
- No strategy question (that is for a known non-zero count), no final recheck, no marker write, no merge command.
- The PR stays open and unmerged. The user can re-run merge-pr once the API answers.
