## Summary
`merge-pr` has no opt-in way to re-check review findings right before its merge write and stop, so a caller's review-finding stop can be bypassed during `merge-pr`'s own prompts.

## Environment
- **Product/Service**: git-kit `merge-pr`, called by `triaging-dependabot-prs` (step 6.6)
- **Region/Version**: `main` plus the issue #730 branch (`fix/triaging-dependabot-review-threads`)
- **Browser/OS**: n/a

## Reproduction Steps
1. Run `triaging-dependabot-prs` with a request that names both the batch and the reviewer findings.
2. At step 6.6, the skill reads `pr-threads <n>` and `pr-view <n> --fields comments`. Nothing is unresolved, so it invokes `Skill(merge-pr)`.
3. While `merge-pr`'s readiness summary or merge confirmation is open, a reviewer opens an inline thread or posts a conversation comment that carries a finding.
4. Confirm the merge.

## Expected Behavior
When the caller asked for it, `merge-pr` re-reads unresolved review threads and conversation comments immediately before the merge write. If either shows a finding, it stops instead of merging.

## Actual Behavior
- `merge-pr`'s step 2 counts unresolved review threads (GraphQL `reviewThreads`), and step 5's confirmation discloses that count. This is advisory and non-blocking by design (closed issue #160).
- `merge-pr` never reads conversation comments and never stops on the thread count.
- A thread opened after step 2's read is not re-checked before the write. A new conversation comment with a finding is not seen at all. The PR can be merged over a fresh finding.

## Error Details
~~~
n/a (a timing gap, not an error)
~~~

## Visual Evidence
n/a

## Impact
**Low**: a narrow timing window with a partial mitigation. The user sees a freshly read unresolved-thread count at `merge-pr`'s confirmation and can decline. Conversation comments are not covered.

## Additional Context
- Found by a Codex challenger pass in the pre-PR cross-model review of the issue #730 branch. That PR documents this residual window in `triaging-dependabot-prs`.
- Proposal, which keeps #160's default: add an opt-in flag or caller signal. `triaging-dependabot-prs` would pass it when the request named reviewer findings. With the signal set, `merge-pr` re-reads threads and comments right before the merge write and stops on a finding. Without it, behavior stays advisory.
- Acceptance: with the opt-in set, a thread or reviewer comment that appears after step 2's read stops the merge before the write. Without it, behavior is unchanged. An eval covers both cases.
- Related: #730, #160.

Refs: #160
