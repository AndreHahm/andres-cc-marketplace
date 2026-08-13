import json

from scripts.marketplace_ci.validators import check_staged_parity


def _write_registry(repo, **kwargs):
    payload = {
        "version": 1,
        "plugin_mirrors": kwargs.get("plugin_mirrors", []),
        "codex_exports": {
            "skills": kwargs.get("skills", []),
            "agents": kwargs.get("agents", []),
        },
    }
    registry_path = repo / ".claude" / "marketplace-sync.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(payload), encoding="utf-8")


def test_unstaged_repair_does_not_satisfy_staged_parity(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.write(".claude/skills/demo/SKILL.md", "new")  # written but never `git add`-ed
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1
    assert any(".claude/skills/demo/SKILL.md" in m for m in result.messages)


def test_staged_mirror_matching_content_satisfies_parity(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.stage(".claude/skills/demo/SKILL.md", "new")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_staged_mirror_with_wrong_content_fails_parity(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.stage(".claude/skills/demo/SKILL.md", "stale content, never updated")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1


def test_unrelated_staged_change_does_not_trigger_parity_check(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("README.md", "unrelated change")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_no_registry_returns_ok(git_repo):
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_no_staged_changes_returns_ok(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_staged_converted_agent_export_matching_content_satisfies_parity(git_repo):
    _write_registry(git_repo.root, agents=["export-demo"])
    agent_markdown = """---
name: export-demo
description: Reviews demo components
tools: ["Read", "Grep"]
---

Review the target carefully.
"""
    from scripts.marketplace_ci.conversion import convert_agent

    git_repo.stage(".claude/agents/export-demo.md", agent_markdown)
    git_repo.stage(".codex/agents/export-demo.toml", convert_agent(agent_markdown))
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_staged_converted_agent_export_stale_content_fails_parity(git_repo):
    _write_registry(git_repo.root, agents=["export-demo"])
    agent_markdown = """---
name: export-demo
description: Reviews demo components
---

Review the target carefully.
"""
    git_repo.stage(".claude/agents/export-demo.md", agent_markdown)
    git_repo.stage(".codex/agents/export-demo.toml", 'name = "export-demo"\nstale = true\n')
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1
