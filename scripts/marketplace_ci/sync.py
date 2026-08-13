"""Plugin mirror synchronization: destination planning, atomic apply, and the
`hooks/hooks.json` structural-merge exception."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from scripts.marketplace_ci.registry import Registry, RemovalSet

COMPONENT_DIRS = ("skills", "agents", "commands", "hooks", "rules")
DEFAULT_REPO_HOOKS_PATH = Path("scripts/marketplace_ci/hooks/hooks.json")
DEFAULT_REPO_RULES_PATH = Path("scripts/marketplace_ci/rules")


class SyncError(RuntimeError):
    """Raised when a sync plan cannot be safely built or applied."""


@dataclass(frozen=True)
class SyncAction:
    operation: str  # "create" | "update" | "delete" | "warn" | "collision"
    source: Path | None
    destination: Path
    reason: str


@dataclass(frozen=True)
class SyncPlan:
    actions: tuple[SyncAction, ...]


@dataclass(frozen=True)
class SyncResult:
    applied: tuple[SyncAction, ...]


@dataclass(frozen=True)
class HooksMergePlan:
    actions: tuple[SyncAction, ...]
    merged_document: dict


def _iter_component_files(plugin_root: Path):
    for component_dir_name in COMPONENT_DIRS:
        component_dir = plugin_root / component_dir_name
        if not component_dir.is_dir():
            continue
        for path in sorted(component_dir.rglob("*")):
            if not path.is_file():
                continue
            if (
                component_dir_name == "hooks"
                and path.name == "hooks.json"
                and path.parent == component_dir
            ):
                continue  # excluded; handled by plan_hooks_merge
            yield path


def _resolve_destination(source: Path, relative_from: Path, dest_root: Path) -> Path:
    rel = source.relative_to(relative_from)
    dest = (dest_root / rel).resolve()
    dest_root_resolved = dest_root.resolve()
    if dest_root_resolved not in dest.parents and dest != dest_root_resolved:
        raise SyncError(f"resolved destination escapes {dest_root_resolved}: {dest}")
    return dest


def plan_plugin_sync(
    repo: Path,
    registry: Registry,
    previous: Registry | None,
    bootstrap: bool,
    repo_rules_path: Path | None = None,
) -> SyncPlan:
    plugins_root = repo / "plugins"
    claude_root = repo / ".claude"

    destinations: dict[Path, list[Path]] = {}

    def register(source: Path, relative_from: Path) -> None:
        dest = _resolve_destination(source, relative_from, claude_root)
        destinations.setdefault(dest, []).append(source)

    for plugin_name in registry.plugin_mirrors:
        plugin_root = plugins_root / plugin_name
        if not plugin_root.is_dir():
            continue
        for source_file in _iter_component_files(plugin_root):
            register(source_file, plugin_root)

    if repo_rules_path is not None and repo_rules_path.is_dir():
        for source_file in sorted(repo_rules_path.glob("*.md")):
            dest = (claude_root / "rules" / source_file.name).resolve()
            destinations.setdefault(dest, []).append(source_file)

    removed: RemovalSet = (
        registry.removed_since(previous) if previous is not None else RemovalSet((), (), ())
    )
    delete_destinations: dict[Path, Path] = {}
    for plugin_name in removed.plugin_mirrors:
        plugin_root = plugins_root / plugin_name
        if not plugin_root.is_dir():
            continue
        for source_file in _iter_component_files(plugin_root):
            dest = _resolve_destination(source_file, plugin_root, claude_root)
            delete_destinations[dest] = source_file

    actions: list[SyncAction] = []

    for dest, sources in sorted(destinations.items()):
        if len(sources) > 1:
            actions.append(
                SyncAction(
                    operation="collision",
                    source=None,
                    destination=dest,
                    reason=f"multiple sources map to {dest}: {[str(s) for s in sources]}",
                )
            )
            continue
        source = sources[0]
        source_bytes = source.read_bytes()
        if dest.exists():
            if dest.read_bytes() == source_bytes:
                continue
            actions.append(
                SyncAction(
                    operation="update",
                    source=source,
                    destination=dest,
                    reason="content differs from canonical source",
                )
            )
        else:
            actions.append(
                SyncAction(
                    operation="create",
                    source=source,
                    destination=dest,
                    reason="missing from destination",
                )
            )

    for dest, source in sorted(delete_destinations.items()):
        actions.append(
            SyncAction(
                operation="delete",
                source=source,
                destination=dest,
                reason="plugin no longer registered in plugin_mirrors",
            )
        )

    if bootstrap:
        known = set(destinations) | set(delete_destinations)
        for component_dir_name in COMPONENT_DIRS:
            dest_component_dir = claude_root / component_dir_name
            if not dest_component_dir.is_dir():
                continue
            for existing_file in sorted(dest_component_dir.rglob("*")):
                if not existing_file.is_file():
                    continue
                if (
                    component_dir_name == "hooks"
                    and existing_file.name == "hooks.json"
                    and existing_file.parent == dest_component_dir
                ):
                    continue
                resolved = existing_file.resolve()
                if resolved in known:
                    continue
                actions.append(
                    SyncAction(
                        operation="warn",
                        source=None,
                        destination=resolved,
                        reason="no canonical source found for this destination; "
                        "requires manual classification",
                    )
                )

    return SyncPlan(actions=tuple(actions))


def plan_hooks_merge(
    repo: Path,
    registry: Registry,
    repo_hooks_path: Path | None = None,
) -> HooksMergePlan:
    if repo_hooks_path is None:
        repo_hooks_path = repo / DEFAULT_REPO_HOOKS_PATH

    sources: list[tuple[str, Path]] = []
    for plugin_name in sorted(registry.plugin_mirrors):
        candidate = repo / "plugins" / plugin_name / "hooks" / "hooks.json"
        if candidate.is_file():
            sources.append((plugin_name, candidate))
    if repo_hooks_path.is_file():
        sources.append((str(repo_hooks_path), repo_hooks_path))
    sources.sort(key=lambda item: item[0])

    merged: dict[str, list[dict]] = {}
    for _, path in sources:
        document = json.loads(path.read_text(encoding="utf-8"))
        for event_key, entries in document.get("hooks", {}).items():
            merged.setdefault(event_key, []).extend(entries)

    merged_document = {"hooks": merged}
    destination = (repo / ".claude" / "hooks" / "hooks.json").resolve()
    new_bytes = (json.dumps(merged_document, indent=2) + "\n").encode("utf-8")

    actions: list[SyncAction] = []
    if destination.exists():
        if destination.read_bytes() != new_bytes:
            actions.append(
                SyncAction(
                    operation="update",
                    source=None,
                    destination=destination,
                    reason="merged hooks.json content changed",
                )
            )
    else:
        actions.append(
            SyncAction(
                operation="create",
                source=None,
                destination=destination,
                reason="merged hooks.json missing",
            )
        )

    return HooksMergePlan(actions=tuple(actions), merged_document=merged_document)


def _atomic_write(destination: Path, data: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.parent / f".{destination.name}.tmp"
    tmp_path.write_bytes(data)
    os.replace(tmp_path, destination)


def apply_sync_plan(plan: SyncPlan) -> SyncResult:
    blocking = [a for a in plan.actions if a.operation == "collision"]
    if blocking:
        raise SyncError(
            "refusing to apply a plan containing unresolved collisions: "
            + "; ".join(a.reason for a in blocking)
        )

    applied: list[SyncAction] = []
    for action in plan.actions:
        if action.operation in ("create", "update"):
            assert action.source is not None
            _atomic_write(action.destination, action.source.read_bytes())
            applied.append(action)
        elif action.operation == "delete":
            action.destination.unlink(missing_ok=True)
            applied.append(action)
        # "warn" actions are informational only; never executed.

    return SyncResult(applied=tuple(applied))


def apply_hooks_merge_plan(plan: HooksMergePlan) -> SyncResult:
    applied: list[SyncAction] = []
    for action in plan.actions:
        data = (json.dumps(plan.merged_document, indent=2) + "\n").encode("utf-8")
        _atomic_write(action.destination, data)
        applied.append(action)
    return SyncResult(applied=tuple(applied))
