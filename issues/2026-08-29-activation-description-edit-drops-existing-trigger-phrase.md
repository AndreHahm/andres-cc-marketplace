## Summary
Editing a skill's frontmatter activation description to add a new exclusion clause silently dropped two existing, still-supported trigger phrases — since skill routing is driven by the frontmatter description alone (not the unloaded body), those exact existing requests could stop selecting the skill with no error anywhere.

## Environment
- **Product/Service**: `git-kit` plugin — `github-issue-lifecycle`'s frontmatter `description`
- **Region/Version**: this repo, found during PR #179 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A prior commit in the same session (an activation-overlap fix, commit `4326f9a`) rewrapped `github-issue-lifecycle`'s frontmatter `description` paragraph to add a new exclusion.
2. In the process, the phrases "is this issue still valid" and "reopen issue #N" were dropped from the description.
3. The skill's own Testing & Validation section still explicitly promised "is this issue still valid" as a trigger, and the workflow still supported reopening — but since Claude Code routes skill selection from the frontmatter description alone, a user typing either exact phrase might no longer select this skill.

## Expected Behavior
When editing a skill's activation description to add a new exclusion or boundary clause, diff the result against every trigger phrase already promised elsewhere in the same skill (its own Testing & Validation section, worked examples) — an edit made for one purpose shouldn't silently regress an unrelated existing guarantee.

## Actual Behavior
Confirmed via `git log -p`: the rewrap accidentally dropped both phrases while adding the new exclusion, with nothing catching the mismatch between the frontmatter description and the skill's own documented trigger promises until this review round.

## Impact
[Severity: Medium] A routing regression with no functional error anywhere — the skill would simply stop being selected for two previously-working request phrasings, silently. Fixed in `analysis-kit`'s PR #179 (commit `dd73f6e`): restored both phrases alongside the new exclusion.

## Additional Context
Mined from PR #179's own review history (`chatgpt-codex-connector[bot]`; 25 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #179` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/179#discussion_r3886084894
