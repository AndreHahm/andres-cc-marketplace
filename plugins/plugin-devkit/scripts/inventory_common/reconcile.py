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


def require_inventory_path_under_scope_dir(inventory_path, scope_dir, expected_filename):
    """Full write-boundary guard for every write-capable subcommand
    (bootstrap/apply/import-grading/repair-history in plugin-inventory.py;
    bootstrap/apply/import-grading in marketplace-inventory.py): resolves
    both `inventory_path` and `scope_dir` to real, symlink-resolved absolute
    paths and requires `inventory_path` to equal exactly
    `<realpath(scope_dir)>/.claude-plugin/<expected_filename>` -- refuses
    anything else before a single byte is written. `scope_dir` is the
    plugin's own root directory for plugin-inventory.py, or the repo root
    for marketplace-inventory.py.

    Every write-capable subcommand in both scripts takes `scope_dir` as a
    required argument specifically so this check can enforce real
    same-plugin-as-discovery containment, not just a filename/parent-dir
    shape match -- a caller can no longer target a *different* real
    plugin's (or, for marketplace-inventory, a different repo's) own valid
    inventory file by supplying its path directly, since that path would
    resolve outside the `scope_dir` this specific invocation names.
    """
    expected = os.path.realpath(os.path.join(scope_dir, ".claude-plugin", expected_filename))
    actual = os.path.realpath(inventory_path)
    if actual != expected:
        raise SystemExit(
            f"inventory_path {inventory_path!r} does not resolve to {expected!r} "
            f"(the expected .claude-plugin/{expected_filename} under {scope_dir!r}) -- "
            "refusing to write outside this invocation's own declared scope"
        )


def validate_or_exit(fn, *args, context, **kwargs):
    """Run `fn(*args, **kwargs)`, converting any `ValueError`, `KeyError`,
    `AttributeError`, `TypeError`, or `OSError` it raises into a clean
    `SystemExit` prefixed with `context`. Every validator in this system
    (`validate_inventory`, `validate_history_periods`, etc.) raises a bare
    `ValueError` on a semantic violation -- every CLI subcommand here wants
    that surfaced as a clean rejection message like every other rejection
    path in these scripts, not an uncaught Python traceback. `KeyError` is
    caught too: `validate_records` indexes several required record fields
    directly (`record["status"]`, `record["name"]`, etc.) rather than via
    `.get()`, so a record missing one of those keys entirely -- a
    hand-corrupted inventory file, not a normal enum/shape violation --
    would otherwise still leak an uncaught traceback. `AttributeError` and
    `TypeError` are caught for the same hand-corrupted-shape reason:
    `validate_records`' `compatibility.values()` call (and `models`'
    `.get()`-based history-period field accesses) assume a dict/list shape
    that a malformed record can violate -- e.g. `compatibility` supplied as
    a list raises `AttributeError` from `.values()`, not `ValueError`.
    `OSError` is caught for the same reason at every read call site this
    wraps (`json_store.read_json`, an approved-plan file open): a missing,
    unreadable, or truncated file raises `OSError`/`json.JSONDecodeError`
    (a `ValueError` subclass) before any validator ever runs, and that path
    deserves the same clean rejection as a validator failure, not a raw
    traceback."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as exc:
        raise SystemExit(f"{context}: {exc}") from exc


def apply_update(inventory, operation, collection_key, allowed_fields):
    """Apply an `update` operation (a single field change) to the record
    with matching `id` in `inventory[collection_key]`. `allowed_fields` is
    the caller's own allowlist of fields a human is actually permitted to
    set this way (a component's `path`/`functional_role`/etc., or a
    plugin's `source`/`functional_role`/etc.) -- `id`, `status`, and every
    history/scoring field are never in it: `status` only ever changes via
    `apply_status_transition` (which keeps `status_history` in sync), and
    the history/scoring fields are append-only, mutable only through
    `history.append_*`/`repair-history`'s own explicit-confirmation gate.
    Without this allowlist, an `update` operation naming `status_history`
    or `naming_history` directly could silently overwrite append-only
    audit history through the ordinary apply path, bypassing
    `repair-history`'s `--confirm` gate entirely."""
    if operation["field"] not in allowed_fields:
        raise ValueError(
            f"apply_update: field {operation['field']!r} is not updatable via 'update' "
            f"(allowed: {sorted(allowed_fields)}) -- a status change goes through "
            "'status-transition', and history/scoring fields are append-only, editable only "
            "through repair-history's own explicit-confirmation gate"
        )
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
    alone would leave `status_history` stale and fail validation).

    An optional `new_name` field additionally renames the record via
    `history.close_and_append_naming_period`, atomically alongside the
    status change -- this is the only path that can actually change a
    record's `name`: `apply_update`'s allowlist deliberately excludes `name`
    for the same reason it excludes `status` (leaving `naming_history`
    stale), and `repair-history` refuses a replacement whose open period
    doesn't match the record's *current* name, so it can't be used to
    rename either. A pure rename with no real status change still requires
    `new_status` to be supplied equal to the record's current status --
    every `status-transition` operation shares this one shape regardless of
    which of the four resolutions it's applying."""
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
            if operation.get("new_name"):
                record["naming_history"] = history.close_and_append_naming_period(
                    record["naming_history"],
                    new_name=operation["new_name"],
                    valid_from=operation.get("valid_from", today()),
                    reason=operation.get("rename_reason", operation["reason"]),
                    evidence=operation.get("evidence", []),
                    closed_valid_to=operation.get("closed_valid_to"),
                )
                record["name"] = operation["new_name"]
            if operation.get("superseded_by_id"):
                record.setdefault("provenance", {})["superseded_by_id"] = operation[
                    "superseded_by_id"
                ]
            return
    raise ValueError(f"apply_status_transition: no record with id {operation['id']!r}")


def apply_plan(inventory, approved_operations, apply_add_fn, collection_key, allowed_update_fields):
    """Apply only the operations present in `approved_operations` (already
    filtered/approved by a human via the calling skill). A `conflict` entry
    itself is never applied directly -- an approved plan instead contains
    the human's actual resolution as a `status-transition` operation (or an
    `update`/`add`/`no-op`), never the bare `conflict` shape. `apply_add_fn`
    is the caller's own record-shape-specific constructor (component vs.
    plugin), called as `apply_add_fn(inventory, operation, existing_ids)`.
    `allowed_update_fields` is passed straight through to `apply_update`."""
    existing_ids = {r["id"] for r in inventory.get(collection_key, [])}
    for operation in approved_operations:
        op = operation["operation"]
        if op == "add":
            apply_add_fn(inventory, operation, existing_ids)
        elif op == "update":
            apply_update(inventory, operation, collection_key, allowed_update_fields)
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


def _load_approved_plan(approved_plan_path):
    """Read and structurally validate an approved-plan file: must be a JSON
    array of operations, never a bare object or scalar -- iterating a dict
    would yield its keys as strings and fail confusingly deep inside
    `apply_plan` rather than here, with a clear message, before anything
    else runs."""
    with open(approved_plan_path, encoding="utf-8") as f:
        approved_operations = json.load(f)
    if not isinstance(approved_operations, list):
        raise ValueError(
            f"approved plan at {approved_plan_path!r} must be a JSON array of operations, "
            f"got {type(approved_operations).__name__}"
        )
    return approved_operations


def cmd_apply_from_plan(
    inventory_path, approved_plan_path, expected_hash, apply_plan_fn, validator
):
    """Shared `apply` subcommand body: hash-gated read, apply, atomic write.
    `apply_plan_fn(inventory, approved_operations)` is the caller's own
    partially-applied `apply_plan` (already bound to its `apply_add_fn` and
    `collection_key`). Returns the number of operations applied."""
    with json_store.InventoryLock(inventory_path):
        inventory = validate_or_exit(json_store.read_json, inventory_path, context="apply")
        current_hash = json_store.compute_hash(inventory)
        if current_hash != expected_hash:
            raise SystemExit(
                f"stale plan: inventory hash is {current_hash} but plan expected "
                f"{expected_hash} -- re-read the inventory and regenerate the plan"
            )
        approved_operations = validate_or_exit(
            _load_approved_plan, approved_plan_path, context="apply"
        )
        updated = validate_or_exit(apply_plan_fn, inventory, approved_operations, context="apply")
        validate_or_exit(
            json_store.atomic_write_json,
            inventory_path,
            updated,
            validator=validator,
            context="apply",
        )
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
        inventory = validate_or_exit(json_store.read_json, inventory_path, context="import-grading")
        record = lookup_fn(inventory)
        if record is None:
            raise SystemExit(f"no record matching target {target!r} (type {target_type!r})")
        report = validate_or_exit(
            grading.load_and_validate_report,
            report_path,
            target,
            target_type,
            context="import-grading",
        )

        scoring_event = validate_or_exit(
            grading.build_scoring_event,
            report,
            report_path,
            target,
            target_type,
            context="import-grading",
        )
        new_scoring_history, appended = validate_or_exit(
            history.append_scoring_event,
            record["scoring_history"],
            scoring_event,
            context="import-grading",
        )
        record["scoring_history"] = new_scoring_history
        record["score"] = history.current_score_from_history(new_scoring_history)

        security_event = validate_or_exit(
            grading.build_security_scoring_event,
            report,
            report_path,
            target,
            target_type,
            context="import-grading",
        )
        security_appended = False
        if security_event is not None:
            new_security_history, security_appended = validate_or_exit(
                history.append_security_scoring_event,
                record["security_scoring_history"],
                security_event,
                context="import-grading",
            )
            record["security_scoring_history"] = new_security_history
            record["security_score"] = history.current_security_score_from_history(
                new_security_history
            )

        inventory["updated_on"] = today()
        validate_or_exit(
            json_store.atomic_write_json,
            inventory_path,
            inventory,
            validator=validator,
            context="import-grading",
        )
    return record, appended, security_appended
