import json

from scripts.marketplace_ci.validators import run_post_edit


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


def test_plugin_edit_cascades_to_registered_codex_export(hook_repo):
    _write_registry(hook_repo.root, plugin_mirrors=["sample-kit"], skills=["demo"])
    result = run_post_edit(hook_repo.root, "plugins/sample-kit/skills/demo/SKILL.md")
    assert result.changed == (".claude/skills/demo/SKILL.md", ".agents/skills/demo/SKILL.md")


def test_plugin_edit_without_codex_export_only_syncs_mirror(hook_repo):
    _write_registry(hook_repo.root, plugin_mirrors=["sample-kit"])
    result = run_post_edit(hook_repo.root, "plugins/sample-kit/skills/demo/SKILL.md")
    assert result.changed == (".claude/skills/demo/SKILL.md",)


def test_generated_destination_edit_is_never_reprocessed(hook_repo):
    _write_registry(hook_repo.root, plugin_mirrors=["sample-kit"], skills=["demo"])
    result = run_post_edit(hook_repo.root, ".agents/skills/demo/SKILL.md")
    assert result.changed == ()
    result = run_post_edit(hook_repo.root, ".codex/agents/demo.toml")
    assert result.changed == ()


def test_unrelated_edit_is_ignored(hook_repo):
    _write_registry(hook_repo.root, plugin_mirrors=["sample-kit"])
    result = run_post_edit(hook_repo.root, "README.md")
    assert result.changed == ()


def test_no_registry_returns_no_changes(hook_repo):
    result = run_post_edit(hook_repo.root, "plugins/sample-kit/skills/demo/SKILL.md")
    assert result.changed == ()


def test_second_run_is_idempotent(hook_repo):
    _write_registry(hook_repo.root, plugin_mirrors=["sample-kit"], skills=["demo"])
    first = run_post_edit(hook_repo.root, "plugins/sample-kit/skills/demo/SKILL.md")
    assert first.changed != ()
    second = run_post_edit(hook_repo.root, "plugins/sample-kit/skills/demo/SKILL.md")
    assert second.changed == ()  # already in sync; nothing left to apply
