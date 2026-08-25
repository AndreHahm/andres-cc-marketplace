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
| `conflict` | Either **any** canonical record (regardless of status) whose `plugin-inventory.json` disagrees on `plugin_id`, or an *active* record missing from the current manifest entirely |
| `no-op` | An active record whose `source` matches, or any non-active existing record with no `plugin_id` mismatch — source is only actually compared for active records (see below) |

Every `add`/`update`/`conflict` carries `requires_approval: true` — this script never applies one on
its own; the calling skill collects human decisions first, exactly like `plugin-inventory`. A `conflict`
is never applied as its own shape — its resolution becomes a `status-transition` operation instead (see
`SKILL.md`'s Plan mode section).

**`no-op` does not mean "identical in every field"** — a non-active existing record (planned/deprecated/
superseded/retired) is classified `no-op` whenever it isn't flagged as a `plugin_id`-mismatch conflict,
*without* comparing its `source` against the candidate at all; only an *active* record's `source` is
actually checked against the candidate before being called a match.

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
math (a violation of "plugin-grader is the sole quality- and security-scoring authority" — see the
concept's own Decisions list). If a whole-plugin report simply hasn't been imported yet, `score`/
`security_score` stay `null`; this script never fabricates a substitute. `import-grading` itself
rejects any `target_type` other than `plugin` outright — a component-level report never reaches this
inventory's `score`/`security_score` fields even by mistake.

**Pre-prerequisite reports (no `grader_schema_version` at all):** if the supplied report predates
`plugin-grader`'s `plugin_security_score` field entirely (detected by that field's own absence, not a
stored value), `import-grading` appends the quality `scoring_history` event normally but silently
appends **no** security event at all — `security_score_appended: false` in the script's own JSON output
is the only signal of this. This is distinct from a post-prerequisite report whose `plugin_security_score`
is explicitly `null` (zero-scorable-components case) — see `plugin-grader/references/output-schema.md`'s
Schema Versioning section for the full two-case distinction this mirrors.

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
