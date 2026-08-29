#!/usr/bin/env python3
"""Deterministic mechanics for building and maintaining the root
.claude-plugin/marketplace-inventory.json.

Subcommands:
  discover        <repo_root>
  bootstrap       <repo_root> <inventory_path>
  plan            <repo_root> <inventory_path>
  apply           <repo_root> <inventory_path> <approved_plan.json> <expected_hash>
  import-grading  <repo_root> <inventory_path> <report_path> <target> <target_type>
  check           <repo_root> <inventory_path>
  repair-history  <repo_root> <inventory_path> <plugin_id> <status_history|naming_history> \
                  <replacement_history.json> --confirm <plugin_id>

Every write-capable subcommand takes `repo_root` so it can enforce that
`inventory_path` resolves to exactly `<repo_root>/.claude-plugin/
marketplace-inventory.json` -- mechanically, not just by prose convention
(see `inventory_common.reconcile.require_inventory_path_under_scope_dir`).
This constrains `inventory_path` relative to whatever `repo_root` the
caller names on that invocation -- it is not a pin to any one specific
repo; a caller passing a different `repo_root` writes that directory's
own inventory file. The SKILL.md invoking this script is the one place
that constrains `repo_root` itself to the current session's repository.

This script owns marketplace-membership reconciliation and rollup fields
(score/security_score sourced from plugin-grader reports, referential
integrity against each plugin-inventory.json) -- it never edits a
plugin-inventory.json directly, and never infers component-level decisions.
Invoking plugin-inventory for a missing/stale plugin record is the calling
skill's job, gated on explicit user approval; this script only reports which
plugins need it.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
from inventory_common import (  # noqa: E402  # ty: ignore[unresolved-import]
    json_store,
    models,
    reconcile,
)

SCHEMA_VERSION = "1.0.0"
INVENTORY_FILENAME = "marketplace-inventory.json"

# Fields a human-approved 'update' operation may actually set on a plugin
# record. 'id'/'name' are structural identity, never updated in place;
# 'status' only ever changes via 'status-transition' (which keeps
# status_history in sync); every history/scoring field is append-only,
# editable only through history.append_*/repair-history's own
# explicit-confirmation gate. 'provenance' is a free-form annotation object,
# not history -- a plain 'update' overwriting it whole is intended, even
# though apply_status_transition also writes into it (superseded_by_id) as
# a side effect of a rename/supersede decision.
ALLOWED_UPDATE_FIELDS = {
    "source",
    "functional_role",
    "domains",
    "compatibility",
    "created_on",
    "provenance",
}


def discover_plugins(repo_root):
    """Read .claude-plugin/marketplace.json for current installable plugin
    entries. Returns a list of {"name", "source"} candidates."""
    marketplace_path = os.path.join(repo_root, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(marketplace_path):
        raise SystemExit(f"no marketplace manifest at {marketplace_path}")
    with open(marketplace_path, encoding="utf-8") as f:
        manifest = json.load(f)
    plugins = manifest.get("plugins", [])
    candidates = []
    for entry in plugins:
        name = entry.get("name")
        source = entry.get("source")
        if name:
            candidates.append({"name": name, "source": source})
    return sorted(candidates, key=lambda c: c["name"])


def read_plugin_inventory(repo_root, source):
    """Read a plugin's own plugin-inventory.json if it exists, resolving
    `source` (a marketplace-relative path like './plugins/plugin-devkit')
    against `repo_root`. Returns None if missing OR unparseable -- either
    way it's reported as a stale/missing plugin inventory, never
    synthesized and never allowed to abort the whole run."""
    if not source:
        return None
    plugin_dir = os.path.normpath(os.path.join(repo_root, source))
    inventory_path = os.path.join(plugin_dir, ".claude-plugin", "plugin-inventory.json")
    if not os.path.isfile(inventory_path):
        return None
    try:
        return json_store.read_json(inventory_path)
    except (OSError, ValueError):
        return None


def empty_inventory(marketplace_name):
    return {
        "schema_version": SCHEMA_VERSION,
        "marketplace_name": marketplace_name,
        "updated_on": reconcile.today(),
        "plugins": [],
    }


def build_plan(inventory, discovered, repo_root):
    """Compare discovered marketplace plugins against the canonical
    inventory's current active plugin records. A discovered candidate
    matching an existing *non-active* record (planned/retired/deprecated/
    superseded) is surfaced as a `conflict`, never a silent no-op -- e.g. a
    planned plugin that has now actually appeared in the marketplace
    manifest needs a human status-transition decision, not an automatic
    reconciliation. Also reports missing/stale per-plugin inventories --
    referential-integrity findings, not reconciliation operations this
    script applies itself."""
    # A duplicate name can occur across a retired/deprecated record and the
    # active record that superseded it (validate_records only forbids two
    # *active* records sharing a name, never a historical one sharing a name
    # with the current active record). Always prefer the active record on
    # such a collision -- keeping whichever record happened to come last in
    # array order would let a retired duplicate shadow the active one and
    # misclassify a genuine no-op/update as a conflict.
    existing_by_name = {}
    for p in inventory.get("plugins", []):
        if p["name"] not in existing_by_name or p.get("status") == "active":
            existing_by_name[p["name"]] = p
    discovered_names = {c["name"] for c in discovered}
    plan = []
    missing_plugin_inventories = []

    for candidate in discovered:
        existing = existing_by_name.get(candidate["name"])
        plugin_inventory = read_plugin_inventory(repo_root, candidate["source"])
        if existing is None:
            add_op = {
                "operation": "add",
                "name": candidate["name"],
                "source": candidate["source"],
                "evidence": [".claude-plugin/marketplace.json"],
                "requires_approval": True,
            }
            if plugin_inventory is not None and plugin_inventory.get("plugin_id"):
                # This plugin already has its own plugin-inventory.json (independently
                # bootstrapped before the marketplace-wide inventory existed) -- reuse its
                # recorded plugin_id instead of minting a new one, or the freshly-added
                # marketplace record would disagree with it and surface a spurious
                # plugin_id-mismatch conflict on the very next check.
                add_op["id"] = plugin_inventory["plugin_id"]
            plan.append(add_op)
        elif existing.get("status") == "active":
            if existing.get("source") != candidate["source"]:
                plan.append(
                    {
                        "operation": "update",
                        "id": existing["id"],
                        "name": candidate["name"],
                        "field": "source",
                        "old_value": existing.get("source"),
                        "new_value": candidate["source"],
                        "evidence": [".claude-plugin/marketplace.json"],
                        "requires_approval": True,
                    }
                )
            else:
                plan.append({"operation": "no-op", "name": candidate["name"]})
        else:
            plan.append(
                {
                    "operation": "conflict",
                    "id": existing["id"],
                    "name": candidate["name"],
                    "reason": f"a discovered candidate matches an existing {existing['status']!r} "
                    "record -- requires a status-transition decision (e.g. activate a planned "
                    "plugin now that it's in the marketplace manifest, restore a retired/"
                    "deprecated/superseded one) before this can be reconciled, never an "
                    "automatic no-op",
                    "requires_approval": True,
                }
            )

        if plugin_inventory is None:
            missing_plugin_inventories.append(candidate["name"])
        elif existing and plugin_inventory.get("plugin_id") != existing.get("id"):
            plan.append(
                {
                    "operation": "conflict",
                    "id": existing["id"],
                    "name": candidate["name"],
                    "reason": "plugin-inventory.json's plugin_id does not match "
                    "this marketplace record's id",
                    "requires_approval": True,
                }
            )

    for existing in inventory.get("plugins", []):
        if existing.get("status") == "active" and existing["name"] not in discovered_names:
            plan.append(
                {
                    "operation": "conflict",
                    "id": existing["id"],
                    "name": existing["name"],
                    "reason": "active record is missing from the current marketplace manifest -- "
                    "requires a deprecate/supersede/retire decision, not automatic retirement",
                    "requires_approval": True,
                }
            )

    return plan, missing_plugin_inventories


def apply_add(inventory, operation, existing_ids):
    """`operation["status"]` defaults to derived-from-`source`-truthiness
    ("active" when a real marketplace.json source exists, "planned"
    otherwise), but an explicit `operation["status"]` always wins -- this
    mirrors plugin-inventory.py's own `apply_add`, which documents why
    truthiness alone isn't safe to rely on for every caller.

    `operation["id"]`, when present, is reused verbatim instead of minting a
    fresh one -- `build_plan` sets this when the plugin already has its own
    plugin-inventory.json (independently bootstrapped before this marketplace
    inventory existed), so the new marketplace record agrees with that
    plugin's already-recorded plugin_id instead of immediately conflicting
    with it on the next check."""
    requested_id = operation.get("id")
    if requested_id is not None:
        if requested_id in existing_ids:
            raise ValueError(
                f"apply_add: requested id {requested_id!r} already exists in this inventory"
            )
        new_id = requested_id
    else:
        new_id = models.generate_id("plugin", existing_ids)
    existing_ids.add(new_id)
    today = reconcile.today()
    status = operation.get("status", "active" if operation["source"] else "planned")
    models.validate_status(status)
    record = {
        "id": new_id,
        "name": operation["name"],
        "source": operation["source"],
        "status": status,
        "status_history": [
            {
                "status": status,
                "valid_from": today,
                "valid_to": None,
                "reason": operation.get(
                    "status_reason",
                    "Discovered by marketplace-inventory Build/Plan."
                    if status == "active"
                    else "Planned plugin, not yet materialized.",
                ),
                "evidence": operation.get("evidence", []),
            }
        ],
        "functional_role": None,
        "domains": [],
        "score": None,
        "security_score": None,
        "created_on": None,
        "compatibility": {},
        "naming_history": [
            {
                "name": operation["name"],
                "valid_from": today,
                "valid_to": None,
                "reason": "Current name at inventory bootstrap.",
                "evidence": operation.get("evidence", []),
            }
        ],
        "scoring_history": [],
        "security_scoring_history": [],
        "provenance": {},
    }
    inventory["plugins"].append(record)


def apply_plan(inventory, approved_operations):
    """Delegates the per-operation-type logic to the shared
    `inventory_common.reconcile` module -- only `apply_add` (the
    plugin-record shape) is this script's own."""
    return reconcile.apply_plan(
        inventory, approved_operations, apply_add, "plugins", ALLOWED_UPDATE_FIELDS
    )


def validate_inventory(inventory):
    """Delegates to the shared `inventory_common.reconcile.validate_records`,
    using this inventory's own bare-`name` active-record uniqueness key
    (unlike plugin-inventory's `(name, type)` pair -- a plugin has no
    `type` field)."""
    reconcile.validate_records(inventory.get("plugins", []), uniqueness_key=lambda p: p["name"])


def cmd_discover(args):
    print(json.dumps(discover_plugins(args.repo_root), indent=2))


def cmd_bootstrap(args):
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.repo_root, INVENTORY_FILENAME
    )
    with json_store.InventoryLock(args.inventory_path):
        if os.path.exists(args.inventory_path):
            raise SystemExit(f"refusing to bootstrap: {args.inventory_path} already exists")
        marketplace_path = os.path.join(args.repo_root, ".claude-plugin", "marketplace.json")
        with open(marketplace_path, encoding="utf-8") as f:
            marketplace_name = json.load(f).get("name", "marketplace")
        inventory = empty_inventory(marketplace_name)
        discovered = discover_plugins(args.repo_root)
        plan, _missing = build_plan(inventory, discovered, args.repo_root)
        add_ops = [op for op in plan if op["operation"] == "add"]
        existing_ids = set()
        for op in add_ops:
            apply_add(inventory, op, existing_ids)
        reconcile.validate_or_exit(validate_inventory, inventory, context="bootstrap")
        reconcile.validate_or_exit(
            json_store.atomic_write_json,
            args.inventory_path,
            inventory,
            validator=validate_inventory,
            context="bootstrap",
        )
    print(json.dumps({"bootstrapped": len(add_ops), "path": args.inventory_path}, indent=2))


def cmd_plan(args):
    if not os.path.exists(args.inventory_path):
        raise SystemExit(f"no inventory at {args.inventory_path} -- run bootstrap first")
    inventory = reconcile.validate_or_exit(
        json_store.read_json, args.inventory_path, context="plan"
    )
    discovered = discover_plugins(args.repo_root)
    plan, missing_plugin_inventories = build_plan(inventory, discovered, args.repo_root)
    print(
        json.dumps(
            {
                "expected_hash": json_store.compute_hash(inventory),
                "operations": plan,
                "missing_plugin_inventories": missing_plugin_inventories,
            },
            indent=2,
        )
    )


def cmd_apply(args):
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.repo_root, INVENTORY_FILENAME
    )
    applied = reconcile.cmd_apply_from_plan(
        args.inventory_path,
        args.approved_plan_path,
        args.expected_hash,
        apply_plan,
        validate_inventory,
    )
    print(json.dumps({"applied": applied, "path": args.inventory_path}, indent=2))


def cmd_import_grading(args):
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.repo_root, INVENTORY_FILENAME
    )
    if args.target_type != "plugin":
        raise SystemExit(
            f"marketplace-inventory only imports whole-plugin reports (target_type='plugin'); "
            f"got target_type={args.target_type!r} -- a component-level report belongs in "
            f"plugin-inventory's own import-grading instead"
        )

    def lookup(inventory):
        # A retired/deprecated/superseded record and an active one may
        # legitimately share the same name -- validate_records only enforces
        # uniqueness among active records. Picking the first array match (as
        # a bare next(...) would) can silently import a report against the
        # wrong one; reject the ambiguity outright instead.
        matches = [p for p in inventory["plugins"] if p["name"] == args.target]
        if len(matches) > 1:
            raise SystemExit(
                f"ambiguous target: {len(matches)} records match name={args.target!r} "
                f"(ids: {[p['id'] for p in matches]!r}) -- resolve the naming conflict "
                "(retire/rename one) before importing a report by name"
            )
        return matches[0] if matches else None

    plugin, appended, security_appended = reconcile.cmd_import_grading_for_record(
        args.inventory_path,
        args.report_path,
        args.target,
        args.target_type,
        lookup,
        validate_inventory,
    )
    print(
        json.dumps(
            {
                "quality_score_appended": appended,
                "security_score_appended": security_appended,
                "current_score": plugin["score"],
                "current_security_score": plugin["security_score"],
            },
            indent=2,
        )
    )


def cmd_check(args):
    if not os.path.exists(args.inventory_path):
        raise SystemExit(f"no inventory at {args.inventory_path} -- run bootstrap first")
    inventory = reconcile.validate_or_exit(
        json_store.read_json, args.inventory_path, context="check"
    )
    reconcile.validate_or_exit(validate_inventory, inventory, context="check")
    discovered = discover_plugins(args.repo_root)
    plan, missing_plugin_inventories = build_plan(inventory, discovered, args.repo_root)
    drift = [op for op in plan if op["operation"] != "no-op"]
    print(
        json.dumps(
            {
                "valid": True,
                "drift_count": len(drift),
                "drift": drift,
                "missing_plugin_inventories": missing_plugin_inventories,
            },
            indent=2,
        )
    )


def _load_replacement_history(path):
    """Read and structurally validate a repair-history replacement file:
    must be a JSON array of periods, never a bare object or scalar."""
    with open(path, encoding="utf-8") as f:
        replacement = json.load(f)
    if not isinstance(replacement, list):
        raise ValueError(
            f"replacement history at {path!r} must be a JSON array of periods, "
            f"got {type(replacement).__name__}"
        )
    return replacement


def cmd_repair_history(args):
    """The only mode allowed to rewrite existing history entries. The
    calling skill must show the user the exact before/after diff and get
    explicit approval before invoking this -- `--confirm <plugin_id>`
    (repeating the same id being repaired) is this function's own
    mechanical gate, so an invocation missing it fails closed instead of
    relying solely on the calling skill having actually shown that diff."""
    if args.confirm != args.plugin_id:
        raise SystemExit(
            "repair-history requires --confirm <plugin_id> to exactly match the "
            "plugin_id being repaired -- this is the destructive-rewrite gate; "
            "show the user the full before/after diff and get explicit approval first"
        )
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.repo_root, INVENTORY_FILENAME
    )
    with json_store.InventoryLock(args.inventory_path):
        inventory = reconcile.validate_or_exit(
            json_store.read_json, args.inventory_path, context="repair-history"
        )
        reconcile.validate_or_exit(validate_inventory, inventory, context="repair-history")
        plugin = next((p for p in inventory["plugins"] if p["id"] == args.plugin_id), None)
        if plugin is None:
            raise SystemExit(f"no plugin with id {args.plugin_id!r} in this inventory")
        if args.history_field not in ("status_history", "naming_history"):
            raise SystemExit("history_field must be 'status_history' or 'naming_history'")
        replacement = reconcile.validate_or_exit(
            _load_replacement_history, args.replacement_history_path, context="repair-history"
        )
        reconcile.validate_or_exit(
            models.validate_history_periods,
            replacement,
            f"{args.plugin_id}.{args.history_field}",
            context="repair-history",
        )
        value_key = "status" if args.history_field == "status_history" else "name"
        open_value = models.open_period_value(replacement, value_key)
        current_value = (
            plugin["status"] if args.history_field == "status_history" else plugin["name"]
        )
        if open_value != current_value:
            raise SystemExit(
                f"replacement history's open period value {open_value!r} does not match "
                f"the record's current {value_key} {current_value!r} -- "
                "update one or the other first"
            )
        plugin[args.history_field] = replacement
        inventory["updated_on"] = reconcile.today()
        reconcile.validate_or_exit(
            json_store.atomic_write_json,
            args.inventory_path,
            inventory,
            validator=validate_inventory,
            context="repair-history",
        )
    print(json.dumps({"repaired": args.plugin_id, "field": args.history_field}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("discover")
    p.add_argument("repo_root")
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("bootstrap")
    p.add_argument("repo_root")
    p.add_argument("inventory_path")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("plan")
    p.add_argument("repo_root")
    p.add_argument("inventory_path")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("apply")
    p.add_argument("repo_root")
    p.add_argument("inventory_path")
    p.add_argument("approved_plan_path")
    p.add_argument("expected_hash")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("import-grading")
    p.add_argument("repo_root")
    p.add_argument("inventory_path")
    p.add_argument("report_path")
    p.add_argument("target")
    p.add_argument("target_type")
    p.set_defaults(func=cmd_import_grading)

    p = sub.add_parser("check")
    p.add_argument("repo_root")
    p.add_argument("inventory_path")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("repair-history")
    p.add_argument("repo_root")
    p.add_argument("inventory_path")
    p.add_argument("plugin_id")
    p.add_argument("history_field")
    p.add_argument("replacement_history_path")
    p.add_argument(
        "--confirm",
        required=True,
        help="must exactly equal plugin_id -- the mechanical confirmation gate for this "
        "destructive mode; the calling skill should only pass this after showing the user "
        "the full before/after diff and getting explicit approval",
    )
    p.set_defaults(func=cmd_repair_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
