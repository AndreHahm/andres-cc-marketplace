## Summary
`.claude/review-outcomes.json` gets a merge conflict whenever two or more PRs promote review dispositions into it at the same time.

## Environment
- **Product/Service**: `.claude/review-outcomes.json`, written by `git-review-ledger.py promote` (git-kit `handling-review-findings`)
- **Region/Version**: PR #595, head `51ef5d90f2f431caab1ca9f26ebcb9d703f1ee04`
- **Browser/OS**: not relevant

## Reproduction Steps
1. On PR A, record review dispositions and run `git-review-ledger.py promote --pr <A>`, then commit the updated `.claude/review-outcomes.json`.
2. On PR B, do the same, from a branch cut before PR A's promotion landed.
3. Merge or rebase PR B onto the branch that now holds PR A's entries.

## Expected Behavior
Promoting entries from concurrent PRs does not conflict, because each PR only adds its own entries.

## Actual Behavior
The file is one JSON `entries` array, kept in finding-id order, and every promotion appends at the end of it. Two PRs therefore edit the same region, and whichever lands second conflicts. The conflict markers fall in the middle of a JSON object (the shared opening line of the last entry), so a hand resolution has to repair the braces as well as keep both sets.

## Error Details
~~~
CONFLICT (content): Merge conflict in .claude/review-outcomes.json
error: could not apply <commit>... chore(reviewer-eval): record the PR 595 review outcomes and issue draft
~~~

Seen live on PR #595: rebasing onto `origin/main` conflicted here because main had received ledger entries for PRs 597, 598 and 602 while PR #595 added seven of its own. No entries overlapped; it was resolved by hand by keeping both sets and fixing the braces, and the merged file was checked afterwards (19 entries, no duplicate ids, still in id order).

## Visual Evidence
None.

## Impact
**High** - every PR that goes through the review loop and promotes entries will hit this once a second PR has promoted, and a wrong hand merge can drop or corrupt entries. Phase 4 of #568 builds its eval corpus from this file.

## Additional Context
Ideas, not decisions:
- one file per PR (for example `.claude/review-outcomes/pr-<N>.json`) that the reader merges;
- a `.gitattributes` merge driver for this file;
- promoting after merge, which does not work as things stand because the skill promotes before the last push (a merged PR cannot take a direct commit to `main`).

## References
- Found while working on PR #595: https://github.com/AndreHahm/andres-cc-marketplace/pull/595
- Parent work: #568 (reference only, not closing)
