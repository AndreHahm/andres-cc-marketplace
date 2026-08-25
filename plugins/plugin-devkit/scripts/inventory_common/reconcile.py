"""Shared reconcile/apply/validate scaffolding for plugin-inventory.py and
marketplace-inventory.py. Both scripts' own records (a "component" or a
"plugin") share the same append-only status_history/naming_history/
scoring_history/security_scoring_history shape and the same generic
cross-record invariants -- this module holds that shared logic once instead
of two independently-maintained, hand-duplicated copies (the root cause
consistency-reviewer flagged as M6 during Wave 1's downstream QA pass).

Each script still owns its own `apply_add` (a "component" record and a
"plugin" record have genuinely different fields -- type/path/domain vs.
source/domains -- so building one isn't shared logic) and its own
`discover_*`/`build_plan` (the discovery sources differ entirely). Everything
below this line operates generically on "a collection of records with an
`id`, `status`, `status_history`, `naming_history`, `scoring_history`, and
`security_scoring_history`" and does not care which of the two record shapes
it's holding.
"""

import datetime
import json
import os

from . import grading, history, json_store, models  # ty: ignore[unresolved-import]


def today():
    return datetime.datetime.now(datetime.UTC).date().isoformat()


def require_inventory_path_shape(inventory_path, expected_filename):
    """Structural write-boundary guard for every write-capable subcommand
    (bootstrap/apply/import-grading/repair-history in both scripts):
    `inventory_path` must end in `.../.claude-plugin/<expected_filename>` --
    refuses any other shape before a single byte is written.

    This is deliberately a *shape* check, not a same-plugin-as-discovery
    check -- `apply`/`import-grading`/`repair-history` take no `plugin_dir`
    argument at all, so there is no "this plugin's own directory" to compare
    against from the CLI args alone. A stricter exact-match-to-plugin_dir
    check was considered and rejected for `bootstrap` too: it would require
    `inventory_path` to live under the same `plugin_dir` discovery reads
    from, which directly conflicts with this script's own persisted smoke
    test intentionally discovering real components from the real
    plugin-devkit tree while writing only to a disposable scratch location
    (never mutating the real repo's own inventory file). This shape check
    still closes the original finding's core concern -- an arbitrary
    unrelated file can no longer be targeted -- without forcing that
    legitimate test pattern to discover from a synthetic fixture instead of
    real data. Writing to a *different* real plugin's own valid inventory
    file is not fully prevented by this check alone; that residual gap is
    disclosed in SKILL.md's Failure Handling section, not silently assumed
    closed.
    """
    path = os.path.normpath(inventory_path)
    parent = os.path.basename(os.path.dirname(path))
    filename = os.path.basename(path)
    if filename != expected_filename or parent != ".claude-plugin":
        raise SystemExit(
            f"inventory_path {inventory_path!r} does not have the required shape "
            f".../.claude-plugin/{expected_filename} -- refusing to write to a path "
            "that doesn't look like a real inventory file location"
        )


def apply_update(inventory, operation, collection_key):
    """Apply an `update` operation (a single field change) to the record
    with matching `id` in `inventory[collection_key]`."""
    for record in inventory[collection_key]:
        if record["id"] == operation["id"]:
            record[operation["field"]] = operation["new_value"]
            return
    raise ValueError(f"apply_update: no record with id {operation['id']!r}")


def apply_status_transition(inventory, operation, collection_key):
    """Apply a human-approved `status-transition` operation -- the actual
    resolution to a `conflict` (rename/supersede/retire/restore decision),
    using `history.close_and_append_status_period` so the status change and
    its history entry are never out of sync (a bare `update` on `status`
    alone would leave `status_history` stale and fail validation)."""
    for record in inventory[collection_key]:
        if record["id"] == operation["id"]:
            record["status_history"] = history.close_and_append_status_period(
                record["status_history"],
                new_status=operation["new_status"],
                valid_from=operation.get("valid_from", today()),
                reason=operation["reason"],
                evidence=operation.get("evidence", []),
                closed_valid_to=operation.get("closed_valid_to"),
            )
            record["status"] = operation["new_status"]
            if operation.get("superseded_by_id"):
                record.setdefault("provenance", {})["superseded_by_id"] = operation[
                    "superseded_by_id"
                ]
            return
    raise ValueError(f"apply_status_transition: no record with id {operation['id']!r}")


def apply_plan(inventory, approved_operations, apply_add_fn, collection_key):
    """Apply only the operations present in `approved_operations` (already
    filtered/approved by a human via the calling skill). A `conflict` entry
    itself is never applied directly -- an approved plan instead contains
    the human's actual resolution as a `status-transition` operation (or an
    `update`/`add`/`no-op`), never the bare `conflict` shape. `apply_add_fn`
    is the caller's own record-shape-specific constructor (component vs.
    plugin), called as `apply_add_fn(inventory, operation, existing_ids)`."""
    existing_ids = {r["id"] for r in inventory.get(collection_key, [])}
    for operation in approved_operations:
        op = operation["operation"]
        if op == "add":
            apply_add_fn(inventory, operation, existing_ids)
        elif op == "update":
            apply_update(inventory, operation, collection_key)
        elif op == "status-transition":
            apply_status_transition(inventory, operation, collection_key)
        elif op == "no-op":
            continue
        else:
            raise ValueError(f"apply_plan: unsupported operation {op!r} in an approved plan")
    inventory["updated_on"] = today()
    return inventory


def validate_records(records, uniqueness_key):
    """Cross-record invariants JSON Schema alone can't express, shared across
    both "component" and "plugin" record collections. `uniqueness_key` computes
    the active-record uniqueness key from a record -- plugin-inventory's own
    `(name, type)` pair, or marketplace-inventory's bare `name` -- since the two
    inventories disagree on what "the same record" means for this check."""
    seen_ids = set()
    seen_active_keys = set()
    for record in records:
        if record["id"] in seen_ids:
            raise ValueError(f"duplicate id {record['id']!r}")
        seen_ids.add(record["id"])
        models.validate_status(record["status"])
        if record.get("functional_role") is not None:
            models.validate_functional_role(record["functional_role"])
        for compat_entry in record.get("compatibility", {}).values():
            models.validate_compatibility_level(compat_entry["level"])
        models.validate_history_periods(record["status_history"], f"{record['id']}.status_history")
        models.validate_history_periods(record["naming_history"], f"{record['id']}.naming_history")
        if models.open_period_value(record["status_history"], "status") != record["status"]:
            raise ValueError(
                f"{record['id']}: status_history's open period must equal current status"
            )
        if models.open_period_value(record["naming_history"], "name") != record["name"]:
            raise ValueError(
                f"{record['id']}: naming_history's open period must equal current name"
            )
        if record["status"] == "active":
            key = uniqueness_key(record)
            if key in seen_active_keys:
                raise ValueError(f"duplicate active key {key!r}")
            seen_active_keys.add(key)
        current_score = history.current_score_from_history(record["scoring_history"])
        if record.get("score") != current_score:
            raise ValueError(f"{record['id']}: score must equal newest scoring_history entry")
        current_security = history.current_security_score_from_history(
            record["security_scoring_history"]
        )
        if record.get("security_score") != current_security:
            raise ValueError(
                f"{record['id']}: security_score must equal newest security_scoring_history entry"
            )


def cmd_apply_from_plan(
    inventory_path, approved_plan_path, expected_hash, apply_plan_fn, validator
):
    """Shared `apply` subcommand body: hash-gated read, apply, atomic write.
    `apply_plan_fn(inventory, approved_operations)` is the caller's own
    partially-applied `apply_plan` (already bound to its `apply_add_fn` and
    `collection_key`). Returns the number of operations applied."""
    with json_store.InventoryLock(inventory_path):
        inventory = json_store.read_json(inventory_path)
        current_hash = json_store.compute_hash(inventory)
        if current_hash != expected_hash:
            raise SystemExit(
                f"stale plan: inventory hash is {current_hash} but plan expected "
                f"{expected_hash} -- re-read the inventory and regenerate the plan"
            )
        with open(approved_plan_path, encoding="utf-8") as f:
            approved_operations = json.load(f)
        updated = apply_plan_fn(inventory, approved_operations)
        json_store.atomic_write_json(inventory_path, updated, validator=validator)
    return len(approved_operations)


def cmd_import_grading_for_record(
    inventory_path, report_path, target, target_type, lookup_fn, validator
):
    """Shared `import-grading` subcommand body: locate the target record via
    the caller's own `lookup_fn(inventory) -> record | None` (already bound to
    `target`/`target_type` so it can apply its own name/type matching rules),
    validate and import the report, atomically write. Returns
    `(record, quality_appended, security_appended)`."""
    with json_store.InventoryLock(inventory_path):
        inventory = json_store.read_json(inventory_path)
        record = lookup_fn(inventory)
        if record is None:
            raise SystemExit(f"no record matching target {target!r} (type {target_type!r})")
        report = grading.load_and_validate_report(report_path, target, target_type)

        scoring_event = grading.build_scoring_event(report, report_path, target, target_type)
        new_scoring_history, appended = history.append_scoring_event(
            record["scoring_history"], scoring_event
        )
        record["scoring_history"] = new_scoring_history
        record["score"] = history.current_score_from_history(new_scoring_history)

        security_event = grading.build_security_scoring_event(
            report, report_path, target, target_type
        )
        security_appended = False
        if security_event is not None:
            new_security_history, security_appended = history.append_security_scoring_event(
                record["security_scoring_history"], security_event
            )
            record["security_scoring_history"] = new_security_history
            record["security_score"] = history.current_security_score_from_history(
                new_security_history
            )

        inventory["updated_on"] = today()
        json_store.atomic_write_json(inventory_path, inventory, validator=validator)
    return record, appended, security_appended
