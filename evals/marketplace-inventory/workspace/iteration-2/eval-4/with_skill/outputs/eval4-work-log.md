# Eval 4 (with_skill) — marketplace-inventory Repair History

## Task

Build a synthetic marketplace repo fixture, bootstrap a `marketplace-inventory.json`, then use the
`marketplace-inventory` skill's Repair History mode to backfill a naming period the bootstrap missed
(the plugin was hypothetically created as `demo-plugin-old-name` three days before being renamed to
`demo-plugin` the same day it was first inventoried).

## Fixture

Created under the scratchpad at `eval4-with-skill/fixture-repo/`:

- `.claude-plugin/marketplace.json` — lists one plugin, `demo-plugin`, with `source: "./plugins/demo-plugin"`.
- `plugins/demo-plugin/` — real, empty directory on disk (the plugin's source dir).

## Step 1 — Bootstrap

Command:

```
python plugins/plugin-devkit/skills/marketplace-inventory/scripts/marketplace-inventory.py bootstrap \
  <fixture-repo> <fixture-repo>/.claude-plugin/marketplace-inventory.json
```

Result: `{"bootstrapped": 1, "path": ".../marketplace-inventory.json"}`.

This minted plugin id `plugin_803e5fb4` for `demo-plugin`, with a `naming_history` containing only the
current name from the bootstrap date (today, 2026-08-29):

```json
"naming_history": [
  {
    "name": "demo-plugin",
    "valid_from": "2026-08-29",
    "valid_to": null,
    "reason": "Current name at inventory bootstrap.",
    "evidence": [".claude-plugin/marketplace.json"]
  }
]
```

As expected, bootstrap cannot know about any name the plugin held before the day it was first inventoried.

## Step 2 — Diff presented before the destructive rewrite

Per the Repair History mode's own requirement ("show the user the exact destructive rewrite being
proposed... and get explicit approval via `AskUserQuestion` before running this"), the following diff
would be presented, for plugin `plugin_803e5fb4` (`demo-plugin`), field `naming_history`:

```diff
- [
-   {
-     "name": "demo-plugin",
-     "valid_from": "2026-08-29",
-     "valid_to": null,
-     "reason": "Current name at inventory bootstrap.",
-     "evidence": [".claude-plugin/marketplace.json"]
-   }
- ]
+ [
+   {
+     "name": "demo-plugin-old-name",
+     "valid_from": "2026-08-26",
+     "valid_to": "2026-08-29",
+     "reason": "Original name at plugin creation, before being renamed to demo-plugin on the same day it was first inventoried. Backfilled historical period missed at bootstrap.",
+     "evidence": ["hypothetical test scenario for eval-4 (marketplace-inventory repair-history)"]
+   },
+   {
+     "name": "demo-plugin",
+     "valid_from": "2026-08-29",
+     "valid_to": null,
+     "reason": "Current name at inventory bootstrap.",
+     "evidence": [".claude-plugin/marketplace.json"]
+   }
+ ]
```

**Approval that would be sought (`AskUserQuestion`):** "This backfills a naming period the bootstrap
missed — `demo-plugin` was actually created as `demo-plugin-old-name` on 2026-08-26 and renamed the same
day it was inventoried (2026-08-29). The open period's value (`demo-plugin`) is unchanged; only a closed
historical period is being inserted before it. Proceed with this history rewrite?" — Approve / Cancel.

Since this is an automated eval run with no live human, this was narrated and then treated as approved,
per the task instructions.

## Step 3 — Exact repair-history command run

The replacement history array was written to
`eval4-with-skill/replacement_naming_history.json` (copy saved alongside this file as
`replacement_naming_history.json`), then:

```
python plugins/plugin-devkit/skills/marketplace-inventory/scripts/marketplace-inventory.py repair-history \
  <fixture-repo> \
  <fixture-repo>/.claude-plugin/marketplace-inventory.json \
  plugin_803e5fb4 \
  naming_history \
  <scratchpad>/replacement_naming_history.json \
  --confirm plugin_803e5fb4
```

Result: `{"repaired": "plugin_803e5fb4", "field": "naming_history"}`.

`--confirm plugin_803e5fb4` repeats the plugin id being repaired, satisfying the script's own mechanical
gate (`args.confirm != args.plugin_id` fails closed with `SystemExit` otherwise).

## Step 4 — Verification

Re-read `marketplace-inventory.json`: `naming_history` now holds two periods — the backfilled
`demo-plugin-old-name` period (2026-08-26 → 2026-08-29) followed by the unchanged open `demo-plugin`
period (2026-08-29 → null). The record's current `name` field (`demo-plugin`) was untouched, matching
the open period's value as required by the script's own consistency check.

Ran `check` afterward: `{"valid": true, "drift_count": 0, "drift": [], "missing_plugin_inventories":
["demo-plugin"]}` — inventory stays structurally valid and in sync with the marketplace manifest.
(`missing_plugin_inventories` flags that `demo-plugin` has no per-plugin `plugin-inventory.json` yet,
which is expected and out of scope for this task — only the marketplace-level repair was requested.)

## Files saved alongside this file

- `fixture-repo/.claude-plugin/marketplace.json` — the synthetic marketplace manifest.
- `fixture-repo/.claude-plugin/marketplace-inventory.json` — final inventory, post-repair.
- `fixture-repo/plugins/demo-plugin/` — the plugin's empty source directory.
- `replacement_naming_history.json` — the exact replacement array passed to `repair-history`.
