"""Plugin mirror sync PLAN computation: read-only destination planning.

Split out of sync.py (issue #351, direction #3) so the review-dispatch-critical
path (compute-scope/codex-review/publish) can depend on the plan side alone,
without pulling in sync.py's apply/staging side (disk writes, `git add`) --
see review.py's dispatch_reviewers docstring and __main__.py's per-handler
lazy imports for how that isolation is actually used.
"""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

from scripts.marketplace_ci.registry import Registry, RemovalSet

COMPONENT_DIRS = ("skills", "agents", "commands", "hooks", "rules")
DEFAULT_REPO_RULES_PATH = Path("scripts/marketplace_ci/rules")


class SyncError(RuntimeError):
    """Raised when a sync plan cannot be safely built or applied."""


@dataclass(frozen=True)
class SyncAction:
    operation: str  # "create" | "update" | "delete" | "warn" | "missing_excepted" | "collision"
    source: Path | None
    destination: Path
    reason: str
    content: bytes | None = None  # overrides a raw source-bytes copy, e.g. converted agent TOML


@dataclass(frozen=True)
class SyncPlan:
    actions: tuple[SyncAction, ...]


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


def _is_executable(path: Path) -> bool:
    return bool(stat.S_IMODE(path.stat().st_mode) & 0o111)


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

    divergence_exceptions = {(exc.source, exc.dest) for exc in registry.divergence_exceptions}

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
    matched_exceptions: set[tuple[str, str]] = set()

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
        rel_source = source.relative_to(repo).as_posix()
        rel_dest = dest.relative_to(repo).as_posix()
        exception_key = (rel_source, rel_dest)
        is_excepted = exception_key in divergence_exceptions
        if is_excepted:
            matched_exceptions.add(exception_key)
        if dest.exists():
            if dest.read_bytes() == source_bytes:
                if _is_executable(dest) == _is_executable(source):
                    continue
                # Content already matches, but the executable bit has drifted (e.g.
                # a mirror lost its +x while retaining identical bytes) -- the
                # content-only comparison above would otherwise skip this file
                # forever, since it never re-runs once bytes match. Schedule an
                # "update" purely to let apply_sync_plan's _atomic_write(source=...)
                # re-copy the correct mode; the content it (re)writes is identical.
                actions.append(
                    SyncAction(
                        operation="update",
                        source=source,
                        destination=dest,
                        reason=(
                            "executable bit differs from canonical source (content already matches)"
                        ),
                    )
                )
                continue
            if is_excepted:
                # Whole-file exception (see registry.DivergenceException docstring) --
                # this destination is allowed to differ from its canonical source, so
                # never schedule a sync action that would overwrite it. Surfaced as an
                # informational "warn" (not a silent no-op) so the active divergence
                # stays visible on every check/check-all run, rather than requiring a
                # human to remember to manually re-compare -- mitigates the "unrelated
                # drift can hide indefinitely behind a whole-file exception" risk that
                # is otherwise inherent to a whole-file (not line-level) exception.
                actions.append(
                    SyncAction(
                        operation="warn",
                        source=None,
                        destination=dest,
                        reason=(
                            "intentionally divergent from its canonical source per a "
                            "declared divergence_exceptions entry -- re-confirm the "
                            "divergence is still only the documented, expected "
                            "difference, not unrelated drift"
                        ),
                    )
                )
                continue
            actions.append(
                SyncAction(
                    operation="update",
                    source=source,
                    destination=dest,
                    reason="content differs from canonical source",
                )
            )
        elif is_excepted:
            # The canonical source's own bytes are, by definition, wrong for this
            # destination (that's the entire reason the exception exists) -- never
            # auto-create it from the canonical source. But a *missing* destination is
            # not the same risk as a *differing* one: the exception permits divergent
            # CONTENT, never absence, so this stays a blocking "missing_excepted"
            # action (not "warn") -- `apply_sync_plan` never executes it either way
            # (its create/update/delete dispatch doesn't recognize this operation), so
            # this can never auto-write anything; only the exit-code/reporting
            # treatment differs from "warn". Devin's original finding asked for
            # exactly this: "emit a blocking/manual-repair action instead of creating
            # a broken mirror."
            actions.append(
                SyncAction(
                    operation="missing_excepted",
                    source=None,
                    destination=dest,
                    reason=(
                        "missing from destination, but excepted from canonical sync "
                        "(divergence_exceptions) -- recreating from the canonical source "
                        "would be incorrect; reconstruct this file's intended "
                        "destination-specific content manually"
                    ),
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

    # A declared exception whose (source, dest) never matched any real, registered
    # mirror pair above is dead configuration -- most likely a typo in
    # divergence_exceptions itself -- and the mirror pair it was actually meant to
    # protect is left unprotected. Surfaced as "warn" so it's visible on every
    # check/check-all run without blocking the commit.
    for exc in sorted(registry.divergence_exceptions, key=lambda e: (e.source, e.dest)):
        if (exc.source, exc.dest) in matched_exceptions:
            continue
        actions.append(
            SyncAction(
                operation="warn",
                source=None,
                destination=(repo / exc.dest).resolve(),
                reason=(
                    f"divergence_exceptions entry (source={exc.source!r}, "
                    f"dest={exc.dest!r}) does not match any registered mirror pair -- "
                    "likely a typo; this exception protects nothing, and its intended "
                    "pair (if any) is left unprotected"
                ),
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
