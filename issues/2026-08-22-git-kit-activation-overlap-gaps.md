## Summary
Three git-kit skills (`explain-pr-changes`, `gh-operations`, `merge-pr`) have activation-overlap and boundary-text gaps against `handling-review-findings`, violating this repo's own bidirectional-exclusion convention in one direction or another.

## Environment
- **Product/Service**: `git-kit` plugin (this marketplace)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Read `plugins/git-kit/skills/explain-pr-changes/SKILL.md` and `plugins/git-kit/skills/handling-review-findings/SKILL.md` side by side — neither's "When NOT to Use" (or equivalent) section names the other, despite both classifying/triaging PR review comments into a disposition.
2. Read `plugins/git-kit/skills/gh-operations/SKILL.md`'s "Issues" section (`gh issue create`) — it carries no exclusion at all, even though `github-issue-creator` already points one-directionally at `gh-operations` for filing.
3. Read `plugins/git-kit/skills/merge-pr/SKILL.md`'s Boundaries section — it states `explain-pr-changes` resolves review comments; grep `explain-pr-changes/SKILL.md` for `resolveReviewThread` — no match exists there.

## Expected Behavior
Per `.claude/rules/resolve-activation-overlap-bidirectionally.md`, two skills (or a skill/agent pair) with genuinely overlapping domains should carry a reciprocal, explicit exclusion naming the sibling and the exact distinguishing criterion — and boundary text should name the skill that actually owns the capability described.

## Actual Behavior
1. **`explain-pr-changes` ↔ `handling-review-findings` (Major).** `explain-pr-changes` builds a FIXED/TRACKED/SKIPPED classification table for an already-open PR's review comments; `handling-review-findings` classifies the same comments into Fix/Issue/Decline. Neither file's exclusion section names the other, so a request like "triage this diff before requesting review" or "triaging review feedback" could plausibly route to either.
2. **`gh-operations` ↔ `handling-review-findings`/`github-issue-creator` (Major).** `gh-operations`'s "Issues" bullet (`gh issue create --title ... --body ...`) has no exclusion at all. `handling-review-findings` performs the literal same command for PR-review-tied findings with mandatory PR/SHA/thread traceability; `github-issue-creator` already points at `gh-operations` for live filing, but `gh-operations` never reciprocates toward either.
3. **`merge-pr`'s Boundaries text (Minor).** States "Does not resolve review comments... that's `explain-pr-changes`'s job," but `explain-pr-changes` never calls `resolveReviewThread` (no such GraphQL mutation anywhere in that file) — that mechanism belongs to `handling-review-findings`. This is a capability-attribution error, not an activation-trigger ambiguity, but it corroborates the same underlying confusion as finding 1.

## Error Details
~~~
N/A — a documentation/activation-hygiene gap, not a runtime error.
~~~

## Visual Evidence
N/A

## Impact
**Medium** — no user-facing runtime failure, but a real risk of a request routing to the wrong skill (or a boundary-text reader being misdirected toward `explain-pr-changes` for a capability it doesn't have). Two of the three findings are Major per the source audit; none are release-blocking.

## Additional Context
Found during PR #101's review (https://github.com/AndreHahm/andres-cc-marketplace/pull/101) by a `plugin-auditor` pass scoped to that PR's own diff (`.claude/output/plugin-auditor/scoped-6components-1plugins-2026-08-22T13-54-28Z.json`, findings `activation-reviewer:M1`, `activation-reviewer:M2`, `activation-reviewer:m1`). All three touch skills PR #101 did not modify (`explain-pr-changes`, `gh-operations`, `merge-pr`), so they were deliberately deferred rather than fixed in that PR — see the PR's own review-finding triage for the full disposition record.

Suggested fixes:
1. Add reciprocal "When NOT to Use" exclusions between `explain-pr-changes` and `handling-review-findings` — `explain-pr-changes` defers for actually fixing/filing/declining a finding, replying to or resolving an inline thread, or triggering a next review round; `handling-review-findings` defers to `explain-pr-changes` for the lightweight PR-description-update summary table.
2. Add an exclusion to `gh-operations`'s Issues bullet naming both `handling-review-findings` (review-finding-tied issues needing PR/SHA/thread traceability) and `github-issue-creator` (general write-ups from raw notes/logs).
3. Correct `merge-pr`'s Boundaries text to name `handling-review-findings` instead of `explain-pr-changes` as the skill that resolves review comments.

Source: `.claude/rules/resolve-activation-overlap-bidirectionally.md` (this repo's own convention, already used to fix analogous overlaps in `analysis-kit` and elsewhere in `git-kit`).
