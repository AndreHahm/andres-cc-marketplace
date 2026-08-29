## Summary
When one user decision fans out into multiple physical side effects (e.g. one comment posted per selected item), the *decision* should be counted as the unit — not each side effect independently — but this isn't a named convention anywhere in the repo.

## Environment
- **Product/Service**: `git-kit` plugin (source instance: `handling-review-findings`'s round-budget counter)
- **Region/Version**: this repo, found during PR #101 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A workflow lets a user select multiple items in one decision (e.g. multiple reviewers in one `AskUserQuestion` answer).
2. The workflow then posts one side-effecting action per selected item (e.g. one trigger comment per reviewer).
3. A separate counter tracks "how many decisions/cycles have occurred" by counting the side effects directly, one increment per action.
4. Observe the counter over-counts: one logical decision (2 reviewers selected) consumes 2 units instead of 1.

## Expected Behavior
The counter should track the decision as the unit of count, using a shared identifier applied to every side effect produced by that one decision, deduped before counting.

## Actual Behavior
`handling-review-findings`' round-budget counter originally counted each posted trigger comment independently, so selecting 2 reviewers in one decision consumed 2 units of the round budget instead of 1.

## Impact
[Severity: Low] The specific instance was already fixed in PR #101 (commit `975fec2`) via a per-decision `<batch-id>` marker shared across every comment from that decision, with the counter deduping on that identifier. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "when one decision fans out into multiple side effects, count the decision, not each side effect" — any other workflow with a similar decision-to-multiple-actions shape could reproduce the same over-count.

## Additional Context
Mined from PR #101's own review history (`chatgpt-codex-connector[bot]`; 18 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #101` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/101#discussion_r3836083791
