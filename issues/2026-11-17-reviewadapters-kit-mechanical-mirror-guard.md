## Summary
The stop that keeps reviewadapters-kit from running the reviewed checkout's own `.claude/` mirror is prose in files that the reviewed branch can edit; it needs a mechanical guard outside the checkout.

## Environment
- **Product/Service**: reviewadapters-kit (`rva-review-diff` command, `review-adapter-dispatch` skill) and the repository rule `resolve-plugin-root-to-claude-mirror.md`
- **Region/Version**: PR #759 head `fa4c63986d74acff404d15f6deefb356dd315830`

## Reproduction Steps
1. Work in a session on this repository itself, where `CLAUDE_PLUGIN_ROOT` is empty and skills load from the `.claude/` mirror.
2. Check out a branch that removes the "never substitute a path inside the checkout" stop from the command or the skill, and changes `.claude/scripts/rva-*.mjs`.
3. Run the command or the dispatch skill.

## Expected Behavior
Nothing from the checkout under review runs, and nothing is sent to a vendor, whatever the branch changed.

## Actual Behavior
The stop is text the model follows: the command's step 1, the skill's run instructions and the rule's exception all come from the checkout under review, so a branch that deletes them also defeats them. The in-script check in `rva-prepare.mjs` has the same limit. The rule discloses this as guidance, not a boundary.

## Error Details
~~~
None: the missing guard produces no error.
~~~

## Visual Evidence
None.

## Impact
**Medium**: needs a hostile branch checked out in a session on this repository plus an enabled vendor; the result is the branch's code running and its content reaching a third party.

## Additional Context
Fix direction: a guard the reviewed branch cannot edit, such as a user-level `PreToolUse` hook (from `~/.claude/settings.json`, outside any checkout) that refuses a `node` call to an `rva-*.mjs` script under the current repository, or running the command only from an installed copy of the plugin. A hook shipped in the repository's own `.claude/` would sit in the checkout too, so it would not close this.

Found in PR #759 (review round 3, Major, CI Codex delta review, rule-reviewer), declined there as already disclosed:
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/759
- Head SHA: fa4c63986d74acff404d15f6deefb356dd315830
- Source: CI run 44070768314, `codex-review-result` artifact (no review thread)
- Severity: Major
