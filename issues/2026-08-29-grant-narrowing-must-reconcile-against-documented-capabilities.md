## Summary
A least-privilege tool-grant narrowing pass must be reconciled against the component's own documented capability list — an allowlist built only from "what's obviously dangerous" can silently regress real, advertised functionality the component's own reference docs still claim to support.

## Environment
- **Product/Service**: `git-kit` plugin (source instance: `gh-operations`)
- **Region/Version**: this repo, found during PR #121 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A skill's `allowed-tools` originally grants an unbounded wildcard (e.g. `Bash(gh pr:*)`/`Bash(gh issue:*)`).
2. A security-motivated narrowing pass replaces the wildcard with an explicit subcommand allowlist, reasoning from "what's clearly needed" without cross-checking the component's own reference documentation.
3. The skill's own `references/*.md` files still document several subcommands (e.g. `gh issue view/comment/reopen/pin/transfer`, `gh pr close/reopen/checkout/ready/diff`) as supported management workflows.
4. Those subcommands now fall outside the narrowed grant — a request for any of them unexpectedly fails, even though the skill's own docs say they're supported.

## Expected Behavior
When narrowing a tool grant for least privilege, cross-check the resulting allowlist against every subcommand the component's own reference/documentation files claim to support — not just against what's obviously dangerous to exclude.

## Actual Behavior
An earlier R6 narrowing pass on `gh-operations` replaced the unbounded grant with an allowlist that omitted several subcommands its own `references/pr-operations.md`/`references/issue-operations.md` still documented as supported.

## Impact
[Severity: Medium] A security fix silently broke advertised functionality. The specific instance was already fixed in `git-kit`'s PR #121 (commit `643fa00`), adding the missing subcommands, each individually verified as a real `gh` subcommand and cross-checked against the skill's own deliberately-excluded list (`create`/`merge`/`review`/`comment` for PRs, routed to other skills). No `.claude/rules/*.md` file currently states this cross-check as a required step of a grant-narrowing pass — any other component's own least-privilege narrowing (in this repo or elsewhere) could reproduce the same functionality regression.

## Additional Context
Mined from PR #121's own review history (`chatgpt-codex-connector[bot]`; 17 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #121` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/121#discussion_r3845824895
