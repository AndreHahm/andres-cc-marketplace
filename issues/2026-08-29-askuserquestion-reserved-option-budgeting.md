## Summary
`AskUserQuestion`'s reserved/mandatory options must be budgeted into its per-question cap, and the 2-option structural floor needs an explicit path for 0/1-eligible-item cases — neither is currently a named, checkable convention in this repo.

## Environment
- **Product/Service**: `git-kit` plugin (source instance: `handling-review-findings`'s reviewer-selection trigger-ask)
- **Region/Version**: this repo, found during PR #101 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Build an `AskUserQuestion` whose option list mixes a fixed/mandatory item (e.g. a "stop" option) with a variable-length list (e.g. one option per eligible reviewer).
2. Size the variable list without first subtracting the fixed item(s) from the tool's real per-question option cap (4).
3. With the maximum variable-list size already at capacity, adding one more variable item pushes the question over the cap.
4. Separately: when fewer than a configured minimum of cycles have run, omit the mandatory "stop" option to enforce the floor — but with only 0 or 1 eligible variable items, the resulting list falls below `AskUserQuestion`'s 2-option minimum.

## Expected Behavior
A fixed/mandatory option should always be subtracted from the total per-question cap before sizing the variable-length part of the list, and an explicit 0/1-eligible-item path should exist so the question never falls below the 2-option minimum.

## Actual Behavior
`handling-review-findings`' original design sized its 3-reviewer variable list independently of the mandatory stop option, reaching exactly 4 total with no room to grow; documentation claimed "nothing assumes exactly three reviewers," which was false. Separately, omitting the stop option below `min_rounds` with 0 or 1 eligible reviewers produced an invalid `AskUserQuestion` call.

## Impact
[Severity: Medium] The specific instance was already fixed in PR #101 (commit `8be897b`), which adds explicit 0/1-eligible-reviewer paths and corrects the reserved-option-budgeting documentation. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "budget every reserved/mandatory `AskUserQuestion` option into its per-question cap before sizing a variable list, and always account for 0/1-item degenerate cases" — any other skill building a mixed fixed+variable `AskUserQuestion` list could reproduce the same shape.

## Additional Context
Mined from PR #101's own review history (`devin-ai-integration[bot]`, `chatgpt-codex-connector[bot]`; 18 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #101` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. Related to, but distinct from, this repo's existing `.claude/rules/verify-tool-behavior-before-instructing.md`, which already documents `AskUserQuestion`'s two independent caps (options-per-question, questions-per-call) but not this reserved-option-budgeting or 0/1-item angle.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/101#discussion_r3836083786, https://github.com/AndreHahm/andres-cc-marketplace/pull/101#discussion_r3836083791

Suggested scope: consider adding a short addendum to `verify-tool-behavior-before-instructing.md`'s own `AskUserQuestion` coverage naming this reserved-option-budgeting and 0/1-item angle explicitly.
