Question: plugin-lifecycle-upstream just finished Phase 5 (Build) and produced a brand-new plugin
called `widget-kit`, which is not present in `.claude/marketplace-sync.json`'s `plugin_mirrors` list.
The Commit step already ran, and Inventory Sync just finished. What does the Mirror Sync step do next,
and what happens if the user answers 'Yes'?

Answer (based on the skill's "Mirror Sync" section):

Mirror Sync is described as "This repository's own dogfooding step only — a no-op if
`scripts/marketplace_ci/` and `.claude/marketplace-sync.json` don't exist." It runs "after Inventory
Sync and before Document" — which matches where we are here (Commit → Inventory Sync just finished,
Mirror Sync is next, Document comes after). It is explicitly "a separate registry from
`marketplace-inventory`/`plugin-inventory`" (component database vs. `.claude/` mirror parity), so "it
needs its own check and its own ask, never inferred from Inventory Sync's outcome."

Since Phase 5 (Build) produced a brand-new plugin directory under `plugins/` (widget-kit, not just a
new component inside an already-existing plugin), the skill says to "read
`.claude/marketplace-sync.json` and check whether the plugin's name is already present in
`plugin_mirrors`." Because widget-kit is not present in that list, the skill does NOT treat this as
"nothing to do." Instead it must ask via `AskUserQuestion`:

"Register `<plugin-name>` in `.claude/marketplace-sync.json`'s `plugin_mirrors`, so its
skills/agents/commands/hooks/rules sync into `.claude/`?"

with options:
- "Yes — add and sync"
- "No — skip for now"

The skill states plainly: "Never add the entry without this ask."

If the user answers "Yes", the skill's documented sequence is:

1. `Edit` the plugin's name into `plugin_mirrors` (i.e., add `widget-kit` to the
   `.claude/marketplace-sync.json` `plugin_mirrors` list).
2. Run `uv run python -m scripts.marketplace_ci sync-plugin-mirrors --stage` directly via the scoped
   `Bash(uv run python -m scripts.marketplace_ci:*)` tool.
3. Then run `uv run python -m scripts.marketplace_ci check-plugin-mirrors` to confirm parity.
4. Explicitly: "never hand-write a file under `.claude/skills|agents|commands|hooks|rules/` yourself;
   only the sync command's own generated output goes there."
5. "Commit the registry edit and the synced files together as their own commit, separate from the
   build commit, the Inventory Sync commit (if one landed), and any doc-fix commit Document produces
   below."

(For completeness, per the skill: if the user had answered "No" instead, it would "state plainly that
the new plugin's own components won't be loadable as this repo's own project skills until mirroring is
registered later — a deferred decision, not a silent skip — then move on to Document." This branch does
not apply here since the question asks specifically about the "Yes" answer.)
