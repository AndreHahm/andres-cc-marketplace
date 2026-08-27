# Require Inventory Updates for New Plugins and Components

## When this applies

Any of the three `plugin-devkit` lifecycle pipelines (`plugin-lifecycle-upstream`,
`plugin-lifecycle-downstream`, `plugin-lifecycle-maintenance`) creates a new plugin, creates a new
component in an existing plugin, or changes an existing plugin's component list (add, remove, split, or
merge).

## Rule

- **New plugin, before finalizing:** run `marketplace-inventory` to add the plugin's record (this mints
  its `plugin_id`), get the proposed `add` operation approved via that skill's own Plan/Apply gate; then
  run `plugin-inventory` against the new plugin directory to bootstrap its own component list using the
  minted `plugin_id`, again through its own Plan/Apply approval gate. `marketplace-inventory` must run
  *before* `plugin-inventory` for a new plugin — `plugin-inventory`'s own Build mode refuses to invent a
  `plugin_id` and requires one already assigned by `marketplace-inventory`.
- **New component in an existing plugin, before finalizing:** run that plugin's own `plugin-inventory`
  (`check`/`plan`/`apply`) so the new component is proposed as an `add` operation and approved — no
  `marketplace-inventory` step needed, since it never tracks component-level records; it only reads
  `plugin-inventory.json` for rollups and referential integrity, never edits it directly.
- **A run changed an existing plugin's component list** (add, remove, split, or merge — not just a new
  component from scratch): run that plugin's own `plugin-inventory check`, propose the resulting
  operations, and get them approved the same way.
- **No silent writes.** Every `add`/`update`/`conflict` operation in both skills is gated behind that
  skill's own Plan → human `AskUserQuestion` approval → Apply-with-same-pass-hash sequence. "Run the
  skill and get its proposed addition approved" is the whole of what this rule requires — it does not
  license an unattended write, and neither skill supports one.
- **Rollout: forward-looking only**, same precedent as
  `.claude/rules/require-declared-plugin-language.md`. No retroactive requirement on plugins that predate
  this rule and have never had either inventory bootstrapped.

## Lifecycle wiring

- **`plugin-lifecycle-upstream`:** an Inventory Sync step, after the Commit step and before the Document
  step. Branches on what Build actually produced: a brand-new plugin → run `marketplace-inventory` then
  `plugin-inventory` as above; a new component in an existing plugin → run that plugin's own
  `plugin-inventory` only. Commit the result as its own commit, separate from the build commit and from
  any doc-fix commit the Document step produces.
- **`plugin-lifecycle-downstream`:** wired into Phase 12 (Handoff Finalization), alongside the Manifest
  Description Staleness Check (see below) — both share the identical trigger ("the plugin's component
  count changed during this run"). After all fix commits from earlier phases land, run the target
  plugin's own `plugin-inventory check`; if it reports drift, propose the corresponding operations for
  approval and fold the resulting commit into Phase 12's own commit record. If the run never changed the
  plugin's component list, state in the handoff report that no inventory sync was needed rather than
  silently omitting the check.
- **`plugin-lifecycle-maintenance`:** a shared Inventory Sync step, alongside the existing Document Step,
  at the same timing (after a workflow's core fix/rule-update is applied and committed, before the
  Document step's own commit). Run that plugin's own `plugin-inventory check`; propose and get approval
  for any resulting operations, committed separately, before the Document step runs.

## Trigger

"Before finalizing" — the same cadence `.claude/rules/plugin-rulebook-enforcement.md` and
[[test-against-example-plugin]] already use.

## Enforcement

More strongly enforceable than most process rules in this file: the *build-time* trigger (did the step
actually run) is a policy gate with no backing hook, same disclosed-limitation model as
[[test-against-example-plugin]]. But unlike a live dry-run or a scope-list judgment call,
`plugin-inventory check`/`marketplace-inventory check` compute `drift_count`/`missing_plugin_inventories`
mechanically from real files — a future audit pass can re-verify compliance retroactively for any
forward-looking-scoped plugin/component by just running `check`, rather than having to trust the step
happened at build time.

## Why

Verified as a real, currently-live gap, not hypothetical: `plugin-lifecycle-upstream` (the pipeline that
actually creates new plugins/components) does not reference `marketplace-inventory` or `plugin-inventory`
anywhere in its own SKILL.md, and zero real `plugin-inventory.json` or `marketplace-inventory.json` files
exist anywhere in this repo today — neither skill has ever been run for real, for any of the plugins that
predate them. Without an explicit wiring point in each pipeline, a plugin or component can be built,
reviewed, and shipped with no inventory record at all, and nothing in the existing pipelines would ever
prompt one to be created.
