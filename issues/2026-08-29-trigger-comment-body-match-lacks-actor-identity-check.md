## Summary
A side-effect counter/dedup mechanism built on matching a comment's body text alone can't tell which actor/skill actually posted it — a systemic pattern found in `handling-review-findings`, worth auditing elsewhere.

## Environment
- **Product/Service**: `git-kit` plugin (source instance: `handling-review-findings`'s round-budget counter)
- **Region/Version**: this repo, found during PR #101 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A skill posts a comment matching a fixed trigger string (e.g. `@codex review`) to signal a review cycle, and a counter elsewhere counts occurrences of that exact string to track how many cycles have run.
2. A second, independent skill (e.g. `codex-review-recovery`) posts a byte-identical trigger comment for its own unrelated purpose (a stuck-check retry).
3. Observe that the counter cannot distinguish the two — it counts both, inflating the tracked cycle count.

## Expected Behavior
A side-effect counter/dedup mechanism should only count comments actually produced by the mechanism it's tracking, verified by actor identity, not by body-text pattern alone.

## Actual Behavior
Body-text-only matching silently double-counts (or misattributes) any comment from an unrelated actor that happens to post the same trigger string — in the source instance, this exhausted a round budget early.

## Impact
[Severity: Medium] The specific instance (`handling-review-findings` vs. `codex-review-recovery`) was already fixed in PR #101 (commits `975fec2`, `0e7a079`) via a per-decision marker comment plus an author-ownership check (`author.login` verified against the account running the skill — marker text alone is forgeable since it's published in the skill's own docs). This issue is about the *general* pattern: no `.claude/rules/*.md` file currently governs "verify actor identity, not just body text, before counting a comment toward a side-effect tally" — the same shape could recur in any other skill that counts or dedupes based on comment text (e.g. another counter, or a future skill with its own trigger-comment convention).

## Additional Context
Mined from PR #101's own review history (`chatgpt-codex-connector[bot]`, `devin-ai-integration[bot]`; 18 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #101` section, "Pattern: a comment-body trigger match can't tell which skill/actor posted it") by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/101#discussion_r3835816005

Suggested scope: consider whether a repo-wide rule should name this pattern explicitly, and whether any other skill's own comment-counting/dedup logic should be audited against it.
