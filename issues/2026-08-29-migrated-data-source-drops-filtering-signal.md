## Summary
Migrating a data source silently dropped a filtering signal (actor type) a "human comments only" contract depended on — the new source (`gh pr view --json reviews`) exposes no bot marker, so bot-authored review bodies started being retained despite the promised human-only contract.

## Environment
- **Product/Service**: `plugin-devkit` plugin — `rules-extract`'s PR Review Extraction Mode
- **Region/Version**: this repo, found during PR #177 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Read `rules-extract`'s PR Review Extraction Mode documentation, which promises human comments only.
2. Note the mode was migrated to source review data from `gh pr view --json reviews` instead of its previous source.
3. Confirm the new source has no actor-type field or reliable bot suffix — `rules-extract` therefore retains bot-authored review bodies, contradicting its own documented human-only contract.
4. Separately, the human-confirmation gate (Step P5's `AskUserQuestion`) exempted "staging-only" project-pattern writes from confirmation — an exemption that only correctly covered sources that had a working bot filter (sources 1/2); the migrated source (3) never did, so its candidates reached staging with no human check at all.

## Expected Behavior
Before migrating a data source a consuming contract depends on, check the new source's schema for feature parity with the old one — a filtering signal the old source exposed (here: actor type) shouldn't be silently absent from the replacement without the consuming logic being updated to compensate.

## Actual Behavior
Bot-authored review patterns could enter staging unconfirmed, since neither the missing bot filter nor the staging-write exemption accounted for the migration.

## Impact
[Severity: Medium] Bot-authored content entering a human-curated staging area without confirmation undermines the whole point of the human-only contract. Fixed in `plugin-devkit`'s PR #177 (commit `29aef6b`): Step P5's `AskUserQuestion` gate no longer exempts a source-3 candidate from confirmation even when routed to staging, and source-number tagging was added so the exception has a concrete mechanism to key on. A deeper structural gap (the `--update`/`--from-conversation` promote paths have no confirmation gate at all, and the staging format doesn't persist author/source provenance) was filed separately as #181, since closing it requires edits outside this PR's own changed-file scope.

## Additional Context
Mined from PR #177's own review history (`devin-ai-integration[bot]`; 17 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #177` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/177#discussion_r3885664289
