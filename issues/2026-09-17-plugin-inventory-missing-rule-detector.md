## Summary
`plugin-inventory`'s discovery tooling has no detector for the `rule` component type

## Environment
- **Product/Service**: plugin-devkit's `plugin-inventory` skill
- **Region/Version**: N/A

## Reproduction Steps
1. Open `plugins/plugin-devkit/skills/plugin-inventory/scripts/plugin-inventory.py`.
2. Inspect `CONVENTION_DETECTED_TYPES` — currently `("skill", "agent", "command", "hook")`.
3. Attempt to have `plugin-inventory check`/`plan` discover a plugin's `rules/*.md` components.

## Expected Behavior
`plugin-inventory` should be able to detect and track `rule` components the same way it already
detects skills/agents/commands/hooks, so a new rule component can go through the normal
`check`/`plan`/`apply` inventory flow.

## Actual Behavior
`rule` (and `output-style`/`theme`/`monitor`/`custom`) components have no detector at all — they must
be added manually via a plan operation. A newly-created rule component cannot be auto-discovered or
tracked for drift.

## Impact
**Medium** — no functional break to existing tooling, but every new rule component in this marketplace
silently falls outside inventory tracking unless someone remembers to add it by hand. This has already
happened for at least one real rule component (see Additional Context).

## Additional Context
Discovered/confirmed during a 2026-09-16/17 `plugin-lifecycle-downstream` QA session on plugin-devkit's
`marketplace-documentation` feature: the session's own new rule component,
`keep-marketplace-root-docs-in-sync.md`, could not be inventoried for this reason and was left as a
documented, out-of-scope gap. Suggested fix: add a `rules/` detection branch to
`discover_filesystem_components()` in `plugin-inventory.py` and add `"rule"` to
`CONVENTION_DETECTED_TYPES`, resolving first which directory is canonical for a rule component in a
shipped plugin (see `.claude/rules/verify-rule-scope-before-lazy-loading.md`'s "Canonical source"
section). This is deterministic script logic — per `.claude/rules/require-tests-for-behavior-changes.md`
it should be verified via direct execution against `example-plugin` (already an in-scope fixture per
`.claude/rules/test-against-example-plugin.md`'s `plugin-inventory` listing), not agent-based testing.
