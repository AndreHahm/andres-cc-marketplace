## Summary
`handling-review-findings`'s Issue path (Workflow step 5) checks `gh issue list -R "<owner>/<repo>" --search "PR #<N>" --limit 100` for an existing issue before filing a new one, but `gh issue list` only lists open issues by default -- a matching issue that's already been closed (fixed, or closed as a duplicate/won't-fix) won't be found, so the workflow could file a second issue for the same PR/SHA/defect.

## Environment
- **Product/Service**: `git-kit`'s `handling-review-findings` skill, `SKILL.md` Workflow step 5
- **Region/Version**: this repo, PR #88, found during that PR's own round-3 review

## Reproduction Steps
1. A finding gets filed as an issue in an earlier round; the issue is later closed (fixed, duplicate, or otherwise).
2. A later round's dedup check runs `gh issue list -R "<owner>/<repo>" --search "PR #<N>" --limit 100` with no `--state` flag.
3. Per `gh issue list --help` -- "By default, this only lists open issues" -- the now-closed issue is excluded from the result set.
4. The dedup check finds no match and files a duplicate issue for the same finding.

## Expected Behavior
The dedup check should search across all issue states (open and closed), since the stated invariant is "no duplicate issue for this PR/SHA/defect" regardless of whether the original issue happens to still be open.

## Actual Behavior
The unqualified `gh issue list` call defaults to open-only, missing closed matches.

## Error Details
~~~
N/A -- logic gap, not a runtime error.
~~~

## Impact
**Minor-to-Major depending on repo issue-closing cadence** -- in a repo where issues filed from PR reviews get triaged and closed quickly, this gap becomes relevant fast; in a slower-moving repo it may rarely trigger. Consequence is a duplicate issue, not a lost finding, so bounded.

## Additional Context
Found by a live Codex review round (round 3) on PR #88, the same PR that introduced the `--search "PR #<N>" --limit 100` dedup fix in round 2 (in response to an earlier finding about the default 30-issue cap). Not fixed as part of PR #88 itself, per `handling-review-findings`'s own round-cap policy: this finding first appears in round 3, which routes to the Issue path rather than an in-session fix.

**Suggested fix** (not prescriptive): add `--state all` to the dedup check's `gh issue list` call in `SKILL.md`'s Workflow step 5.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88
- **Head SHA at time of finding**: `fd9802afcd72ea726e25064ec5fba71a9c88d0bc`
- **Thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88#discussion_r3830100614
- **Reviewer**: Codex (`chatgpt-codex-connector[bot]`)
- **Stated severity**: P2
