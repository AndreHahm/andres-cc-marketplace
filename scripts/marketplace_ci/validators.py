"""Portable validator orchestration: the repository/plugin validator catalog,
subprocess-based black-box execution of plugin validators, and the delta-scoped
structural check `dispatch_reviewers` (Task 9) reuses in-process."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.marketplace_ci.conversion import plan_exports
from scripts.marketplace_ci.git_state import ChangedPath
from scripts.marketplace_ci.registry import Registry
from scripts.marketplace_ci.sync import plan_plugin_sync

_INTERPRETER_COMMAND = {"python": "python", "bash": "bash"}


@dataclass(frozen=True)
class PluginValidatorEntry:
    id: str
    plugin: str
    path: Path
    interpreter: str  # "python" | "bash"
    platforms: tuple[str, ...]  # platforms this entry can run on directly
    kind: str = "black-box"  # "black-box" | "out-of-scope"
    note: str | None = None


@dataclass(frozen=True)
class RepositoryValidatorEntry:
    id: str
    kind: str  # "reusable" | "adaptable" | "superseded"
    module: str
    description: str


@dataclass(frozen=True)
class ValidatorCatalog:
    repository_validators: tuple[RepositoryValidatorEntry, ...] = ()
    plugin_validators: tuple[PluginValidatorEntry, ...] = ()


@dataclass(frozen=True)
class ValidatorResult:
    id: str
    status: str  # "passed" | "failed" | "skipped"
    reason: str | None = None


def load_catalog(path: Path) -> ValidatorCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    repository_validators = tuple(
        RepositoryValidatorEntry(
            id=entry["id"],
            kind=entry["kind"],
            module=entry["module"],
            description=entry["description"],
        )
        for entry in raw.get("repository_validators", [])
    )
    plugin_validators = tuple(
        PluginValidatorEntry(
            id=entry["id"],
            plugin=entry["plugin"],
            path=Path(entry["path"]),
            interpreter=entry["interpreter"],
            platforms=tuple(entry["platforms"]),
            kind=entry.get("kind", "black-box"),
            note=entry.get("note"),
        )
        for entry in raw.get("plugin_validators", [])
    )
    return ValidatorCatalog(
        repository_validators=repository_validators, plugin_validators=plugin_validators
    )


def run_catalog(catalog: ValidatorCatalog, platform: str) -> tuple[ValidatorResult, ...]:
    """Run every plugin-owned validator as a black-box subprocess.

    Repository-owned validators are never listed here for execution — they're
    invoked directly, in-process, by the CLI commands that already implement
    them (`check-plugin-mirrors`, `check-codex-exports`, ...).
    """
    results: list[ValidatorResult] = []
    for entry in catalog.plugin_validators:
        if entry.kind == "out-of-scope":
            continue
        if platform not in entry.platforms:
            results.append(
                ValidatorResult(
                    id=entry.id,
                    status="skipped",
                    reason=f"{entry.interpreter.capitalize()} prerequisite unavailable on "
                    f"{platform.capitalize()}",
                )
            )
            continue
        argv = [_INTERPRETER_COMMAND[entry.interpreter], entry.path.as_posix()]
        completed = subprocess.run(argv, check=False, capture_output=True)
        if completed.returncode == 0:
            results.append(ValidatorResult(id=entry.id, status="passed"))
        else:
            results.append(
                ValidatorResult(
                    id=entry.id, status="failed", reason=f"exit code {completed.returncode}"
                )
            )
    return tuple(results)


@dataclass(frozen=True)
class Finding:
    path: str
    operation: str
    reason: str


def _component_key(path: str, depth: int = 4) -> str:
    parts = path.split("/")
    return "/".join(parts[:depth])


def run_delta_structural_checks(
    repo: Path, changed: tuple[ChangedPath, ...]
) -> tuple[Finding, ...]:
    """Scope `check-all`'s mirror/export parity checks to only the components
    touched by `changed`. This is the same structural-validation logic
    `check-all` runs in full; Task 9's Delta Validate calls it directly."""
    registry_path = repo / ".claude" / "marketplace-sync.json"
    if not registry_path.is_file():
        return ()
    registry = Registry.load(registry_path)

    changed_paths = {cp.new_path or cp.old_path for cp in changed}
    changed_paths.discard(None)
    changed_keys = {_component_key(p) for p in changed_paths if p is not None}
    if not changed_keys:
        return ()

    mirror_plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=False)
    export_plan = plan_exports(repo, registry, previous=None)

    findings: list[Finding] = []
    for action in (*mirror_plan.actions, *export_plan.actions):
        if action.operation == "delete" or action.source is None:
            continue
        try:
            rel_source = action.source.relative_to(repo).as_posix()
        except ValueError:
            rel_source = action.source.as_posix()
        if _component_key(rel_source) in changed_keys:
            findings.append(
                Finding(path=rel_source, operation=action.operation, reason=action.reason)
            )

    return tuple(findings)
