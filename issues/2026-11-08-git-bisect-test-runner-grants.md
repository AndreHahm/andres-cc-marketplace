# git-bisect: test-runner grants pre-approve arbitrary code through the user's test command

## Summary

git-bisect runs the user's test command verbatim during an automatic bisect, and its allowed-tools pre-approves Bash(npm:*), Bash(yarn:*), Bash(pnpm:*), Bash(pip:*), Bash(pytest:*), Bash(cargo:*) and Bash(go:*).

## Environment

- Repository: AndreHahm/andres-cc-marketplace, branch `fix/propagate-allowed-tools-correction`
- File: `plugins/git-kit/skills/git-bisect/SKILL.md` line 43

## Reproduction Steps

Read the file at the cited line on the reviewed head commit.

## Expected Behavior

Pre-approve a narrower set, or keep the broad grants and state the trust assumption next to them.

## Actual Behavior

These general task runners and installers can run arbitrary scripts or change state, and they are pre-approved for a command the user supplies.

## Error Details

Not applicable: this is a documentation or design finding, not a runtime error.

## Visual Evidence

Not applicable.

## Impact

A malicious or mistaken test command in a bisected repository runs with no permission prompt for these prefixes.

## Additional Context

- Found in PR #675 (https://github.com/AndreHahm/andres-cc-marketplace/pull/675)
- Reviewed head SHA: 862fa4b4 (CI round 10; the export item: 454aac18, round 9)
- Reviewer: security-reviewer (Codex delta review), severity: Major
- Deferred as out of the PR's scope; the text pre-dates the PR or sits next to lines it changed.
- SKILL.md lines 20-28 document the grants as deliberate; the open question is whether that fits plugin-rulebook R6.
