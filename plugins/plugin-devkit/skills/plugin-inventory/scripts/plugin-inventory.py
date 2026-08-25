#!/usr/bin/env python3
"""Deterministic mechanics for building and maintaining exactly one plugin's
plugins/<plugin>/.claude-plugin/plugin-inventory.json.

Subcommands:
  discover        <plugin_dir>
  bootstrap       <plugin_dir> <inventory_path> <plugin_id> <plugin_name>
  plan            <plugin_dir> <inventory_path>
  apply           <plugin_dir> <inventory_path> <approved_plan.json> <expected_hash>
  import-grading  <plugin_dir> <inventory_path> <report_path> <target> <target_type>
  check           <inventory_path> <plugin_dir>
  repair-history  <plugin_dir> <inventory_path> <component_id> <history_field> \
                  <replacement_history.json> --confirm <component_id>

Every write-capable subcommand takes `plugin_dir` so it can enforce that
`inventory_path` resolves to exactly `<plugin_dir>/.claude-plugin/
plugin-inventory.json` -- this script never writes a different plugin's own
inventory file, mechanically, not just by prose convention (see
`inventory_common.reconcile.require_inventory_path_under_scope_dir`).

This script owns discovery, reconciliation-plan construction, and atomic
apply -- it never decides lifecycle status, functional_role, domain, or
compatibility for a human; those stay as `null`/pending fields a human
approves through the calling skill's own AskUserQuestion steps. See
SKILL.md for the full workflow this script is one piece of.
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
INVENTORY_FILENAME = "plugin-inventory.json"

# Fields a human-approved 'update' operation may actually set on a component
# record. 'id'/'name'/'type' are structural identity, never updated in place;
# 'status' only ever changes via 'status-transition' (which keeps
# status_history in sync); every history/scoring field is append-only,
# editable only through history.append_*/repair-history's own
# explicit-confirmation gate -- none of those belong here.
ALLOWED_UPDATE_FIELDS = {"path", "functional_role", "domain", "compatibility", "created_on"}

# Logical component types this script has a real filesystem-convention
# detector for. Of the remaining logical types, only mcp-server/lsp-server
# have any detector at all (manifest-declared -- see
# discover_manifest_declared); rule/output-style/theme/monitor/custom have
# no detector of any kind and must be added manually via a plan operation.
CONVENTION_DETECTED_TYPES = ("skill", "agent", "command", "hook")


def discover_filesystem_components(plugin_dir):
    """Detect skill/agent/command/hook components by filesystem convention.
    Returns a list of {"type", "name", "path"} candidates, sorted for
    deterministic output."""
    candidates = []

    skills_dir = os.path.join(plugin_dir, "skills")
    if os.path.isdir(skills_dir):
        for name in sorted(os.listdir(skills_dir)):
            skill_md = os.path.join(skills_dir, name, "SKILL.md")
            if os.path.isfile(skill_md):
                candidates.append({"type": "skill", "name": name, "path": f"skills/{name}"})

    agents_dir = os.path.join(plugin_dir, "agents")
    if os.path.isdir(agents_dir):
        for filename in sorted(os.listdir(agents_dir)):
            if filename.endswith(".md"):
                candidates.append(
                    {"type": "agent", "name": filename[:-3], "path": f"agents/{filename}"}
                )

    commands_dir = os.path.join(plugin_dir, "commands")
    if os.path.isdir(commands_dir):
        for filename in sorted(os.listdir(commands_dir)):
            if filename.endswith(".md"):
                candidates.append(
                    {"type": "command", "name": filename[:-3], "path": f"commands/{filename}"}
                )

    hooks_json = os.path.join(plugin_dir, "hooks", "hooks.json")
    if os.path.isfile(hooks_json):
        with open(hooks_json, encoding="utf-8") as f:
            hooks_config = json.load(f)
        # Real hooks.json files nest events one level down under a "hooks"
        # key (alongside a sibling "description" string) -- fall back to the
        # top level only if that key is absent, so a bare {event: [...]}
        # shape still works too.
        events = hooks_config.get("hooks", hooks_config)
        for event_name, matchers in sorted(events.items()):
            if not isinstance(matchers, list):
                continue
            for i in range(len(matchers)):
                candidates.append(
                    {"type": "hook", "name": f"{event_name}-{i}", "path": "hooks/hooks.json"}
                )

    return candidates


def discover_manifest_declared(plugin_dir):
    """Detect logical types with no filesystem-convention detector, via
    plugin.json's own declarations. Returns [] gracefully when the manifest
    declares none -- a real absence, not a stub."""
    manifest_path = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    if not os.path.isfile(manifest_path):
        return []
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    declared = []
    for key, type_name in (("mcpServers", "mcp-server"), ("lspServers", "lsp-server")):
        entries = manifest.get(key)
        if isinstance(entries, dict):
            for name in sorted(entries):
                declared.append({"type": type_name, "name": name, "path": None})
    return declared


def discover_components(plugin_dir):
    return discover_filesystem_components(plugin_dir) + discover_manifest_declared(plugin_dir)


def empty_inventory(plugin_id, plugin_name):
    return {
        "schema_version": SCHEMA_VERSION,
        "plugin_id": plugin_id,
        "plugin_name": plugin_name,
        "updated_on": reconcile.today(),
        "components": [],
        "extensions": {},
    }


def build_plan(inventory, discovered):
    """Compare discovered candidates against the canonical inventory's
    current active components and produce a deterministic plan: add /
    update (path change) / no-op per candidate. Missing-active-component,
    rename detection, and a discovered candidate matching an existing
    *non-active* record (planned/retired/deprecated/superseded -- e.g. a
    planned component that has now actually been built) all need human
    identity confirmation, not a heuristic guess -- so all three are
    surfaced as `conflict` entries here, resolved later via an approved
    `status-transition` operation (see apply_status_transition), never
    auto-applied by this function."""
    existing_by_key = {(c["name"], c["type"]): c for c in inventory.get("components", [])}
    discovered_keys = {(c["name"], c["type"]) for c in discovered}
    plan = []

    for candidate in discovered:
        key = (candidate["name"], candidate["type"])
        existing = existing_by_key.get(key)
        if existing is None:
            plan.append(
                {
                    "operation": "add",
                    "name": candidate["name"],
                    "type": candidate["type"],
                    "path": candidate["path"],
                    "evidence": [candidate["path"]] if candidate["path"] else [],
                    "requires_approval": True,
                }
            )
        elif existing.get("status") == "active":
            if existing.get("path") != candidate["path"]:
                plan.append(
                    {
                        "operation": "update",
                        "id": existing["id"],
                        "name": candidate["name"],
                        "field": "path",
                        "old_value": existing.get("path"),
                        "new_value": candidate["path"],
                        "evidence": [candidate["path"]] if candidate["path"] else [],
                        "requires_approval": True,
                    }
                )
            else:
                plan.append(
                    {"operation": "no-op", "name": candidate["name"], "type": candidate["type"]}
                )
        else:
            plan.append(
                {
                    "operation": "conflict",
                    "id": existing["id"],
                    "name": existing["name"],
                    "type": existing["type"],
                    "reason": f"a discovered candidate matches an existing {existing['status']!r} "
                    "record -- requires a status-transition decision (e.g. activate a planned "
                    "component now that it's built, restore a retired/deprecated/superseded one) "
                    "before this can be reconciled, never an automatic no-op",
                    "requires_approval": True,
                }
            )

    for existing in inventory.get("components", []):
        key = (existing["name"], existing["type"])
        if existing.get("status") == "active" and key not in discovered_keys:
            plan.append(
                {
                    "operation": "conflict",
                    "id": existing["id"],
                    "name": existing["name"],
                    "type": existing["type"],
                    "reason": "active record's discovered path is missing -- requires a rename, "
                    "supersede, retire, or restoration decision, not an automatic retirement",
                    "requires_approval": True,
                }
            )

    return plan


def apply_add(inventory, operation, plugin_id_scope_ids):
    """`operation["status"]` defaults to `"active"` -- every candidate this
    script's own `discover`/`build_plan` produces (filesystem-detected or
    manifest-declared) genuinely exists right now, whether or not it has a
    filesystem `path`. Only the plugin-planning integration path (which
    constructs its own `add` operations by hand, outside `build_plan` --
    see SKILL.md's "Integration with plugin-planning") sets an explicit
    `"status": "planned"` for a not-yet-materialized component. Deriving
    status from `path` truthiness alone would wrongly demote a real,
    manifest-declared mcp-server/lsp-server (which never has a filesystem
    path) to "planned"."""
    new_id = models.generate_id("component", plugin_id_scope_ids)
    plugin_id_scope_ids.add(new_id)
    today = reconcile.today()
    status = operation.get("status", "active")
    models.validate_status(status)
    record = {
        "id": new_id,
        "type": operation["type"],
        "name": operation["name"],
        "path": operation["path"],
        "status": status,
        "status_history": [
            {
                "status": status,
                "valid_from": today,
                "valid_to": None,
                "reason": operation.get(
                    "status_reason",
                    "Discovered by plugin-inventory Build/Plan."
                    if status == "active"
                    else "Accepted planned component from plugin-planning.",
                ),
                "evidence": operation.get("evidence", []),
            }
        ],
        "functional_role": None,
        "domain": None,
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
        "details": {"schema": operation["type"]},
        "provenance": {},
    }
    inventory["components"].append(record)


def apply_plan(inventory, approved_operations):
    """Apply only the operations present in `approved_operations` (already
    filtered/approved by a human via the calling skill). A `conflict` entry
    itself is never applied directly -- an approved plan instead contains
    the human's actual resolution as a `status-transition` operation (or an
    `update`/`add`/`no-op`), never the bare `conflict` shape. Delegates the
    per-operation-type logic to the shared `inventory_common.reconcile`
    module -- only `apply_add` (the component-record shape) is this script's
    own."""
    return reconcile.apply_plan(
        inventory, approved_operations, apply_add, "components", ALLOWED_UPDATE_FIELDS
    )


def validate_inventory(inventory):
    """Cross-record invariants JSON Schema alone can't express. Delegates to
    the shared `inventory_common.reconcile.validate_records`, using this
    inventory's own `(name, type)` active-record uniqueness key."""
    reconcile.validate_records(
        inventory.get("components", []),
        uniqueness_key=lambda c: (c["name"], c["type"]),
    )


def cmd_discover(args):
    print(json.dumps(discover_components(args.plugin_dir), indent=2))


def cmd_bootstrap(args):
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.plugin_dir, INVENTORY_FILENAME
    )
    with json_store.InventoryLock(args.inventory_path):
        if os.path.exists(args.inventory_path):
            raise SystemExit(f"refusing to bootstrap: {args.inventory_path} already exists")
        inventory = empty_inventory(args.plugin_id, args.plugin_name)
        discovered = discover_components(args.plugin_dir)
        plan = build_plan(inventory, discovered)
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
    inventory = (
        json_store.read_json(args.inventory_path) if os.path.exists(args.inventory_path) else None
    )
    if inventory is None:
        raise SystemExit(f"no inventory at {args.inventory_path} -- run bootstrap first")
    discovered = discover_components(args.plugin_dir)
    plan = build_plan(inventory, discovered)
    print(
        json.dumps(
            {"expected_hash": json_store.compute_hash(inventory), "operations": plan},
            indent=2,
        )
    )


def cmd_apply(args):
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.plugin_dir, INVENTORY_FILENAME
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
        args.inventory_path, args.plugin_dir, INVENTORY_FILENAME
    )
    if args.target_type == "plugin":
        raise SystemExit(
            "target_type 'plugin' is not valid here -- a whole-plugin report belongs in "
            "marketplace-inventory's own inventory, not a single component's record"
        )

    def lookup(inventory):
        return next(
            (
                c
                for c in inventory["components"]
                if c["name"] == args.target and c["type"] == args.target_type
            ),
            None,
        )

    component, appended, security_appended = reconcile.cmd_import_grading_for_record(
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
                "current_score": component["score"],
                "current_security_score": component["security_score"],
            },
            indent=2,
        )
    )


def cmd_check(args):
    if not os.path.exists(args.inventory_path):
        raise SystemExit(f"no inventory at {args.inventory_path} -- run bootstrap first")
    inventory = json_store.read_json(args.inventory_path)
    reconcile.validate_or_exit(validate_inventory, inventory, context="check")
    discovered = discover_components(args.plugin_dir)
    plan = build_plan(inventory, discovered)
    drift = [op for op in plan if op["operation"] != "no-op"]
    print(json.dumps({"valid": True, "drift_count": len(drift), "drift": drift}, indent=2))


def cmd_repair_history(args):
    """The only mode allowed to rewrite existing history entries. The
    calling skill must show the user the exact before/after diff and get
    explicit approval before invoking this -- `--confirm <component_id>`
    (repeating the same id being repaired) is this function's own
    mechanical gate, so an invocation missing it fails closed instead of
    relying solely on the calling skill having actually shown that diff."""
    if args.confirm != args.component_id:
        raise SystemExit(
            "repair-history requires --confirm <component_id> to exactly match the "
            "component_id being repaired -- this is the destructive-rewrite gate; "
            "show the user the full before/after diff and get explicit approval first"
        )
    reconcile.require_inventory_path_under_scope_dir(
        args.inventory_path, args.plugin_dir, INVENTORY_FILENAME
    )
    with json_store.InventoryLock(args.inventory_path):
        inventory = json_store.read_json(args.inventory_path)
        component = next((c for c in inventory["components"] if c["id"] == args.component_id), None)
        if component is None:
            raise SystemExit(f"no component with id {args.component_id!r} in this inventory")
        if args.history_field not in ("status_history", "naming_history"):
            raise SystemExit("history_field must be 'status_history' or 'naming_history'")
        with open(args.replacement_history_path, encoding="utf-8") as f:
            replacement = json.load(f)
        reconcile.validate_or_exit(
            models.validate_history_periods,
            replacement,
            f"{args.component_id}.{args.history_field}",
            context="repair-history",
        )
        value_key = "status" if args.history_field == "status_history" else "name"
        open_value = models.open_period_value(replacement, value_key)
        current_value = (
            component["status"] if args.history_field == "status_history" else component["name"]
        )
        if open_value != current_value:
            raise SystemExit(
                f"replacement history's open period value {open_value!r} does not match "
                f"the record's current {value_key} {current_value!r} -- "
                "update one or the other first"
            )
        component[args.history_field] = replacement
        inventory["updated_on"] = reconcile.today()
        reconcile.validate_or_exit(
            json_store.atomic_write_json,
            args.inventory_path,
            inventory,
            validator=validate_inventory,
            context="repair-history",
        )
    print(json.dumps({"repaired": args.component_id, "field": args.history_field}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("discover")
    p.add_argument("plugin_dir")
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("bootstrap")
    p.add_argument("plugin_dir")
    p.add_argument("inventory_path")
    p.add_argument("plugin_id")
    p.add_argument("plugin_name")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("plan")
    p.add_argument("plugin_dir")
    p.add_argument("inventory_path")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("apply")
    p.add_argument("plugin_dir")
    p.add_argument("inventory_path")
    p.add_argument("approved_plan_path")
    p.add_argument("expected_hash")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("import-grading")
    p.add_argument("plugin_dir")
    p.add_argument("inventory_path")
    p.add_argument("report_path")
    p.add_argument("target")
    p.add_argument("target_type")
    p.set_defaults(func=cmd_import_grading)

    p = sub.add_parser("check")
    p.add_argument("inventory_path")
    p.add_argument("plugin_dir")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("repair-history")
    p.add_argument("plugin_dir")
    p.add_argument("inventory_path")
    p.add_argument("component_id")
    p.add_argument("history_field")
    p.add_argument("replacement_history_path")
    p.add_argument(
        "--confirm",
        required=True,
        help="must exactly equal component_id -- the mechanical confirmation gate for this "
        "destructive mode; the calling skill should only pass this after showing the user "
        "the full before/after diff and getting explicit approval",
    )
    p.set_defaults(func=cmd_repair_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
