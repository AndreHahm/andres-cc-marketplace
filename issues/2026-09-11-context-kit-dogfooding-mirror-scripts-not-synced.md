## Summary
`scripts/marketplace_ci/sync.py`'s plugin-mirror sync only copies `skills/agents/commands/hooks/rules` into `.claude/`, never `scripts/` — so any plugin's Python/Node-script-backed hook entry that gets merged into `.claude/hooks/hooks.json` (via `plan_hooks_merge`) resolves to a `${CLAUDE_PLUGIN_ROOT}/scripts/...` path that is never created there, breaking that hook under the in-repo `.claude/` dogfooding setup. Newly registering `context-kit` as a plugin mirror (PR #304) is what surfaced this for its 3 Python-backed hooks, but the root cause is pre-existing, generic sync infrastructure, not something scoped to `context-kit` — other already-mirrored plugins' script-backed hook entries in `.claude/hooks/hooks.json` (e.g. `session-lifecycle-hook.mjs`, `stop-review-gate-hook.mjs`) share the identical gap.

## Environment
- **Product/Service**: `andres-cc-marketplace` — `scripts/marketplace_ci` plugin-mirror sync tooling
- **Region/Version**: n/a
- **Browser/OS**: n/a (repo-internal tooling; confirmed by direct code read, not yet reproduced live against a running Claude Code session)

## Reproduction Steps
1. Register any plugin with a Python/Node-backed hook (e.g. `context-kit`, whose `hooks/hooks.json` runs `${CLAUDE_PLUGIN_ROOT}/scripts/context-monitor.py`) as a `plugin_mirrors` entry in `.claude/marketplace-sync.json`.
2. Run `uv run python -m scripts.marketplace_ci sync-plugin-mirrors`.
3. Inspect `scripts/marketplace_ci/sync.py`'s `COMPONENT_DIRS = ("skills", "agents", "commands", "hooks", "rules")` (line 16) — `scripts` is absent, so `_iter_component_files` never yields anything under `plugins/<name>/scripts/`, and no destination under `.claude/scripts/` is ever planned or created.
4. `plan_hooks_merge` (same file, line 274) merges each mirrored plugin's `hooks/hooks.json` into `.claude/hooks/hooks.json` as a raw byte-for-byte JSON merge with **no path rewriting** — `${CLAUDE_PLUGIN_ROOT}` is left verbatim in every merged command string.
5. When Claude Code loads hooks from the project's own `.claude/hooks/hooks.json` (not from an installed marketplace plugin), there is no enclosing plugin context — this repo's own precedent (`.claude/marketplace-sync.json`'s existing `divergence_exceptions` entry for `plugins/plugin-devkit/skills/marketplace-development/SKILL.md`) explicitly documents `${CLAUDE_PLUGIN_ROOT}` as "confirmed-broken for a project-level skill with no enclosing plugin" in exactly this dogfooding context.

## Expected Behavior
Every hook command merged into `.claude/hooks/hooks.json` should resolve to a script that actually exists on disk under the `.claude/` dogfooding checkout, the same way the plugin's own canonical `plugins/<name>/hooks/hooks.json` resolves correctly when the plugin is actually installed via the marketplace.

## Actual Behavior
For `context-kit` specifically: all 3 Python-backed hook entries (`context-monitor.py`, `pre-compact.py`, `post-compact-restore.py`) in the merged `.claude/hooks/hooks.json` reference `${CLAUDE_PLUGIN_ROOT}/scripts/<file>.py`, which never exists under `.claude/` (only under `plugins/context-kit/scripts/`) — so all 3 hooks fail with a missing-file error whenever they execute via the `.claude/` mirror, even though the real installed plugin works correctly.

## Error Details
~~~
Not yet reproduced against a live Claude Code hook execution — confirmed by direct code read only:
- scripts/marketplace_ci/sync.py:16 COMPONENT_DIRS excludes "scripts"
- scripts/marketplace_ci/sync.py:274-326 plan_hooks_merge does no ${CLAUDE_PLUGIN_ROOT} rewriting
- .claude/hooks/hooks.json:32 (and its 2 sibling context-kit entries) reference
  ${CLAUDE_PLUGIN_ROOT}/scripts/context-monitor.py, which .claude/scripts/ never contains
~~~

## Visual Evidence
None.

## Impact
Medium (P2, per Codex's own review label — no upgrade warranted; this breaks dogfooding-only tooling, not anything shipped to real plugin installs). All 3 context-kit hooks currently silently no-op or error under the `.claude/` dogfooding checkout specifically (their `onError: "warn"` config means this fails open, not loudly) — real plugin installs via the marketplace are unaffected, since those resolve `${CLAUDE_PLUGIN_ROOT}` correctly to the installed plugin's own root.

## Additional Context
- **Found in PR #304**: https://github.com/AndreHahm/andres-cc-marketplace/pull/304
- **Head SHA at time of finding**: `fa489a772b62e576902b71b641ebc7157ac81e17`
- **Reviewer**: Codex (`chatgpt-codex-connector[bot]`), round 2, review id `5181650537`
- **Thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/304#discussion_r3991772278 (comment id `3991772278`)
- **Severity**: P2 (Codex's own label; not escalated on review — a dogfooding-only tooling gap, not a correctness/security issue for real installs)

**Why filed instead of fixed in this PR**: the bug is real, but its root cause is pre-existing, shared sync infrastructure (`scripts/marketplace_ci/sync.py`'s `COMPONENT_DIRS` and `plan_hooks_merge`) used by every mirrored plugin, not something introduced by or scoped to `context-kit`. A correct fix needs new mechanism design — either mirroring `scripts/` into `.claude/` for every plugin (COMPONENT_DIRS change, repo-wide blast radius) or extending `plan_hooks_merge` to rewrite `${CLAUDE_PLUGIN_ROOT}` per source plugin into a `${CLAUDE_PROJECT_DIR}`-relative path (new per-entry rewriting logic for what is currently an N:1 merge with no per-entry provenance tracking, and no existing hook to the `divergence_exceptions` model, which is built for 1:1 file mirrors only). Both options need their own design decision, implementation, and test coverage — out of scope for a plugin-registration PR, and too large to fix in this session per `.claude/skills/handling-review-findings/references/settings-and-round-budget.md`'s named exceptions.

**Suggested next step**: decide between the two fix shapes above (or a third), then implement in `scripts/marketplace_ci/sync.py` with test coverage, and sweep every other already-mirrored plugin's `hooks/hooks.json` for the same `${CLAUDE_PLUGIN_ROOT}` pattern once fixed — this almost certainly isn't unique to `context-kit`.
