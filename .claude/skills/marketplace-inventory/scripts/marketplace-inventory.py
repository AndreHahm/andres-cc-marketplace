#!/usr/bin/env python3
"""Deterministic mechanics for building and maintaining the root
.claude-plugin/marketplace-inventory.json.

Subcommands:
  discover        <repo_root>
  bootstrap       <repo_root> <inventory_path>
  plan            <repo_root> <inventory_path>
  apply           <inventory_path> <approved_plan.json> <expected_hash>
  import-grading  <inventory_path> <report_path> <target> <target_type>
  check           <repo_root> <inventory_path>

This script owns marketplace-membership reconciliation and rollup fields
(score/security_score sourced from plugin-grader reports, referential
integrity against each plugin-inventory.json) -- it never edits a
plugin-inventory.json directly, and never infers component-level decisions.
Invoking plugin-inventory for a missing/stale plugin record is the calling
skill's job, gated on explicit user approval; this script only reports which
plugins need it.
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
from inventory_common import (  # noqa: E402  # ty: ignore[unresolved-import]
    grading,
    history,
    json_store,
    models,
)

SCHEMA_VERSION = "1.0.0"


def _today():
    return datetime.datetime.now(datetime.UTC).date().isoformat()


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
        "updated_on": _today(),
        "plugins": [],
    }


def build_plan(inventory, discovered, repo_root):
    """Compare discovered marketplace plugins against the canonical
    inventory's current active plugin records. Also reports missing/stale
    per-plugin inventories -- referential-integrity findings, not
    reconciliation operations this script applies itself."""
    existing_by_name = {p["name"]: p for p in inventory.get("plugins", [])}
    discovered_names = {c["name"] for c in discovered}
    plan = []
    missing_plugin_inventories = []

    for candidate in discovered:
        existing = existing_by_name.get(candidate["name"])
        if existing is None:
            plan.append(
                {
                    "operation": "add",
                    "name": candidate["name"],
                    "source": candidate["source"],
                    "evidence": [".claude-plugin/marketplace.json"],
                    "requires_approval": True,
                }
            )
        elif existing.get("status") == "active" and existing.get("source") != candidate["source"]:
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

        plugin_inventory = read_plugin_inventory(repo_root, candidate["source"])
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
    truthiness alone isn't safe to rely on for every caller."""
    new_id = models.generate_id("plugin", existing_ids)
    existing_ids.add(new_id)
    today = _today()
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


def apply_update(inventory, operation):
    for plugin in inventory["plugins"]:
        if plugin["id"] == operation["id"]:
            plugin[operation["field"]] = operation["new_value"]
            return
    raise ValueError(f"apply_update: no plugin with id {operation['id']!r}")


def apply_status_transition(inventory, operation):
    """Apply a human-approved `status-transition` operation -- the actual
    resolution to a `conflict` (deprecate/supersede/retire decision), using
    `history.close_and_append_status_period` so the status change and its
    history entry are never out of sync."""
    for plugin in inventory["plugins"]:
        if plugin["id"] == operation["id"]:
            plugin["status_history"] = history.close_and_append_status_period(
                plugin["status_history"],
                new_status=operation["new_status"],
                valid_from=operation.get("valid_from", _today()),
                reason=operation["reason"],
                evidence=operation.get("evidence", []),
                closed_valid_to=operation.get("closed_valid_to"),
            )
            plugin["status"] = operation["new_status"]
            if operation.get("superseded_by_id"):
                plugin.setdefault("provenance", {})["superseded_by_id"] = operation[
                    "superseded_by_id"
                ]
            return
    raise ValueError(f"apply_status_transition: no plugin with id {operation['id']!r}")


def apply_plan(inventory, approved_operations):
    existing_ids = {p["id"] for p in inventory.get("plugins", [])}
    for operation in approved_operations:
        op = operation["operation"]
        if op == "add":
            apply_add(inventory, operation, existing_ids)
        elif op == "update":
            apply_update(inventory, operation)
        elif op == "status-transition":
            apply_status_transition(inventory, operation)
        elif op == "no-op":
            continue
        else:
            raise ValueError(f"apply_plan: unsupported operation {op!r} in an approved plan")
    inventory["updated_on"] = _today()
    return inventory


def validate_inventory(inventory):
    seen_ids = set()
    seen_active_names = set()
    for plugin in inventory.get("plugins", []):
        if plugin["id"] in seen_ids:
            raise ValueError(f"duplicate plugin id {plugin['id']!r}")
        seen_ids.add(plugin["id"])
        models.validate_status(plugin["status"])
        if plugin.get("functional_role") is not None:
            models.validate_functional_role(plugin["functional_role"])
        for compat_entry in plugin.get("compatibility", {}).values():
            models.validate_compatibility_level(compat_entry["level"])
        models.validate_history_periods(plugin["status_history"], f"{plugin['id']}.status_history")
        models.validate_history_periods(plugin["naming_history"], f"{plugin['id']}.naming_history")
        if models.open_period_value(plugin["status_history"], "status") != plugin["status"]:
            raise ValueError(
                f"{plugin['id']}: status_history's open period must equal current status"
            )
        if models.open_period_value(plugin["naming_history"], "name") != plugin["name"]:
            raise ValueError(
                f"{plugin['id']}: naming_history's open period must equal current name"
            )
        if plugin["status"] == "active":
            if plugin["name"] in seen_active_names:
                raise ValueError(f"duplicate active plugin name {plugin['name']!r}")
            seen_active_names.add(plugin["name"])
        current_score = history.current_score_from_history(plugin["scoring_history"])
        if plugin.get("score") != current_score:
            raise ValueError(f"{plugin['id']}: score must equal newest scoring_history entry")
        current_security = history.current_security_score_from_history(
            plugin["security_scoring_history"]
        )
        if plugin.get("security_score") != current_security:
            raise ValueError(
                f"{plugin['id']}: security_score must equal newest security_scoring_history entry"
            )


def cmd_discover(args):
    print(json.dumps(discover_plugins(args.repo_root), indent=2))


def cmd_bootstrap(args):
    with json_store.InventoryLock(args.inventory_path):
        if os.path.exists(args.inventory_path):
            raise SystemExit(f"refusing to bootstrap: {args.inventory_path} already exists")
        marketplace_path = os.path.join(args.repo_root, ".claude-plugin", "marketplace.json")
        with open(marketplace_path, encoding="utf-8") as f:
            marketplace_name = json.load(f).get("name", "marketplace")
        inventory = empty_inventory(marketplace_name)
        discovered = discover_plugins(args.repo_root)
        plan, _missing = build_plan(inventory, discovered, args.repo_root)
        existing_ids = set()
        for op in plan:
            if op["operation"] == "add":
                apply_add(inventory, op, existing_ids)
        validate_inventory(inventory)
        json_store.atomic_write_json(args.inventory_path, inventory, validator=validate_inventory)
    print(json.dumps({"bootstrapped": len(discovered), "path": args.inventory_path}, indent=2))


def cmd_plan(args):
    if not os.path.exists(args.inventory_path):
        raise SystemExit(f"no inventory at {args.inventory_path} -- run bootstrap first")
    inventory = json_store.read_json(args.inventory_path)
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
    with json_store.InventoryLock(args.inventory_path):
        inventory = json_store.read_json(args.inventory_path)
        current_hash = json_store.compute_hash(inventory)
        if current_hash != args.expected_hash:
            raise SystemExit(
                f"stale plan: inventory hash is {current_hash} but plan expected "
                f"{args.expected_hash} -- re-read the inventory and regenerate the plan"
            )
        with open(args.approved_plan_path, encoding="utf-8") as f:
            approved_operations = json.load(f)
        updated = apply_plan(inventory, approved_operations)
        json_store.atomic_write_json(args.inventory_path, updated, validator=validate_inventory)
    print(json.dumps({"applied": len(approved_operations), "path": args.inventory_path}, indent=2))


def cmd_import_grading(args):
    if args.target_type != "plugin":
        raise SystemExit(
            f"marketplace-inventory only imports whole-plugin reports (target_type='plugin'); "
            f"got target_type={args.target_type!r} -- a component-level report belongs in "
            f"plugin-inventory's own import-grading instead"
        )
    with json_store.InventoryLock(args.inventory_path):
        inventory = json_store.read_json(args.inventory_path)
        plugin = next((p for p in inventory["plugins"] if p["name"] == args.target), None)
        if plugin is None:
            raise SystemExit(f"no plugin named {args.target!r} in this inventory")
        report = grading.load_and_validate_report(args.report_path, args.target, args.target_type)

        scoring_event = grading.build_scoring_event(
            report, args.report_path, args.target, args.target_type
        )
        new_scoring_history, appended = history.append_scoring_event(
            plugin["scoring_history"], scoring_event
        )
        plugin["scoring_history"] = new_scoring_history
        plugin["score"] = history.current_score_from_history(new_scoring_history)

        security_event = grading.build_security_scoring_event(
            report, args.report_path, args.target, args.target_type
        )
        security_appended = False
        if security_event is not None:
            new_security_history, security_appended = history.append_security_scoring_event(
                plugin["security_scoring_history"], security_event
            )
            plugin["security_scoring_history"] = new_security_history
            plugin["security_score"] = history.current_security_score_from_history(
                new_security_history
            )

        inventory["updated_on"] = _today()
        json_store.atomic_write_json(args.inventory_path, inventory, validator=validate_inventory)
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
    inventory = json_store.read_json(args.inventory_path)
    validate_inventory(inventory)
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
    p.add_argument("inventory_path")
    p.add_argument("approved_plan_path")
    p.add_argument("expected_hash")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("import-grading")
    p.add_argument("inventory_path")
    p.add_argument("report_path")
    p.add_argument("target")
    p.add_argument("target_type")
    p.set_defaults(func=cmd_import_grading)

    p = sub.add_parser("check")
    p.add_argument("repo_root")
    p.add_argument("inventory_path")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
