## Summary
A rule instructing "add the missing tool grant" didn't distinguish agent `tools:` frontmatter from skill/command `allowed-tools:` frontmatter — the two have incompatible syntax, so generic rule text written for one component type instructed an agent edit to add frontmatter that's actually invalid for agents.

## Environment
- **Product/Service**: `plugin-devkit` plugin — new authoring-discipline rule text (component-check-required-tool-grants class)
- **Region/Version**: this repo, found during PR #157 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Apply a rule requiring "add the exact scoped grant" to a component that adds a new Bash invocation.
2. Apply it to a skill or command: `allowed-tools` needs an exact scoped grant (e.g. `Bash(cmd:*)`) — correct.
3. Apply the same rule text to an agent: an agent's `tools` field uses bare tool names with no `Bash(...)` scoping syntax at all — this repo's own R6 rulebook check treats a scoped `Bash(...)` entry in an agent's `tools` field as itself the violation, not the fix.
4. The generic rule text, applied uniformly, directs an agent edit toward invalid frontmatter.

## Expected Behavior
Any rule, checklist, or reviewer instruction touching tool-grant frontmatter should explicitly distinguish skill/command `allowed-tools` (scoped grants required) from agent `tools` (bare names only, scoped syntax is itself wrong) — never write "add the grant" generically across both component types.

## Actual Behavior
The rule text as originally drafted would have instructed an incorrect fix when applied to an agent file, despite being correct for skills/commands.

## Impact
[Severity: Medium] Following the unqualified instruction on an agent file would introduce a new R6 violation while attempting to fix a different gap. Fixed in `plugin-devkit`'s PR #157 (commit `9cfb91b`): the "New tool grants" bullet now explicitly distinguishes the two cases, verified against `plugin-rulebook`'s R6 section directly before writing the fix.

## Additional Context
Mined from PR #157's own review history (`chatgpt-codex-connector[bot]`; 5 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #157` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This is a companion instance to `.claude/rules/verify-scope-declarations-before-finalizing.md`'s existing agent-vs-skill tool-grant guidance — this issue concerns generic rule/checklist *authoring* text conflating the two, not the calling-skill's own new-call checklist that rule already governs.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/157#discussion_r3878320333
