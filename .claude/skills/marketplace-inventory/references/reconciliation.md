# Marketplace Reconciliation

`scripts/marketplace-inventory.py plan <repo_root> <inventory_path>` compares
`.claude-plugin/marketplace.json`'s current installable plugin list against the canonical inventory's
own active records, and separately reports whether each candidate plugin has a real, readable
`plugin-inventory.json` of its own.

## Reconciliation Operations

Same deterministic vocabulary as `plugin-inventory`, at plugin scope:

| Operation | Meaning |
|---|---|
| `add` | A plugin in `marketplace.json` with no matching canonical record yet |
| `update` | An existing active record whose `source` path changed |
| `conflict` | Any canonical record (regardless of status) whose `plugin-inventory.json` disagrees on `plugin_id`; an *active* record missing from the current manifest entirely; **or a discovered candidate matching an existing *non-active* record (planned/deprecated/superseded/retired) — always a `conflict`, requiring a status-transition decision, never automatic** |
| `no-op` | An *active* record whose `source` matches — the only case that resolves to `no-op` |

Every `add`/`update`/`conflict` carries `requires_approval: true` — this script never applies one on
its own; the calling skill collects human decisions first, exactly like `plugin-inventory`. A `conflict`
is never applied as its own shape — its resolution becomes a `status-transition` operation instead (see
`SKILL.md`'s Plan mode section).

**A non-active record match is never a `no-op`.** When a discovered candidate matches an existing
non-active record (planned/deprecated/superseded/retired), `build_plan()` unconditionally surfaces a
`conflict` — regardless of `plugin_id` status — requiring a human status-transition decision, the same
guarantee `SKILL.md`'s own Failure Handling section states ("Non-active record reappears... is surfaced
as a `conflict`... never a silent `no-op`", also `scripts/smoke_test.py`'s `check_non_active_reappearance_conflict`,
scenario 12). This was the fix for a cross-model-review finding that an earlier version of `build_plan()`'s
discovery loop only ever compared against `active` records, silently no-op'ing a planned/retired/
deprecated/superseded record's reappearance — that gap is closed, and this file previously still
documented the pre-fix behavior.

## Missing Plugin Inventories

`plan`/`check`'s own `missing_plugin_inventories` list is **not** a reconciliation operation — it's a
referential-integrity report. A plugin candidate whose own `plugin-inventory.json` doesn't exist yet (or
fails to parse) is reported by name so the calling skill can offer to invoke `plugin-inventory` for it —
**only after explicit user approval**, and only as a separate `plugin-inventory` invocation per selected
plugin, never a direct write from this script. This mirrors the concept's own ownership boundary:
`marketplace-inventory` reads plugin inventories for referential integrity and rollups, and repairs them
only by delegating, never by writing them itself.

## The `conflict` Case: `plugin_id` Mismatch

If a plugin's own `plugin-inventory.json` exists but its `plugin_id` field doesn't match the marketplace
record's `id` for that same plugin name, this is surfaced as a `conflict` — never silently trusted from
either side. Resolving it needs a human decision about which `plugin_id` is actually correct (a stale
plugin-inventory.json from before a rename, or a marketplace record that drifted) — this script only
detects and reports the mismatch.

## Rollup Fields Are Import-Only

`score`/`security_score` on a marketplace plugin record are populated only by
`import-grading`, from a completed whole-plugin `plugin-grader` report (`plugin_final_score`/
`plugin_security_score`) — never derived from that plugin's own component-level scores. Deriving a
plugin-level score from its components would duplicate `plugin-grader`'s own whole-plugin rollup
math (a violation of "plugin-grader is the sole quality- and security-scoring authority" — see
`inventory_common/grading.py`'s own module docstring). If a whole-plugin report simply hasn't been imported yet, `score`/
`security_score` stay `null`; this script never fabricates a substitute. `import-grading` itself
rejects any `target_type` other than `plugin` outright — a component-level report never reaches this
inventory's `score`/`security_score` fields even by mistake.

**Pre-prerequisite reports (no `grader_schema_version` at all):** if the supplied report predates
`plugin-grader`'s `plugin_security_score` field entirely (detected by that field's own absence, not a
stored value), `import-grading` appends the quality `scoring_history` event normally but silently
appends **no** security event at all — `security_score_appended: false` in the script's own JSON output
is the only signal of this. This mirrors `plugin-grader`'s own two-case distinction for a missing
security score: a report written before `plugin_security_score` existed has no `grader_schema_version`
key at all (field-absence signals "pre-prerequisite," never a stale stored value), which is a different
case from a *post*-prerequisite report that carries the field but sets it explicitly to `null` (the
zero-scorable-components case, where `plugin-grader` did run the newer scoring logic and legitimately
found nothing to score) — this script's `security_score_appended: false` handles only the first case;
an explicit `null` in a schema-versioned report is a valid, importable value, not treated as absence.

## Repair Plugins (Marketplace-Wide)

Not implemented as an automated cascade in this script — the calling skill's own workflow is:

1. Run `plan`/`check` here to get the `missing_plugin_inventories` list and any `conflict` operations.
2. Present the list to the user; get explicit approval for which plugins to repair.
3. For each approved plugin, invoke `plugin-inventory`'s own Build/Check/Plan/Apply modes separately —
   never batch-apply across plugins from within this script.
4. Re-run this script's `plan`/`check` once the selected plugin inventories exist, to confirm the
   `missing_plugin_inventories` list has shrunk accordingly.

This keeps `plugin-inventory`'s exclusive per-plugin ownership intact — this script never writes a
`plugin-inventory.json` directly, under any mode.

## Concurrency

`bootstrap`, `apply`, and `import-grading` all hold `inventory_common.json_store.InventoryLock` for
their full read-modify-write span, in addition to the hash-based staleness check `apply` already
performs — the lock prevents two concurrent invocations from interleaving between the hash check and
the atomic write; the hash check alone prevents a *stale* write, not a *simultaneous* one.
