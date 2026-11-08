# permission-reviewer: the Codex export is unregistered in the sync config and has drifted from the agent file

## Summary

The agent has a hand-maintained export at .codex/agents/permission-reviewer.toml that is absent from codex_exports.agents in .claude/marketplace-sync.json, so convert-codex-exports never updates it.

## Environment

- Repository: AndreHahm/andres-cc-marketplace, branch `fix/propagate-allowed-tools-correction`
- File: `.codex/agents/permission-reviewer.toml` line 29

## Reproduction Steps

Read the file at the cited line on the reviewed head commit.

## Expected Behavior

Register the export so it is generated, or remove it, and sync it once.

## Actual Behavior

Registered exports are regenerated from the agent file. This one is not, and it differs from the agent beyond the five lines synced in PR 675 (about 28 agent lines missing from it and 7 export lines not in the agent).

## Error Details

Not applicable: this is a documentation or design finding, not a runtime error.

## Visual Evidence

Not applicable.

## Impact

Codex users get stale reviewer instructions, and every wording change to the agent needs a manual toml edit that CI does not check.

## Additional Context

- Found in PR #675 (https://github.com/AndreHahm/andres-cc-marketplace/pull/675)
- Reviewed head SHA: 862fa4b4 (CI round 10; the export item: 454aac18, round 9)
- Reviewer: consistency-reviewer (Codex delta review), severity: Major
- Deferred as out of the PR's scope; the text pre-dates the PR or sits next to lines it changed.
