## Summary
antigravity-kit cannot be registered in Mirror Sync because 5 of its command names collide with existing codex-kit commands

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `.claude/marketplace-sync.json` / `scripts/marketplace_ci/`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. Add `antigravity-kit` to `.claude/marketplace-sync.json`'s `plugin_mirrors` list.
2. Run `sync-plugin-mirrors --stage`.
3. Observe the sync fails: `cancel`, `result`, `review`, `setup`, and `status` all collide with existing `codex-kit` commands already registered in the same shared flat `.claude/commands/` namespace.

## Expected Behavior
`antigravity-kit`'s commands should be reachable via the shared shorthand namespace, the same as every other registered plugin's commands.

## Actual Behavior
Registration is blocked outright; `antigravity-kit`'s commands remain reachable only via their fully-qualified `/antigravity-kit:<name>` form.

## Impact
**Low-Medium** — a discoverability/ergonomics gap, not a functional break. `antigravity-kit`'s commands work fine via their fully-qualified form; they just don't get the shared-namespace shorthand every other registered plugin gets.

## Additional Context
Discovered during the `antigravity-kit` plugin transfer (branch `feat/add-antigravity-kit`) and disclosed in `plugins/antigravity-kit/KNOWN_ISSUES.md` with 3 documented remediation options, none yet chosen:
1. Rename `antigravity-kit`'s 5 colliding commands to something less generic.
2. Extend the mirror-sync tooling (`scripts/marketplace_ci/`) to support a per-plugin namespace prefix instead of one flat shared list.
3. Accept fully-qualified-only `/antigravity-kit:<name>` invocation as a permanent limitation for this plugin.

This is a decision-tracking issue, not an implementation request — the next step is choosing among the 3 options above, not implementing one now.
