"""Stable command-line interface for scripts.marketplace_ci.

Exit codes: 0 = pass, 1 = policy failure, 2 = invalid invocation/configuration.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.marketplace_ci.conversion import find_legacy_command_exports, plan_exports
from scripts.marketplace_ci.registry import Registry, RegistryError
from scripts.marketplace_ci.sync import (
    DEFAULT_REPO_RULES_PATH,
    SyncError,
    apply_hooks_merge_plan,
    apply_sync_plan,
    plan_hooks_merge,
    plan_plugin_sync,
)

REGISTRY_RELATIVE_PATH = Path(".claude/marketplace-sync.json")


def _load_registry(repo: Path) -> Registry:
    return Registry.load(repo / REGISTRY_RELATIVE_PATH)


def _load_previous_registry(repo: Path) -> Registry | None:
    result = subprocess.run(
        ["git", "show", f"HEAD:{REGISTRY_RELATIVE_PATH.as_posix()}"],
        cwd=repo,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return Registry.loads(
        result.stdout.decode("utf-8"), source="HEAD:" + REGISTRY_RELATIVE_PATH.as_posix()
    )


def _report(label: str, actions, repo: Path) -> bool:
    """Print each action using a repo-relative posix path; return True if any
    non-warn action exists."""
    has_problem = False
    for action in actions:
        try:
            shown = action.destination.relative_to(repo).as_posix()
        except ValueError:
            shown = action.destination.as_posix()
        print(f"[{label}] {action.operation}: {shown} - {action.reason}")
        if action.operation != "warn":
            has_problem = True
    return has_problem


def _repo_rules_path(repo: Path) -> Path | None:
    candidate = repo / DEFAULT_REPO_RULES_PATH
    return candidate if candidate.is_dir() else None


def _handle_check_plugin_mirrors(args: argparse.Namespace) -> int:
    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"check-plugin-mirrors: {exc}", file=sys.stderr)
        return 2
    plan = plan_plugin_sync(
        repo, registry, previous=None, bootstrap=False, repo_rules_path=_repo_rules_path(repo)
    )
    if not plan.actions:
        print("check-plugin-mirrors: OK")
        return 0
    _report("mirrors", plan.actions, repo)
    return 1


def _handle_sync_plugin_mirrors(args: argparse.Namespace) -> int:
    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"sync-plugin-mirrors: {exc}", file=sys.stderr)
        return 2
    plan = plan_plugin_sync(
        repo, registry, previous=None, bootstrap=False, repo_rules_path=_repo_rules_path(repo)
    )
    try:
        result = apply_sync_plan(plan)
    except SyncError as exc:
        print(f"sync-plugin-mirrors: {exc}", file=sys.stderr)
        return 1
    hooks_plan = plan_hooks_merge(repo, registry)
    apply_hooks_merge_plan(hooks_plan)
    print(f"sync-plugin-mirrors: applied {len(result.applied)} action(s)")
    return 0


def _handle_check_codex_exports(args: argparse.Namespace) -> int:
    repo = Path.cwd()
    legacy = find_legacy_command_exports(repo)
    if legacy:
        for path in legacy:
            print(f"check-codex-exports: blocking legacy command export: {path}")
        return 1
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"check-codex-exports: {exc}", file=sys.stderr)
        return 2
    plan = plan_exports(repo, registry, previous=None)
    if not plan.actions:
        print("check-codex-exports: OK")
        return 0
    _report("exports", plan.actions, repo)
    return 1


def _handle_convert_codex_exports(args: argparse.Namespace) -> int:
    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"convert-codex-exports: {exc}", file=sys.stderr)
        return 2
    plan = plan_exports(repo, registry, previous=None)
    try:
        result = apply_sync_plan(plan)
    except SyncError as exc:
        print(f"convert-codex-exports: {exc}", file=sys.stderr)
        return 1
    print(f"convert-codex-exports: applied {len(result.applied)} action(s)")
    return 0


def _handle_check_all(args: argparse.Namespace) -> int:
    mirrors_rc = _handle_check_plugin_mirrors(args)
    exports_rc = _handle_check_codex_exports(args)
    rc = 2 if (mirrors_rc == 2 or exports_rc == 2) else (1 if (mirrors_rc or exports_rc) else 0)

    if getattr(args, "json_output", None):
        payload = {
            "check_plugin_mirrors": mirrors_rc,
            "check_codex_exports": exports_rc,
            "exit_code": rc,
        }
        Path(args.json_output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return rc


def _handle_repair_all(args: argparse.Namespace) -> int:
    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"repair-all: {exc}", file=sys.stderr)
        return 2

    previous = _load_previous_registry(repo) if args.bootstrap else None
    rules_path = _repo_rules_path(repo)

    mirror_plan = plan_plugin_sync(
        repo, registry, previous=previous, bootstrap=args.bootstrap, repo_rules_path=rules_path
    )
    export_plan = plan_exports(repo, registry, previous=previous, bootstrap=args.bootstrap)
    hooks_plan = plan_hooks_merge(repo, registry)

    all_actions = (*mirror_plan.actions, *export_plan.actions, *hooks_plan.actions)
    if not all_actions:
        print("repair-all: nothing to do")
        return 0

    _report("mirrors", mirror_plan.actions, repo)
    _report("exports", export_plan.actions, repo)
    _report("hooks", hooks_plan.actions, repo)

    if args.bootstrap and not args.apply:
        print("repair-all: bootstrap plan printed above; re-run with --apply to execute")
        return 0

    try:
        mirror_result = apply_sync_plan(mirror_plan)
        export_result = apply_sync_plan(export_plan)
        hooks_result = apply_hooks_merge_plan(hooks_plan)
    except SyncError as exc:
        print(f"repair-all: {exc}", file=sys.stderr)
        return 1

    applied_count = (
        len(mirror_result.applied) + len(export_result.applied) + len(hooks_result.applied)
    )
    print(f"repair-all: applied {applied_count} action(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.marketplace_ci")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "check-plugin-mirrors", help="verify .claude mirrors match the registry"
    ).set_defaults(handler=_handle_check_plugin_mirrors)

    subparsers.add_parser("sync-plugin-mirrors", help="apply .claude mirror parity").set_defaults(
        handler=_handle_sync_plugin_mirrors
    )

    subparsers.add_parser(
        "check-codex-exports", help="verify .agents/.codex exports match the registry"
    ).set_defaults(handler=_handle_check_codex_exports)

    subparsers.add_parser(
        "convert-codex-exports", help="apply .agents/.codex export parity"
    ).set_defaults(handler=_handle_convert_codex_exports)

    check_all = subparsers.add_parser("check-all", help="run every deterministic check")
    check_all.add_argument("--json-output", metavar="PATH", help="also write a JSON report")
    check_all.set_defaults(handler=_handle_check_all)

    repair_all = subparsers.add_parser(
        "repair-all", help="reconcile mirrors/exports/hooks against the registry"
    )
    repair_all.add_argument(
        "--bootstrap", action="store_true", help="also reconcile unregistered destinations"
    )
    repair_all.add_argument(
        "--apply", action="store_true", help="execute a --bootstrap plan (otherwise plan-only)"
    )
    repair_all.set_defaults(handler=_handle_repair_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
