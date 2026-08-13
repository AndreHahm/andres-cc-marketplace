"""Claude-to-Codex export conversion: skill copying, strict agent-to-TOML
conversion, and forward-looking `source-command-*` prevention."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.marketplace_ci.registry import Registry, RemovalSet
from scripts.marketplace_ci.sync import SyncAction, SyncPlan

_ALLOWED_FRONTMATTER_KEYS = {"name", "description", "tools", "model", "color"}
_REQUIRED_FRONTMATTER_KEYS = {"name", "description"}


class ConversionError(ValueError):
    """Raised when an agent Markdown source cannot be converted to Codex TOML."""


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _split_frontmatter(source: str) -> tuple[dict, str]:
    if not source.startswith("---"):
        raise ConversionError("agent markdown must start with YAML frontmatter delimited by '---'")
    parts = source.split("---", 2)
    if len(parts) < 3:
        raise ConversionError("agent markdown frontmatter is not closed with a second '---'")
    _, frontmatter_text, body = parts
    frontmatter = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(frontmatter, dict):
        raise ConversionError("agent frontmatter must be a YAML mapping")
    return frontmatter, body.lstrip("\n")


def convert_agent(source: str) -> str:
    frontmatter, body = _split_frontmatter(source)

    unknown = set(frontmatter) - _ALLOWED_FRONTMATTER_KEYS
    if unknown:
        raise ConversionError(f"unsupported agent frontmatter field(s): {sorted(unknown)}")
    missing = _REQUIRED_FRONTMATTER_KEYS - set(frontmatter)
    if missing:
        raise ConversionError(f"agent frontmatter missing required field(s): {sorted(missing)}")

    lines = [
        f'name = "{_toml_escape(str(frontmatter["name"]))}"',
        f'description = "{_toml_escape(str(frontmatter["description"]))}"',
    ]

    if "tools" in frontmatter:
        tools = frontmatter["tools"]
        if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
            raise ConversionError("agent frontmatter 'tools' must be a list of strings")
        rendered_tools = ", ".join(f'"{_toml_escape(t)}"' for t in tools)
        lines.append(f"tools = [{rendered_tools}]")

    body_text = body.rstrip("\n")
    lines.append(f'developer_instructions = """\n{body_text}"""')

    return "\n".join(lines) + "\n"


def find_legacy_command_exports(repo: Path) -> tuple[Path, ...]:
    skills_root = repo / ".agents" / "skills"
    if not skills_root.is_dir():
        return ()
    found = sorted(
        p for p in skills_root.iterdir() if p.is_dir() and p.name.startswith("source-command-")
    )
    return tuple(p.relative_to(repo) for p in found)


def plan_exports(
    repo: Path, registry: Registry, previous: Registry | None, bootstrap: bool = False
) -> SyncPlan:
    claude_agents_root = repo / ".claude" / "agents"
    claude_skills_root = repo / ".claude" / "skills"
    export_skills_root = repo / ".agents" / "skills"
    export_agents_root = repo / ".codex" / "agents"

    destinations: dict[Path, list[tuple[Path, bytes]]] = {}

    def register(source: Path, dest: Path, content: bytes) -> None:
        destinations.setdefault(dest.resolve(), []).append((source, content))

    for skill_name in registry.skills:
        source_dir = claude_skills_root / skill_name
        if not source_dir.is_dir():
            continue
        for file in sorted(source_dir.rglob("*")):
            if file.is_file():
                dest = export_skills_root / skill_name / file.relative_to(source_dir)
                register(file, dest, file.read_bytes())

    for agent_name in registry.agents:
        source_file = claude_agents_root / f"{agent_name}.md"
        if not source_file.is_file():
            continue
        content = convert_agent(source_file.read_text(encoding="utf-8")).encode("utf-8")
        dest = export_agents_root / f"{agent_name}.toml"
        register(source_file, dest, content)

    removed: RemovalSet = (
        registry.removed_since(previous) if previous is not None else RemovalSet((), (), ())
    )
    delete_destinations: dict[Path, Path] = {}
    for skill_name in removed.skills:
        source_dir = claude_skills_root / skill_name
        if not source_dir.is_dir():
            continue
        for file in sorted(source_dir.rglob("*")):
            if file.is_file():
                dest = (export_skills_root / skill_name / file.relative_to(source_dir)).resolve()
                delete_destinations[dest] = file
    for agent_name in removed.agents:
        source_file = claude_agents_root / f"{agent_name}.md"
        dest = (export_agents_root / f"{agent_name}.toml").resolve()
        delete_destinations[dest] = source_file

    actions: list[SyncAction] = []

    for dest, entries in sorted(destinations.items()):
        if len(entries) > 1:
            actions.append(
                SyncAction(
                    operation="collision",
                    source=None,
                    destination=dest,
                    reason=f"multiple sources map to {dest}",
                )
            )
            continue
        source, content = entries[0]
        if dest.exists():
            if dest.read_bytes() == content:
                continue
            actions.append(
                SyncAction(
                    operation="update",
                    source=source,
                    destination=dest,
                    reason="content differs from canonical source",
                    content=content,
                )
            )
        else:
            actions.append(
                SyncAction(
                    operation="create",
                    source=source,
                    destination=dest,
                    reason="missing from destination",
                    content=content,
                )
            )

    for dest, source in sorted(delete_destinations.items()):
        actions.append(
            SyncAction(
                operation="delete",
                source=source,
                destination=dest,
                reason="no longer registered in codex_exports",
            )
        )

    if bootstrap:
        known = set(destinations) | set(delete_destinations)
        if export_skills_root.is_dir():
            for existing_file in sorted(export_skills_root.rglob("*")):
                if not existing_file.is_file():
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
        if export_agents_root.is_dir():
            for existing_file in sorted(export_agents_root.glob("*.toml")):
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
