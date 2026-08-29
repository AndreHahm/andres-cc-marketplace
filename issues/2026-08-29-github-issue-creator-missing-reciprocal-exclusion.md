## Summary
`github-issue-creator` is missing the reciprocal activation-overlap exclusion back to `analysis-kit`'s `managing-review-learnings` skill — only one direction of the required bidirectional exclusion exists.

## Environment
- **Product/Service**: `git-kit` plugin, `github-issue-creator` skill
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Read `plugins/git-kit/skills/github-issue-creator/SKILL.md`'s "When NOT to Use" section in full.
2. Grep it for `managing-review-learnings` and `analysis-kit` — zero matches, confirmed live.
3. Compare against `plugins/analysis-kit/skills/managing-review-learnings/SKILL.md`'s own "When NOT to Use" section (around line 53-54), which already reads: "A single already-known bug with no PR-mining involved — use `github-issue-creator` (drafting) or `github-issue-lifecycle` (full lifecycle) directly; this skill's own input is always a mined, cross-PR systemic-pattern candidate."

## Expected Behavior
Per this repo's own `.claude/rules/resolve-activation-overlap-bidirectionally.md` convention, two skills with genuinely overlapping domains need a reciprocal, explicit exclusion naming the sibling and the distinguishing criterion — in both directions. `github-issue-creator`'s own "When NOT to Use" section should name `managing-review-learnings` and state the distinguishing criterion: a mined, cross-PR systemic-pattern candidate needing doc-diff/rule-coverage judgment first belongs to `managing-review-learnings`; a single already-known bug/log/screenshot with no such judgment needed belongs directly here.

## Actual Behavior
Only `managing-review-learnings`' side of the exclusion exists — it already points users toward `github-issue-creator` for the single-known-bug case, but `github-issue-creator`'s own activation text is silent on this sibling entirely. A request framed as "draft this mined finding as an issue" could land ambiguously on `github-issue-creator` directly instead of being routed through `managing-review-learnings`' own doc-diff/rule-coverage checks first.

## Impact
**Low** — a routing/activation-precision gap, not a functional bug. Worst case is a mined finding getting drafted via `github-issue-creator` directly, bypassing `managing-review-learnings`' doc-diff/rule-coverage checks — likely still caught by a careful reader, since both skills' purposes are described clearly enough elsewhere in their own docs.

## Additional Context
This is the same shape of gap just fixed in this session for a sibling skill: `github-issue-lifecycle`'s own "When NOT to Use" section already got this exact exclusion added for `managing-review-learnings` (commit `4326f9a`, part of PR #179) — `github-issue-creator`, which `github-issue-lifecycle` delegates drafting to, was apparently missed when that fix was made, even though it's exactly as exposed to the same ambiguity (a user could ask this skill directly to draft a mined-finding writeup, bypassing both `managing-review-learnings` and `github-issue-lifecycle`).
