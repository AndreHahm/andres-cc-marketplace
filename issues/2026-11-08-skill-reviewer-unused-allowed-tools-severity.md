# skill-reviewer: severity of an unused allowed-tools entry versus R6 grant hygiene

## Summary

skill-reviewer grades an allowed-tools entry that is never referenced as Minor, while plugin-rulebook R6 treats over-permissioning as REQUIRED for compliance.

## Environment

- Repository: AndreHahm/andres-cc-marketplace, branch `fix/propagate-allowed-tools-correction`
- File: `plugins/plugin-devkit/agents/skill-reviewer.md` line 144

## Reproduction Steps

Read the file at the cited line on the reviewed head commit.

## Expected Behavior

Pick one severity mapping, or document why the quality review and the compliance rule intentionally differ, and align agent-development with the decision.

## Actual Behavior

skill-reviewer reports Minor and says the review scores quality; one reviewer in CI expects Major.

## Error Details

Not applicable: this is a documentation or design finding, not a runtime error.

## Visual Evidence

Not applicable.

## Impact

Reviewers disagree across CI rounds about the same entry. The Minor line already exists on main, and no authoritative Major mapping was found in agent-development.

## Additional Context

- Found in PR #675 (https://github.com/AndreHahm/andres-cc-marketplace/pull/675)
- Reviewed head SHA: 862fa4b4 (CI round 10; the export item: 454aac18, round 9)
- Reviewer: subagent-reviewer (Codex delta review), severity: Major
- Deferred as out of the PR's scope; the text pre-dates the PR or sits next to lines it changed.
