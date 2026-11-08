# command-development frontmatter-reference: Bash(git:*), Bash(npm:*), Bash(docker:*) presented as security filters

## Summary

The reference shows Bash(git:*), Bash(npm:*) and Bash(docker:*) as standard command-filter examples and describes them as security-oriented pre-approval patterns.

## Environment

- Repository: AndreHahm/andres-cc-marketplace, branch `fix/propagate-allowed-tools-correction`
- File: `plugins/plugin-devkit/skills/command-development/references/frontmatter-reference.md` line 97

## Reproduction Steps

Read the file at the cited line on the reviewed head commit.

## Expected Behavior

State that such a prefix pre-approves a family of commands, not a safe subset, or choose examples that do not cover mutating forms.

## Actual Behavior

These prefixes still cover state-changing operations and arbitrary package scripts, while the text frames them as a protective filter.

## Error Details

Not applicable: this is a documentation or design finding, not a runtime error.

## Visual Evidence

Not applicable.

## Impact

Readers copy the examples believing they limit what a command can do; allowed-tools only pre-approves.

## Additional Context

- Found in PR #675 (https://github.com/AndreHahm/andres-cc-marketplace/pull/675)
- Reviewed head SHA: 862fa4b4 (CI round 10; the export item: 454aac18, round 9)
- Reviewer: security-reviewer (Codex delta review), severity: Major
- Deferred as out of the PR's scope; the text pre-dates the PR or sits next to lines it changed.
