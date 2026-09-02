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


def test_agent_conversion_preserves_description_and_prompt_but_drops_tools():
    rendered = convert_agent(AGENT_MARKDOWN, "demo")
    assert 'description = "Reviews demo components"' in rendered
    assert "tools" not in rendered
    assert "Review the target carefully." in rendered


def test_convert_agent_always_emits_read_only_sandbox_mode():
    # Every exported agent needs its own sandbox_mode -- otherwise it silently
    # inherits the parent session's (e.g. a root config.toml's workspace-write)
    # instead of staying read-only. See conversion.py's own comment for why.
    rendered = convert_agent(AGENT_MARKDOWN, "demo")
    assert 'sandbox_mode = "read-only"' in rendered


def test_convert_agent_translates_model_to_codex_tier():
    rendered = convert_agent(AGENT_MARKDOWN, "demo")  # declares model: sonnet
    assert 'model = "gpt-5.6-terra"' in rendered


def test_convert_agent_rejects_name_registry_key_mismatch():
    # frontmatter 'name' must match the registry key the caller loaded this
    # source under -- otherwise _WORKSPACE_WRITE_AGENTS membership (and the
    # emitted `name` line itself) would be keyed off untrusted, self-reported
    # frontmatter instead of the actual registered agent identity.
    with pytest.raises(ConversionError, match="does not match its registry key"):
        convert_agent(AGENT_MARKDOWN, "not-demo")


@pytest.mark.parametrize(
    "claude_model,codex_model",
    [
        ("opus", "gpt-5.6-sol"),
        ("fable", "gpt-5.6-sol"),
        ("sonnet", "gpt-5.6-terra"),
        ("haiku", "gpt-5.6-luna"),
    ],
)
def test_convert_agent_model_mapping_per_tier(claude_model, codex_model):
    markdown = f"""---
name: demo
description: Reviews demo components
model: {claude_model}
---

Body.
"""
    rendered = convert_agent(markdown, "demo")
    assert f'model = "{codex_model}"' in rendered


def test_convert_agent_rejects_unmapped_model():
    markdown = """---
name: demo
description: Reviews demo components
model: gpt-4
---

Body.
"""
    with pytest.raises(ConversionError, match="no Codex tier mapping"):
        convert_agent(markdown, "demo")


def test_convert_agent_omits_model_line_for_inherit():
    # "inherit" means "use whatever model invoked this agent" -- not a fixed
    # tier, so nothing to translate; found live via work-intake-classifier.md
    # and work-transition-reviewer.md (plugins/workmanagement-kit/agents/),
    # both of which declare model: inherit.
    markdown = """---
name: demo
description: Reviews demo components
model: inherit
---

Body.
"""
    rendered = convert_agent(markdown, "demo")
    assert "model" not in rendered


def test_convert_agent_omits_model_line_when_absent():
    markdown = """---
name: demo
description: Reviews demo components
---

Body.
"""
    rendered = convert_agent(markdown, "demo")
    assert "model" not in rendered


def test_convert_agent_gives_smoke_tester_workspace_write():
    markdown = """---
name: smoke-tester
description: Runs smoke tests.
---

Body.
"""
    rendered = convert_agent(markdown, "smoke-tester")
    assert 'sandbox_mode = "workspace-write"' in rendered


def test_convert_agent_other_agents_stay_read_only():
    markdown = """---
name: some-other-reviewer
description: Reviews things.
---

Body.
"""
    rendered = convert_agent(markdown, "some-other-reviewer")
    assert 'sandbox_mode = "read-only"' in rendered


def test_legacy_source_command_is_blocking(repo):
    (repo / ".agents" / "skills" / "source-command-old").mkdir(parents=True)
    assert find_legacy_command_exports(repo) == (Path(".agents/skills/source-command-old"),)


def test_find_legacy_command_exports_returns_empty_when_none_exist(repo):
    assert find_legacy_command_exports(repo) == ()


def test_convert_agent_requires_frontmatter():
    with pytest.raises(ConversionError, match="frontmatter"):
        convert_agent("no frontmatter here", "demo")


def test_convert_agent_rejects_unsupported_field():
    markdown = """---
name: demo
description: Reviews demo components
extra_field: not allowed
---

Body.
"""
    with pytest.raises(ConversionError, match="unsupported"):
        convert_agent(markdown, "demo")


def test_convert_agent_accepts_and_drops_permission_mode():
    markdown = """---
name: demo
description: Reviews demo components
permissionMode: dontAsk
disallowedTools: ["Write"]
---

Body.
"""
    rendered = convert_agent(markdown, "demo")
    assert "permissionMode" not in rendered
    assert "disallowedTools" not in rendered
    assert 'name = "demo"' in rendered


def test_convert_agent_rejects_missing_required_field():
    markdown = """---
name: demo
---

Body.
"""
    with pytest.raises(ConversionError, match="missing required"):
        convert_agent(markdown, "demo")


def test_convert_agent_omits_tools_line_when_absent():
    markdown = """---
name: demo
description: No special access needed.
---

Body text.
"""
    rendered = convert_agent(markdown, "demo")
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


def test_plan_exports_bootstrap_flags_unregistered_agent_export_as_orphan(repo):
    orphan = repo / ".codex" / "agents" / "ghost-reviewer.toml"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('name = "ghost-reviewer"\n', encoding="utf-8")

    registry = Registry.empty()
    plan = plan_exports(repo, registry, previous=None, bootstrap=True)
    warnings = [a for a in plan.actions if a.operation == "warn"]
    assert any(a.destination == orphan.resolve() for a in warnings)


def test_plan_exports_without_bootstrap_ignores_unregistered_export(repo):
    orphan = repo / ".codex" / "agents" / "ghost-reviewer.toml"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('name = "ghost-reviewer"\n', encoding="utf-8")

    registry = Registry.empty()
    plan = plan_exports(repo, registry, previous=None, bootstrap=False)
    assert plan.actions == ()


def test_plan_exports_prunes_removed_agent(repo):
    previous = Registry(version=1, plugin_mirrors=(), skills=(), agents=("export-demo", "gone"))
    plan = plan_exports(repo, Registry.empty(), previous=previous)
    assert any(a.operation == "delete" and a.destination.name == "gone.toml" for a in plan.actions)
