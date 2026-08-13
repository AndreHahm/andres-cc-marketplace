from pathlib import Path

import pytest

from scripts.marketplace_ci.conversion import (
    ConversionError,
    convert_agent,
    find_legacy_command_exports,
    plan_exports,
)
from scripts.marketplace_ci.registry import Registry

AGENT_MARKDOWN = """---
name: demo
description: Reviews demo components
tools: ["Read", "Grep"]
model: sonnet
color: blue
---

Review the target carefully.
"""


def test_agent_conversion_preserves_description_tools_and_prompt():
    rendered = convert_agent(AGENT_MARKDOWN)
    assert 'description = "Reviews demo components"' in rendered
    assert 'tools = ["Read", "Grep"]' in rendered
    assert "Review the target carefully." in rendered


def test_legacy_source_command_is_blocking(repo):
    (repo / ".agents" / "skills" / "source-command-old").mkdir(parents=True)
    assert find_legacy_command_exports(repo) == (Path(".agents/skills/source-command-old"),)


def test_find_legacy_command_exports_returns_empty_when_none_exist(repo):
    assert find_legacy_command_exports(repo) == ()


def test_convert_agent_requires_frontmatter():
    with pytest.raises(ConversionError, match="frontmatter"):
        convert_agent("no frontmatter here")


def test_convert_agent_rejects_unsupported_field():
    markdown = """---
name: demo
description: Reviews demo components
extra_field: not allowed
---

Body.
"""
    with pytest.raises(ConversionError, match="unsupported"):
        convert_agent(markdown)


def test_convert_agent_rejects_missing_required_field():
    markdown = """---
name: demo
---

Body.
"""
    with pytest.raises(ConversionError, match="missing required"):
        convert_agent(markdown)


def test_convert_agent_omits_tools_line_when_absent():
    markdown = """---
name: demo
description: No special access needed.
---

Body text.
"""
    rendered = convert_agent(markdown)
    assert "tools" not in rendered
    assert 'name = "demo"' in rendered


def test_plan_exports_copies_skill_and_converts_agent(repo):
    registry = Registry(
        version=1, plugin_mirrors=(), skills=("export-demo",), agents=("export-demo",)
    )
    plan = plan_exports(repo, registry, previous=None)
    destinations = {
        action.destination.relative_to(repo).as_posix(): action for action in plan.actions
    }

    assert ".agents/skills/export-demo/SKILL.md" in destinations
    skill_action = destinations[".agents/skills/export-demo/SKILL.md"]
    assert skill_action.operation == "create"
    expected = (repo / ".claude" / "skills" / "export-demo" / "SKILL.md").read_bytes()
    assert skill_action.content == expected

    assert ".codex/agents/export-demo.toml" in destinations
    agent_action = destinations[".codex/agents/export-demo.toml"]
    assert agent_action.operation == "create"
    assert agent_action.content is not None
    assert b'description = "Reviews demo components"' in agent_action.content


def test_plan_exports_prunes_removed_agent(repo):
    previous = Registry(version=1, plugin_mirrors=(), skills=(), agents=("export-demo", "gone"))
    plan = plan_exports(repo, Registry.empty(), previous=previous)
    assert any(a.operation == "delete" and a.destination.name == "gone.toml" for a in plan.actions)
