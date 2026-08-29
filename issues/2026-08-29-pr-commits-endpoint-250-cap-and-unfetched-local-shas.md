## Summary
Two related gaps in a cherry-pick strategy that lists a PR's commits via the GitHub REST API: (1) the "list commits on a pull request" endpoint caps at 250 commits regardless of `--paginate`, silently truncating a larger PR; (2) even a correctly fetched, valid SHA can be absent from the local git object database, causing `git cherry-pick` to fail deep into the operation rather than being caught up front.

## Environment
- **Product/Service**: `git-kit` plugin — `git-worktrees`/`merge-pr`'s Strategy C cherry-pick path
- **Region/Version**: this repo, found during PR #148 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. **250-cap**: Fetch a PR's commit list via `gh api repos/{owner}/{repo}/pulls/{number}/commits --paginate` where the PR has more than 250 commits. GitHub's own REST docs state this endpoint "lists a maximum of 250 commits for a pull request" — a hard server-side cap `--paginate` cannot walk past.
2. A strategy relying on this list as authoritative can report success after cherry-picking only the first 250 commits, silently omitting the rest.
3. **Unfetched local SHAs**: On a maintainer checkout that never fetched a contributor's feature branch, the API still returns valid commit SHAs for that PR.
4. Handing those SHAs directly to `git cherry-pick` fails with an unknown/bad-object error, since the commits were never fetched into the local object database.

## Expected Behavior
When a documented API endpoint has a hard page cap, fall back to a genuinely paginated alternative (the compare endpoint) once the cap is hit, rather than trusting `--paginate` to walk past a server-side ceiling. Separately, verify every commit a remote API returns actually exists locally and fetch it if missing, before handing the list to a cherry-pick step.

## Actual Behavior
A PR at or above the 250-commit boundary would silently lose commits from the resolved list; an unfetched contributor branch would surface as a confusing mid-operation git error rather than an up-front, clear failure.

## Impact
[Severity: High for the 250-cap (silent data loss on large PRs); Medium for the unfetched-SHA case (confusing failure, but not silent).] Both fixed in `git-kit`'s PR #148 (commit `c5f9c9c`): the 250-commit hard cap is now documented and, when the resolved count is exactly 250, Path 2 falls back to `gh api repos/{owner}/{repo}/compare/<baseRefOid>...<headRefOid> --paginate` (live-verified against GitHub's docs to support pagination past 250 for the commit list). Path 2 also now verifies every resolved SHA exists locally with `git cat-file -e <sha>^{commit}` before handing the list to Strategy C, fetching via `git fetch origin pull/<N>/head` (GitHub's synthetic per-PR ref, which works even for a fork PR) and re-verifying if any is missing.

## Additional Context
Mined from PR #148's own review history (`chatgpt-codex-connector[bot]`; 12 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #148` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/148#discussion_r3872684537, https://github.com/AndreHahm/andres-cc-marketplace/pull/148#discussion_r3872684549
