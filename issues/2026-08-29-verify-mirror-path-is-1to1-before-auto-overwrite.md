## Summary
Before treating a resolved "mirror path" as safe to auto-overwrite, verify it is actually a clean 1:1 mirror of the one source being edited — existence at the expected location alone doesn't establish that, and a many-sources-to-one merged/aggregate destination is a categorically different case.

## Environment
- **Product/Service**: `analysis-kit` plugin (source instance: `running-a-full-retrospective`'s direct-fix path)
- **Region/Version**: this repo, found during PR #108 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A direct-fix workflow resolves a canonical source path (e.g. `plugins/<name>/hooks/hooks.json`) and checks whether a corresponding `.claude/`-side path exists.
2. If it exists, the workflow treats it as "the mirror" and edits both files identically.
3. For `skills/`/`agents/`/`commands/`/`rules/`, this repo's convention really is a clean 1:1 mirror, so the assumption holds.
4. For `hooks/hooks.json`, the `.claude/`-side file is actually a *merged aggregate* of several plugins' own hook configs, not a copy of any single one — editing "the mirror" there overwrites an unrelated aggregate with the wrong plugin's content.

## Expected Behavior
A resolved "mirror path" should only be auto-edited after verifying it's a genuine 1:1 mirror of the one source being changed; a many-sources-to-one merged destination should be routed to a hand-off/human path instead.

## Actual Behavior
`running-a-full-retrospective`'s direct-fix flow treated "a corresponding `.claude/`-side file exists" as sufficient grounds to resolve and auto-edit it, with no check for whether the relationship was actually 1:1.

## Impact
[Severity: Medium] The specific instance was already fixed in PR #108 (commit `67ccdbc`) by scoping mirror-detection to `skills/`/`agents/`/`commands/`/`rules/` only, and routing any `hooks/`-path resolution to hand-off instead of direct auto-edit. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "verify a resolved mirror path is a genuine 1:1 mirror before auto-overwriting it, not merely that a file exists there" — any future direct-fix-style automation touching a mirrored path could reproduce the same class of unintended overwrite.

## Additional Context
Mined from PR #108's own review history (`chatgpt-codex-connector[bot]`; 16 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #108` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/108#discussion_r3842768726
