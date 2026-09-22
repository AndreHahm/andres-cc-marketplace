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
of exactly the scripts two plugins' hooks actually need, individually mirrored into
`_external-scripts/<plugin>/<relative-path>` by `plan_external_hook_scripts_mirror`.
This is deliberately **not** a general `plugins/*/scripts/` mirror — of the 8 plugins
with a root-level `scripts/` directory, only `context-kit` and `codex-kit` are involved
at all, and even for those two, most of their `scripts/` content (tooling, smoke tests,
etc.) has nothing to do with hooks and stays out of `.claude/` entirely:

- **`context-kit`'s 3 hook scripts are each self-contained** (stdlib-only imports) — the
  entry point alone is enough.
- **`codex-kit`'s 2 hook scripts are not self-contained, and their real closure is
  large.** Mirroring only the two entry-point files initially shipped with this broken
  — the mirrored copies couldn't even load (`ERR_MODULE_NOT_FOUND`), caught by
  cross-model review before merge. Tracing the actual dependency graph (relative
  `import`s, `new URL(..., import.meta.url)` references, and two scripts spawned
  dynamically via `path.join(...)` + `spawn()` rather than a static import) turned up
  26 files across four different locations in the plugin, not just `scripts/`:
  - `.claude-plugin/plugin.json` — read by `lib/app-server.mjs` for its own version string.
  - `prompts/stop-review-gate.md` — the prompt template `stop-review-gate-hook.mjs` loads.
  - `schemas/review-output.schema.json` — read by `codex-companion.mjs`.
  - `scripts/session-lifecycle-hook.mjs`, `scripts/stop-review-gate-hook.mjs` — the two
    entry points.
  - `scripts/codex-companion.mjs`, `scripts/app-server-broker.mjs` — spawned as
    subprocesses by the entry points/`lib/`, not statically imported.
  - Every file under `scripts/lib/` except `app-server-protocol.d.ts` (a type-only
    file, referenced only from JSDoc comments, never a runtime `import`).

  `prompts/adversarial-review.md` is deliberately excluded: it's read only by
  `codex-companion.mjs`'s `adversarial-review` subcommand, which
  `stop-review-gate-hook.mjs` never invokes (it only ever calls the `task` subcommand).
  Verified by actually executing all four entry points (both hooks,
  `codex-companion.mjs`, `app-server-broker.mjs`) from their mirrored destination —
  not just reading the source — after each newly-discovered dependency, until all four
  ran clean.

Adding a new hook that references a script outside the five component dirs requires a
new entry in `EXTERNAL_HOOK_SCRIPT_MIRRORS` — and, if that script has its own
dependencies (imports, spawned sibling scripts, or a runtime read of another file
relative to its own location), every file in that closure too, not just the entry
point. `plan_settings_hooks_sync` raises a `SyncError` if any `${CLAUDE_PLUGIN_ROOT}`
reference survives rewriting, which catches a missing *entry point*, but nothing here
automatically detects a missing *transitive dependency* of an entry that's already
listed — that still requires actually tracing the real dependency graph and executing
the mirrored copies end-to-end, the way this list itself was built, whenever one of
these scripts' own dependencies change.

## Background

See issue #374 for the gap this addresses.
