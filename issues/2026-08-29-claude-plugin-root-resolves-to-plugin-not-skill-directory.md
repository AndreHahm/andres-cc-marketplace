## Summary
`CLAUDE_PLUGIN_ROOT` resolves to the plugin's root directory, not an individual skill's own directory — every script reference in a new skill must explicitly include the `skills/<skill-name>/` segment, or every call fails.

## Environment
- **Product/Service**: `git-kit` plugin (`resolving-merge-conflicts`)
- **Region/Version**: this repo, found during PR #143 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Write a new skill's `SKILL.md` and `allowed-tools` referencing its own helper scripts as `"${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh"`.
2. Install/run the plugin. `CLAUDE_PLUGIN_ROOT` resolves to `<plugin-root>`, not `<plugin-root>/skills/<skill-name>`.
3. The skill's helper scripts actually live under `<plugin-root>/skills/<skill-name>/scripts/`, not `<plugin-root>/scripts/`.
4. Every call in the skill's own Steps 1, 3, and 5 fails with "No such file or directory."

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/scripts/<name>` resolves to a skill's own local scripts directory | `CLAUDE_PLUGIN_ROOT` is the *plugin's* root; a skill-local reference needs the explicit `skills/<skill-name>/` segment |

## Expected Behavior
Any reference to a skill-local script/resource should explicitly include the `skills/<skill-name>/` segment: `"${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/scripts/<name>.sh"`.

## Actual Behavior
Every helper-script invocation in this newly-built skill failed, blocking its entire core workflow, because the skill-directory segment was omitted.

## Impact
[Severity: High] This was a severe, genuine bug — every script invocation in the skill was broken from the start. Fixed in `git-kit`'s PR #143 (commit `0bb9d72`), confirmed against direct precedent: `analysis-kit` and `codex-kit` both already reference their own skill-local files with the `skills/<name>/...` segment included. Added the missing segment to both `allowed-tools` and every call site.

## Additional Context
Mined from PR #143's own review history (`chatgpt-codex-connector[bot]`; 24 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #143` section, marked `### Self-caught`) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This is a previously-undocumented, concrete fact about Claude Code's own `CLAUDE_PLUGIN_ROOT` semantics worth naming explicitly so a future new-skill build doesn't repeat it.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/143#discussion_r3861476754
