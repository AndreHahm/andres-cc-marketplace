# Marketplace Inventory — Baseline Run (no skill)

## What I did

1. Explored the repo (no dedicated skill was available) and found the relevant tooling at
   `.claude/skills/marketplace-inventory/scripts/marketplace-inventory.py`, which builds/maintains
   `.claude-plugin/marketplace-inventory.json` by reading `.claude-plugin/marketplace.json` and each
   plugin's own `.claude-plugin/plugin-inventory.json`.
2. Ran `discover <repo_root>` against the real repo to list the plugins named in
   `.claude-plugin/marketplace.json`: `analysis-kit`, `codex-kit`, `git-kit`, `plugin-devkit`.
3. The script's `bootstrap`/`apply`/`import-grading`/`repair-history` subcommands mechanically refuse to
   write anywhere except `<repo_root>/.claude-plugin/marketplace-inventory.json` (a hard scope guard in
   `reconcile.require_inventory_path_under_scope_dir`). Since the task required writing to the
   scratchpad rather than the repo's real inventory file, I built a small mirror repo root entirely
   under the scratchpad:
   - `<scratch>/eval1-baseline/mirror-repo/.claude-plugin/marketplace.json` (copy of the real one)
   - `<scratch>/eval1-baseline/mirror-repo/plugins/<plugin>/.claude-plugin/plugin-inventory.json`
     (copies of each real plugin's own inventory file, for each of the 4 plugins)

   This let me run `bootstrap`/`check` with `repo_root` pointed at the scratch mirror (satisfying the
   script's own path guard) while reading the *real* plugin-inventory data, without ever writing to
   `C:\Dev\Repos\andres-cc-marketplace\.claude-plugin\marketplace-inventory.json` (the real repo was
   never modified — confirmed no writes occurred there).
4. Ran:
   ```
   python .claude/skills/marketplace-inventory/scripts/marketplace-inventory.py bootstrap <mirror_repo_root> <mirror_repo_root>/.claude-plugin/marketplace-inventory.json
   python .claude/skills/marketplace-inventory/scripts/marketplace-inventory.py check     <mirror_repo_root> <mirror_repo_root>/.claude-plugin/marketplace-inventory.json
   ```

## Results

- **Bootstrap**: `{"bootstrapped": 4, "path": "...marketplace-inventory.json"}` — 4 plugins found and
  written: `analysis-kit`, `codex-kit`, `git-kit`, `plugin-devkit`. Each plugin already carried a
  `plugin_id` in its own `plugin-inventory.json`, and bootstrap correctly reused those exact IDs
  (`plugin_97cc39b8`, `plugin_29c58158`, `plugin_8b374e26`, `plugin_7e527600`) rather than minting new
  ones.
- **Check**:
  ```json
  {
    "valid": true,
    "drift_count": 0,
    "drift": [],
    "missing_plugin_inventories": []
  }
  ```
  `missing_plugin_inventories` is **empty** — all 4 plugins already have their own readable
  `plugin-inventory.json` with a `plugin_id` that matches this marketplace record, so there is nothing
  stale or missing to reconcile.

## What I'd offer to do next (per the Repair Plugins documentation)

The skill's SKILL.md documents the Repair Plugins mode as: *"After explicit user approval, invoke
`plugin-inventory` (via `Skill`) separately for each selected plugin from `missing_plugin_inventories`
... then re-run this skill's own `plan`/`check` to confirm the list shrank. Never invoke
`plugin-inventory` without asking first, and never batch-apply across multiple plugins in one call."*

Because `missing_plugin_inventories` came back **empty** in this run, there is nothing to repair — I
would not invoke Repair Plugins at all, and would simply report that every discovered plugin already has
a valid, cross-referenced `plugin-inventory.json`.

If the list had been non-empty (say it had contained `"some-plugin"`), the correct next step per this
same documentation would be to ask the user for approval first, and then, for each approved plugin
individually (never batched), run:

```
Skill(plugin-inventory) with args: "<plugin_dir> build"
```

e.g. concretely: `Skill(plugin-inventory)` with args `"./plugins/some-plugin build"` — one such call per
approved plugin, followed by re-running this skill's own `plan`/`check` to confirm the missing list
shrank.

## Files

- `marketplace-inventory.json` — the bootstrapped inventory (built under the scratch mirror repo, never
  touching the real repo's own file)
- `check-output.json` — raw output of the `check` subcommand run against it
