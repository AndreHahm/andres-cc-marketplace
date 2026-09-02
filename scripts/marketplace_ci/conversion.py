"""Claude-to-Codex export conversion: skill copying, strict agent-to-TOML
conversion, and forward-looking `source-command-*` prevention."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.marketplace_ci.registry import Registry, RemovalSet
from scripts.marketplace_ci.sync import SyncAction, SyncPlan

_ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "tools",
    "model",
    "color",
    "permissionMode",
    "disallowedTools",
}
_REQUIRED_FRONTMATTER_KEYS = {"name", "description"}

# Claude model family -> Codex GPT-5.6 tier, per this marketplace's own
# delegation policy (.codex/config.toml's developer_instructions): Opus/Fable
# are the flagship tier (-> Sol), Sonnet is the balanced mid-tier (-> Terra),
# Haiku is the fast/cheap tier (-> Luna). Source: fixed model catalog
# confirmed against Codex's GPT-5.6 tier documentation, 2026-09-02.
_MODEL_MAP = {
    "opus": "gpt-5.6-sol",
    "fable": "gpt-5.6-sol",
    "sonnet": "gpt-5.6-terra",
    "haiku": "gpt-5.6-luna",
}

# Agents whose documented job requires executing commands (not just reading/
# analyzing) need workspace-write, not the read-only default below -- keep
# this list to the minimum agents that actually need it, not a blanket
# override. smoke-tester's whole job is running `python`/`node` against each
# skill's scripts/smoke_test.*; under read-only, Codex cannot run a command
# at all without an approval prompt per turn (confirmed against Codex's own
# sandbox behavior, 2026-09-02), breaking its documented non-interactive
# batch-sweep workflow.
_WORKSPACE_WRITE_AGENTS = {"smoke-tester"}


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

    name = str(frontmatter["name"])
    lines = [
        f'name = "{_toml_escape(name)}"',
        f'description = "{_toml_escape(str(frontmatter["description"]))}"',
    ]

    # Codex's custom-subagent TOML schema has no `tools` field (only name,
    # description, developer_instructions are required; model,
    # model_reasoning_effort, sandbox_mode, mcp_servers, skills.config are the
    # only supported optional fields) — `tools` is Claude-side-only and must
    # not be carried into the export.
    # https://learn.chatgpt.com/docs/agent-configuration/subagents?surface=app
    #
    # Translate the Claude source's `model` into the matching Codex tier,
    # rather than silently dropping it -- an untranslated model would leave
    # every exported agent using whatever [agents].default_subagent_model
    # happens to be, regardless of what the source actually declared. Fail
    # closed on an unrecognized value instead of silently falling through.
    if "model" in frontmatter:
        source_model = str(frontmatter["model"]).lower()
        if source_model == "inherit":
            # "inherit" means "use whatever model invoked this agent" -- not a
            # fixed tier, so there's nothing to translate. Omit the line and
            # let Codex's own [agents] default apply, the same fallback
            # behavior as declaring no model preference at all.
            pass
        elif source_model not in _MODEL_MAP:
            raise ConversionError(
                f"agent frontmatter 'model' {source_model!r} has no Codex tier mapping "
                f"(known: {sorted(_MODEL_MAP)} plus 'inherit')"
            )
        else:
            lines.append(f'model = "{_MODEL_MAP[source_model]}"')

    # A custom subagent with no sandbox_mode of its own inherits the parent
    # session's sandbox_mode (see docs/codex-subagents-schema.md) -- since
    # `tools` above is dropped rather than translated, every exported agent
    # needs an explicit sandbox_mode or it silently inherits whatever the
    # root config.toml sets (currently workspace-write). Every agent this
    # marketplace currently exports is a read-only reviewer/classifier except
    # smoke-tester (_WORKSPACE_WRITE_AGENTS above), which needs to actually
    # run commands.
    sandbox_mode = "workspace-write" if name in _WORKSPACE_WRITE_AGENTS else "read-only"
    lines.append(f'sandbox_mode = "{sandbox_mode}"')

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
