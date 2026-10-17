## Summary
The reviewer-eval archiver enumerates a PR's commits through an endpoint capped at 250 commits, so a PR with more commits is archived incompletely and nothing says so.

## Environment
- **Product/Service**: `scripts/reviewer_eval/archive.py` (`GhSource.pr_heads`, `gh api .../pulls/<n>/commits --paginate`)
- **Region/Version**: PR #595, head `eb9f7c75c8fb7f4a518b4b4afbe81799452bef50`
- **Browser/OS**: not relevant

## Reproduction Steps
1. Run `uv run python -m scripts.reviewer_eval.archive --pr <N>` for a PR with more than 250 commits.
2. Compare the commits the archiver selected artifacts for with the PR's commit count.

Not reproduced live: this repository has no PR over the cap (PR #595 has 13 commits). The limit comes from GitHub's documentation of the list-commits-on-a-pull-request endpoint, which the reviewer cited; it was not checked against a live response.

## Expected Behavior
Every downloadable `codex-review-result` of a commit in the PR is archived, or the run reports that the commit list was incomplete.

## Actual Behavior
`select_artifacts` only sees the first 250 commits the endpoint returns. Artifacts of any later commit are never selected, and the report shows no failure.

## Error Details
~~~
None. The omission is silent.
~~~

## Visual Evidence
None.

## Impact
Low to Medium. It only affects PRs with more than 250 commits, which this repository rarely has, but the result is a silently incomplete archive, and artifacts expire after 90 days.

## Additional Context
Possible fixes: enumerate the PR's commits through GraphQL (`pullRequest.commits`, paginated) or the compare endpoint, or make the archiver fail loudly when the endpoint returns exactly 250 commits.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/595
- **Head SHA the finding was raised against**: `eb9f7c75c8fb7f4a518b4b4afbe81799452bef50`
- **Thread**: https://github.com/AndreHahm/andres-cc-marketplace/pull/595#discussion_r4303356978
- **Reviewer**: CodeRabbit
- **Stated severity**: Major

Found in PR #595.
