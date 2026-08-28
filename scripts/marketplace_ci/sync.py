"""Plugin mirror synchronization: destination planning, atomic apply, and the
`hooks/hooks.json` structural-merge exception."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.marketplace_ci.git_state import GitState
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
    content: bytes | None = None  # overrides a raw source-bytes copy, e.g. converted agent TOML


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
    sources: tuple[Path, ...] = ()


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

    return HooksMergePlan(
        actions=tuple(actions),
        merged_document=merged_document,
        sources=tuple(path for _, path in sources),
    )


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
            if action.content is not None:
                data = action.content
            else:
                assert action.source is not None
                data = action.source.read_bytes()
            _atomic_write(action.destination, data)
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


def _staged_path_set(repo: Path) -> set[str]:
    return {
        path
        for change in GitState(repo=repo).staged_paths()
        for path in (change.old_path, change.new_path)
        if path is not None
    }


def _is_fully_staged(repo: Path, path: Path) -> bool:
    """True when `path` has no unstaged worktree changes on top of what's staged -- i.e. the
    index content `git diff --cached` shows for it is the same content actually on disk.

    `plan_plugin_sync`/`plan_exports` read a canonical source's *working-tree* bytes
    (`source.read_bytes()`), not its staged (index) content. If a source is only partially
    staged (some hunks staged, some not), the generated destination gets built from the fuller
    working-tree version and then staged as if it matched -- `check_staged_parity` then rejects
    the commit, since the staged destination no longer byte-matches the staged source. Same
    Y-character check `lint-staged-python.sh` already uses for the identical reason.

    `:(top,literal)` anchors the match to the repo root regardless of `cwd` -- but that magic
    word only makes sense applied to a repo-relative pathspec; `path` itself may be absolute
    (every `SyncAction.source`/`HooksMergePlan.sources` entry is), so it's resolved relative to
    `repo` first.
    """
    rel_path = path.resolve().relative_to(repo.resolve()).as_posix()
    result = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--", f":(top,literal){rel_path}"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    entries = result.stdout.split(b"\0")
    if not entries or not entries[0]:
        return True  # nothing pending for this path at all -- trivially fully staged
    status_line = entries[0].decode("utf-8", errors="surrogateescape")
    return status_line[1:2] == " "


def _git_add_forced(repo: Path, destination: Path) -> None:
    # -f: a generated destination under .claude/.codex/.agents is a deliberately tracked file
    # regardless of what a machine-local global gitignore says about those directory names (some
    # machines exclude them everywhere) -- same override the test suite's own
    # GitRepoHelper.stage() already applies for the identical reason.
    #
    # A destination path here is untrusted plugin content on a fetched or contributed branch;
    # it reaches `git` as a single literal argv element via `subprocess.run`'s list form -- never
    # interpolated into a shell command string -- so the shell never re-parses it and no
    # quoting/injection concern applies regardless of what characters the path contains.
    try:
        subprocess.run(["git", "add", "-f", "--", str(destination)], cwd=repo, check=True)
    except subprocess.CalledProcessError as exc:
        raise SyncError(f"git add failed for {destination}: {exc}") from exc


def stage_generated_destinations(repo: Path, actions: tuple[SyncAction, ...]) -> tuple[Path, ...]:
    """Stage each applied create/update action's destination, but only when its own canonical
    `source` is already staged in this commit *and* that source has no unstaged changes on top
    (see `_is_fully_staged`) -- leaving an unrelated repair (drift the sync happened to also fix)
    or a partially-staged source's mismatched destination untouched on disk, unstaged.
    """
    staged = _staged_path_set(repo)
    repo_resolved = repo.resolve()
    staged_destinations: list[Path] = []
    for action in actions:
        if action.operation not in ("create", "update") or action.source is None:
            continue
        rel_source = action.source.resolve().relative_to(repo_resolved).as_posix()
        if rel_source not in staged or not _is_fully_staged(repo, action.source):
            continue
        _git_add_forced(repo, action.destination)
        staged_destinations.append(action.destination)
    return tuple(staged_destinations)


def stage_hooks_merge_result(repo: Path, plan: HooksMergePlan) -> tuple[Path, ...]:
    """Stage the merged `hooks.json` destination(s) when at least one contributing per-plugin
    `hooks/hooks.json` (or the repo-level hooks path) is staged and fully staged.

    The merge has no single 1:1 canonical source the way `plan_plugin_sync`/`plan_exports` do --
    one destination is built from N contributing files -- so `stage_generated_destinations`
    (which requires exactly one `action.source`) never covers it; every `HooksMergePlan` action
    carries `source=None`. Without this, staging a canonical `plugins/<name>/hooks/hooks.json`
    change leaves the regenerated `.claude/hooks/hooks.json` unstaged and unstageable by
    `--stage`, silently narrowing coverage versus the old fully-manual step 8 flow this replaced.
    """
    staged = _staged_path_set(repo)
    repo_resolved = repo.resolve()
    any_staged_source = False
    for source in plan.sources:
        try:
            rel_source = source.resolve().relative_to(repo_resolved).as_posix()
        except ValueError:
            continue  # a source outside the repo (e.g. a caller-supplied external path) can't
            # be "staged" in this repo's index at all
        if rel_source in staged and _is_fully_staged(repo, source):
            any_staged_source = True
    if not any_staged_source:
        return ()
    staged_destinations: list[Path] = []
    for action in plan.actions:
        _git_add_forced(repo, action.destination)
        staged_destinations.append(action.destination)
    return tuple(staged_destinations)
