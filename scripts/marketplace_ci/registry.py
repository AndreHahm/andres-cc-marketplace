"""Marketplace mirror/export registry: schema, validation, and diffing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_VERSION = 1
_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_TOP_LEVEL_KEYS = {"version", "plugin_mirrors", "codex_exports"}
_CODEX_EXPORT_KEYS = {"skills", "agents"}


class RegistryError(ValueError):
    """Raised when a marketplace-sync registry file is malformed or invalid."""


def _validate_name(name: object, *, kind: str) -> str:
    if not isinstance(name, str) or not _NAME_PATTERN.match(name):
        raise RegistryError(
            f"{kind} must be an exact plugin name (lowercase letters, digits, hyphens; "
            f"no globs, slashes, or path traversal): {name!r}"
        )
    return name


def _validate_unique(names: tuple[str, ...], *, kind: str) -> None:
    seen: set[str] = set()
    for name in names:
        if name in seen:
            raise RegistryError(f"duplicate {kind} name: {name!r}")
        seen.add(name)


@dataclass(frozen=True)
class RemovalSet:
    plugin_mirrors: tuple[str, ...]
    skills: tuple[str, ...]
    agents: tuple[str, ...]


@dataclass(frozen=True)
class Registry:
    version: int
    plugin_mirrors: tuple[str, ...]
    skills: tuple[str, ...]
    agents: tuple[str, ...]

    @staticmethod
    def empty() -> Registry:
        return Registry(version=SUPPORTED_VERSION, plugin_mirrors=(), skills=(), agents=())

    @staticmethod
    def load(path: Path) -> Registry:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegistryError(f"{path}: invalid JSON: {exc}") from exc

        if not isinstance(raw, dict):
            raise RegistryError(f"{path}: top-level document must be an object")

        unknown_top_level = set(raw) - _TOP_LEVEL_KEYS
        if unknown_top_level:
            raise RegistryError(f"{path}: unknown top-level key(s): {sorted(unknown_top_level)}")

        version = raw.get("version")
        if version != SUPPORTED_VERSION:
            raise RegistryError(f"{path}: unsupported version: {version!r}")

        raw_mirrors = raw.get("plugin_mirrors", [])
        if not isinstance(raw_mirrors, list):
            raise RegistryError(f"{path}: plugin_mirrors must be a list")
        plugin_mirrors = tuple(
            _validate_name(name, kind="plugin_mirrors entry") for name in raw_mirrors
        )
        _validate_unique(plugin_mirrors, kind="plugin_mirrors")

        codex_exports = raw.get("codex_exports", {})
        if not isinstance(codex_exports, dict):
            raise RegistryError(f"{path}: codex_exports must be an object")
        unknown_export_keys = set(codex_exports) - _CODEX_EXPORT_KEYS
        if unknown_export_keys:
            raise RegistryError(
                f"{path}: unknown codex_exports key(s): {sorted(unknown_export_keys)}"
            )

        raw_skills = codex_exports.get("skills", [])
        if not isinstance(raw_skills, list):
            raise RegistryError(f"{path}: codex_exports.skills must be a list")
        skills = tuple(
            _validate_name(name, kind="codex_exports.skills entry") for name in raw_skills
        )
        _validate_unique(skills, kind="codex_exports.skills")

        raw_agents = codex_exports.get("agents", [])
        if not isinstance(raw_agents, list):
            raise RegistryError(f"{path}: codex_exports.agents must be a list")
        agents = tuple(
            _validate_name(name, kind="codex_exports.agents entry") for name in raw_agents
        )
        _validate_unique(agents, kind="codex_exports.agents")

        return Registry(
            version=version, plugin_mirrors=plugin_mirrors, skills=skills, agents=agents
        )

    def removed_since(self, previous: Registry) -> RemovalSet:
        """What `previous` had that `self` no longer has."""
        return RemovalSet(
            plugin_mirrors=tuple(
                p for p in previous.plugin_mirrors if p not in self.plugin_mirrors
            ),
            skills=tuple(s for s in previous.skills if s not in self.skills),
            agents=tuple(a for a in previous.agents if a not in self.agents),
        )
