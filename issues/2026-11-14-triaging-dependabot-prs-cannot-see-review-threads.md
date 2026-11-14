## Summary
triaging-dependabot-prs cannot see inline review threads, so its stop before merging or closing a PR with reviewer findings covers PR comments only.

## Environment
- **Product/Service**: git-kit `triaging-dependabot-prs` (`SKILL.md` "When NOT to Use", step 6 loop; `scripts/dependabot_pr_read.py`)
- **Region/Version**: found in PR #726 at head `00f0a4728b919c29aabd3ec2850d558acf8909ab`

## Reproduction Steps
1. Read `plugins/git-kit/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py`, `VIEW_FIELDS` (around lines 58-73): it offers `comments` but no review-thread field.
2. Read the skill's step 6 loop: it never reads review threads before the close (6.2) or merge (6.6) path.
3. Take a Dependabot PR whose only reviewer finding is an inline review thread, with no PR conversation comment.

## Expected Behavior
Before closing or merging a Dependabot PR during a batch that also names reviewer findings, the skill sees every reviewer finding on that PR, inline threads included, and stops to offer `handling-review-findings` first.

## Actual Behavior
The skill can only see PR conversation comments. An inline-only finding does not trigger the stop. On the merge path `merge-pr`'s own gates (change requests, required conversation resolution) still apply; the close path has no such backstop. PR #726 narrowed the skill text to what the reader can see and points here.

## Error Details
~~~
None: a capability gap, not an error.
~~~

## Visual Evidence
None.

## Impact
**Low** - A combined "triage the Dependabot PRs and their findings" request can close a Dependabot PR without offering triage of an inline-only finding. Dependabot PRs rarely carry reviewer threads.

## Additional Context
Suggested fix: add a read-only, paginated review-thread query to `dependabot_pr_read.py`, read it at the start of each PR's loop before close or merge, decide whether the gate covers all threads or only unresolved ones, and test the combined-request close and merge paths.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/726
- **Head SHA**: `00f0a4728b919c29aabd3ec2850d558acf8909ab`
- **Thread**: review comment 4571948380 (`plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md`, lines 34-36)
- **Reviewer**: Devin Review
- **Severity**: Minor (yellow)

Found in PR #726.
