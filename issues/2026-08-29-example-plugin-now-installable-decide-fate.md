## Summary
example-plugin (this repo's internal test fixture) is now registered in `.claude-plugin/marketplace.json` and genuinely installable via `/plugin` — decide whether that should stand, and if so, whether its docs need a disclaimer.

## Environment
- **Product/Service**: andres-cc-marketplace catalog (`.claude-plugin/marketplace.json`)
- **Region/Version**: N/A

## Reproduction Steps
N/A — not a bug. Sequence of events that created the situation:
1. `example-plugin` has existed on disk at `plugins/example-plugin/` for a while, used only as the dry-run target named in `.claude/rules/test-against-example-plugin.md` (the fixture 21 agents + 9 skills in `plugin-devkit` validate themselves against).
2. It was never listed in `.claude-plugin/marketplace.json` and so was never actually installable.
3. As a live end-to-end test of the `marketplace-inventory`/`plugin-inventory` workflow, it was registered for real (commit `6156af1`, branch `chore/bootstrap-marketplace-plugin-inventory`) and given its own `plugin-inventory.json` (3 components: 1 skill, 1 agent, 1 command).
4. `claude plugin validate` passed, and `marketplace-inventory check` now shows it as a normal `active` catalog entry with zero drift.

## Expected Behavior
N/A (not a bug) — flagging for a decision, not a defect.

## Actual Behavior
`example-plugin` is now a real, publicly-installable marketplace entry, indistinguishable from the four real toolkits (`plugin-devkit`, `git-kit`, `analysis-kit`, `codex-kit`) to anyone browsing or installing from this marketplace — but its `plugin.json`/README give no indication it's a test fixture rather than a working tool (`description: "Example plugin demonstrating command structure"`).

## Impact
**Low** — no functional breakage, but a real user installing `example-plugin` expecting a working tool would get a minimal fixture with no real capability, which is a legitimate (if minor) confusion/trust cost for the marketplace as a whole.

## Additional Context
Two decisions to make, not mutually exclusive:
1. **Keep it installable, or pull it back out of `marketplace.json`?** Its only established purpose to date is as `plugin-devkit`'s own internal dry-run fixture (`test-against-example-plugin.md`) — nothing currently requires it to be publicly installable. If there's no real use case for someone installing it standalone, consider removing the `marketplace.json` entry (leaving the plugin on disk for the existing fixture role) rather than leaving a placeholder plugin live in the catalog indefinitely.
2. **If it stays installable**, its `plugin.json` description and `README.md` should say plainly that it's a minimal internal test/reference fixture, not a tool meant for general use — so it doesn't read as a genuine offering next to the marketplace's four real plugins.

Related: `.claude/rules/test-against-example-plugin.md` (the fixture's only documented real purpose today); `plugins/example-plugin/.claude-plugin/plugin.json`; `.claude-plugin/marketplace.json`.
