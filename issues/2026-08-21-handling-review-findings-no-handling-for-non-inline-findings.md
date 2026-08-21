## Summary
`handling-review-findings`'s Workflow assumes every finding is an inline PR review comment (with a `comment_id` that a reply/resolve mechanism can act on), but its own step 1 fetches `gh pr view --json reviews,comments` -- which includes PR review *bodies* (a top-level review summary, no line association) alongside the inline comment list. A finding a reviewer puts only in a review body, or in a general PR conversation comment, has no corresponding inline-comment ID or GraphQL review-thread ID for the Fix path's reply-and-resolve step or the Issue path's reply-with-issue-link step to act on.

## Environment
- **Product/Service**: `git-kit`'s `handling-review-findings` skill, `SKILL.md` Workflow (all of steps 1, 4, 5, 6)
- **Region/Version**: this repo, PR #88, found during that PR's own review

## Reproduction Steps
1. A reviewer (human or bot) posts a finding as the body text of a submitted PR review (`POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` with a `body`, no inline `path`/`line`) -- or as a plain conversation comment (`POST /repos/{owner}/{repo}/issues/{pull_number}/comments`), rather than an inline review comment.
2. Workflow step 1's `gh pr view $ARGUMENTS --json reviews,comments` call surfaces the review body as part of `reviews`, so the finding is visible and gets classified in step 2.
3. Once triaged, every disposition path (Fix path step 4, Issue path step 5, Decline path step 6) requires replying to "the finding's own thread" and, for the Fix path, resolving it via `resolveReviewThread`.
4. Per `plugins/git-kit/skills/gh-operations/references/api-reference.md` (lines ~163-210), a review body and a conversation comment are structurally different objects from an inline review comment -- neither has the `comment_id`/GraphQL thread node ID `references/github-api-mechanics.md`'s reply/resolve mechanics require. There is nothing to reply to or resolve for a non-inline finding.
5. The workflow can commit and push a fix for such a finding, then have no defined way to complete its own required reply/resolve step.

## Expected Behavior
The Workflow should either restrict triage to inline findings only (explicitly excluding review-body/conversation-comment findings, with guidance on how to handle them separately), or define a distinct mechanism for a non-inline finding's own "reply" (e.g. a general PR comment referencing what was fixed) since it has no thread to resolve at all.

## Actual Behavior
No distinction exists in the current Workflow -- step 1 fetches both kinds of finding sources together, and every later step assumes a resolvable thread exists.

## Error Details
~~~
N/A -- design gap, not a runtime error.
~~~

## Impact
**Major** -- this can leave a fix committed and pushed with the workflow unable to complete its own disclosure/reply obligations for that specific finding, and (for a Critical/Major non-inline finding) potentially unable to satisfy the Hard Cap exception's requirement to reply pointing at a filed issue.

## Additional Context
Found by a live Codex review round on PR #88. Not fixed as part of PR #88 itself -- this PR is well past its own two-round fix cap at the point this was found (multiple fix-driven pushes already landed), so per `handling-review-findings`'s own round-cap policy this routes to the Issue path rather than another in-session fix.

**Suggested fix** (not prescriptive): add an explicit classification step distinguishing inline findings (have a `comment_id`, use the existing reply/resolve mechanics) from non-inline findings (review body or conversation comment, no thread) -- for the latter, either restrict this skill's own scope to inline findings only and hand off non-inline ones to a human/different mechanism, or define a review-level or PR-conversation-level "reply" (a general PR comment, not a thread reply) as the acknowledgment mechanism, with no resolve step since there's no thread to resolve.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88
- **Head SHA at time of finding**: `b100f43cfe64b65961a3a3b9f65d3cc351d06d7a`
- **Thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88#discussion_r3833471803
- **Reviewer**: Codex (`chatgpt-codex-connector[bot]`)
- **Stated severity**: P1
