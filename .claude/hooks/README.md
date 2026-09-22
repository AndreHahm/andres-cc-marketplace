# `.claude/hooks/`

`hooks.json` in this directory is **generated**, not hand-written. It's produced by
`scripts/marketplace_ci/sync.py`'s `plan_hooks_merge` / `apply_hooks_merge_plan`
(run via `python -m scripts.marketplace_ci sync-plugin-mirrors` or `repair-all`),
which does a byte-for-byte JSON merge of every registered plugin's own
`plugins/<name>/hooks/hooks.json`, plus the repo-owned fragment at
`scripts/marketplace_ci/hooks/hooks.json`.

**Never hand-edit `hooks.json` directly.** Edit the owning plugin's own
`hooks/hooks.json` (or the repo-owned fragment) and re-run sync — a direct edit here
is silently overwritten the next time sync runs.

## Why `hooks.json` itself still isn't directly executable

Every merged entry keeps `${CLAUDE_PLUGIN_ROOT}` exactly as it appears in its owning
plugin's own manifest. That variable only resolves when Claude Code loads a hook from
an actually-installed plugin's own manifest — it's unset for project-level hook
execution. So this file, on its own, stays a merged *reference* view of every
registered plugin's hooks in one place, not something safe to wire into
`.claude/settings.json`'s `hooks` key as-is (see issue #374).

## The live copy: `.claude/settings.json`

`sync.py` separately derives a project-relative copy of this same merged content
(`plan_settings_hooks_sync`) and writes it into `.claude/settings.json`'s own `hooks`
key, rewriting every `${CLAUDE_PLUGIN_ROOT}` reference to
`${CLAUDE_PROJECT_DIR}/.claude/...` so it resolves correctly from a project-level hook
execution context. **That copy is the one that's actually live** — `hooks.json` in
this directory stays the unmodified, plugin-manifest-shaped reference copy described
above.

## `_external-scripts/`

A handful of hook commands reference a script outside the five mirrored component
directories (`skills/`, `agents/`, `commands/`, `hooks/`, `rules/`) — in every current
case, a plugin's own root-level `scripts/` directory. Those paths have no mirrored
counterpart under `.claude/` by default, so `plan_settings_hooks_sync`'s rewrite has
nowhere to point without one.

`sync.py`'s `EXTERNAL_HOOK_SCRIPT_MIRRORS` is a small, explicit, hand-maintained list
of exactly these scripts (5 files, from `codex-kit` and `context-kit`), individually
mirrored into `_external-scripts/<plugin>/<relative-path>` by
`plan_external_hook_scripts_mirror`. This is deliberately **not** a general
`plugins/*/scripts/` mirror — across the 8 plugins that have a root-level `scripts/`
directory, only these 5 of 122 files are ever referenced by a hook; the rest (tooling,
skill implementation scripts, etc.) have nothing to do with hooks and stay out of
`.claude/` entirely.

Adding a new hook that references a script outside the five component dirs requires a
new entry in `EXTERNAL_HOOK_SCRIPT_MIRRORS`. `plan_settings_hooks_sync` raises a
`SyncError` if any `${CLAUDE_PLUGIN_ROOT}` reference survives rewriting, so a missed
addition is a build-time failure, not a silently broken hook path.

## Background

See issue #374 for the gap this addresses.
