## Summary
Nine `.codex/agents/*.toml` files are not in the export registry, so they are never regenerated or checked and can drift from their agent files.

## Environment
- **Product/Service**: Codex agent exports (`.codex/agents/`), `.claude/marketplace-sync.json`, `scripts/marketplace_ci` (`convert-codex-exports`, `check-codex-exports`)
- **Region/Version**: branch `fix/register-codex-agent-exports` (2026-11-13)
- **Browser/OS**: n/a

## Reproduction Steps
1. List `.codex/agents/*.toml` (26 files).
2. Compare with `codex_exports.agents` in `.claude/marketplace-sync.json` (17 entries once `command-reviewer` and `permission-reviewer` are registered).
3. Nine files have no registry entry.

## Expected Behavior
`docs/codex-subagents-schema.md` says `.codex/agents/*.toml` "is a **generated export**, not hand-authored", with `codex_exports.agents` as the registered list. Every file is either registered and regenerated from its agent file, or removed.

## Actual Behavior
These nine exports are not registered: `agent-creator`, `build-handoff-writer`, `claudemd-reviewer`, `enhancement-suggestor`, `external-references-reviewer`, `human-doc-reviewer`, `language-reviewer`, `plugin-inspector`, `skilldir-reviewer`. `convert-codex-exports` never updates them and `check-codex-exports` never compares them with their agent files.

## Error Details
~~~
None. The drift is silent.
~~~

## Visual Evidence
n/a

## Impact
**Medium** - Codex users can get stale reviewer instructions, and CI does not detect the drift. The workaround is to edit each export by hand.

## Additional Context
- #663 and #686 found the same problem in `command-reviewer` and `permission-reviewer`. Both had drifted from their agent files, and both had been made with a blind "Claude to Codex" text substitution that produced wrong paths such as `.Codex/commands/` and `.Codex/settings.json`. The nine files listed here probably have the same problem.
- Fix per file: add it to `codex_exports.agents` and run `convert-codex-exports`, or delete it if the agent should not be exported.
- Related: #663, #686, #700.
