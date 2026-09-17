## Summary
antigravity-kit's mirrored commands are name-reachable via the shared shorthand namespace but non-functional unless the plugin is also separately installed

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `scripts/marketplace_ci/sync.py`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. `antigravity-kit` is registered in `.claude/marketplace-sync.json`'s `plugin_mirrors` (#335's fix) and `sync-plugin-mirrors` has been run.
2. Without separately installing the `antigravity-kit` plugin (`/plugin install antigravity-kit@andres-cc-marketplace`) or manually adding `plugins/antigravity-kit/bin` to `PATH`, run the mirrored `/agy-setup` command (or any of the other 9 mirrored commands).
3. Observe the command attempts to run a bare executable name (`agy-doctor`, `agy-delegate`, `agy-job`, `agy-media`, `agy-migrate`, or `agy-cloud-debug`, depending on the command) that resolves to nothing.

## Expected Behavior
A command reachable via the shared shorthand namespace should actually run, the same as every other registered plugin's mirrored commands.

## Actual Behavior
Every one of antigravity-kit's 10 mirrored commands invokes a bare executable that lives in `plugins/antigravity-kit/bin/`. Per Claude Code's own official documentation (`code.claude.com/docs/en/plugins-reference`, fetched live): "`bin/`: Executables added to the Bash tool's `PATH` **while the plugin is enabled**" — this is a plugin-only mechanism. The same docs' own migration-steps table (for converting a standalone `.claude/` config into a plugin) doesn't even list `bin/` as something a standalone/project-level `.claude/` directory can have. There is no equivalent PATH-granting mechanism for a project-level mirror, so a mirrored command that depends on a `bin/` script cannot function unless the real plugin is *also* separately installed in that same session — in which case the fully-qualified `/antigravity-kit:<name>` form already worked, and the mirror added nothing but a name that looks reachable and silently fails.

`antigravity-kit` is the first plugin registered in `plugin_mirrors` with a `bin/` directory at all — no prior registered plugin exercised this gap.

## Impact
**Medium** — not a data-loss or security issue, but a real "looks like it works, fails silently" trap: a user (or an agent) in this repo who tries `/agy-setup` without the real plugin installed gets a bare command-not-found failure with no indication the mirror itself is the reason. Skills (`antigravity`, `migrate-to-antigravity`) are unaffected by this specific gap — skill matching/discovery isn't gated by `bin/` PATH — but any Bash command they instruct (which also invokes the same `bin/`-resident executables) hits the identical failure once actually executed.

## Additional Context
Found by Codex's automated PR review of #349 (the mirror-sync registration fix), and independently verified against Claude Code's official docs rather than the review's own citation (which pointed at unrelated `AGENTS.md` lines). This is a structural limitation, not something `scripts/marketplace_ci/sync.py` can be extended to fix — `bin/`'s PATH-granting behavior has no project-level (`.claude/`) equivalent per the platform's own documented plugin/standalone distinction. Suggested remediation options, none prescriptive:
1. Accept as a documented, permanent limitation for any `bin/`-dependent plugin registered in `plugin_mirrors` (this plugin's own `KNOWN_ISSUES.md` convention).
2. Rewrite antigravity-kit's commands to invoke `bin/` scripts via an absolute, plugin-qualified path instead of a bare PATH-resolved name — would need `${CLAUDE_PLUGIN_ROOT}` (works when the plugin is installed) but has no working equivalent for the mirror either, so this doesn't actually fix the mirrored copy.
3. Reconsider whether a `bin/`-dependent plugin should be registered in `plugin_mirrors` at all, given the shorthand can't ever deliver working functionality independent of a full plugin install.

This is a decision-tracking issue — the next step is choosing among these options (most likely option 1, given options 2-3 don't have a real technical resolution), not implementing one now.
