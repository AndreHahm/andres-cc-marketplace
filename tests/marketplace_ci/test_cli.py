import json

import pytest

from scripts.marketplace_ci.__main__ import main


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
    return registry_path


def test_main_with_no_command_returns_2(monkeypatch, repo):
    monkeypatch.chdir(repo)
    assert main([]) == 2


def test_check_plugin_mirrors_fails_when_out_of_sync(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    assert main(["check-plugin-mirrors"]) == 1


def test_sync_then_check_plugin_mirrors_passes(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    assert main(["sync-plugin-mirrors"]) == 0
    assert main(["check-plugin-mirrors"]) == 0
    assert (repo / ".claude" / "skills" / "demo" / "SKILL.md").exists()


def test_check_codex_exports_blocks_legacy_command_export(monkeypatch, repo):
    _write_registry(repo)
    (repo / ".agents" / "skills" / "source-command-old").mkdir(parents=True)
    monkeypatch.chdir(repo)
    assert main(["check-codex-exports"]) == 1


def test_convert_then_check_codex_exports_passes(monkeypatch, repo):
    _write_registry(repo, skills=["export-demo"], agents=["export-demo"])
    monkeypatch.chdir(repo)
    assert main(["convert-codex-exports"]) == 0
    assert main(["check-codex-exports"]) == 0
    assert (repo / ".agents" / "skills" / "export-demo" / "SKILL.md").exists()
    assert (repo / ".codex" / "agents" / "export-demo.toml").exists()


def test_check_all_ok_after_full_sync(monkeypatch, repo):
    _write_registry(
        repo, plugin_mirrors=["sample-kit"], skills=["export-demo"], agents=["export-demo"]
    )
    monkeypatch.chdir(repo)
    assert main(["sync-plugin-mirrors"]) == 0
    assert main(["convert-codex-exports"]) == 0
    assert main(["check-all"]) == 0


def test_check_all_writes_json_output(monkeypatch, repo, tmp_path):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    out = tmp_path / "report.json"
    rc = main(["check-all", "--json-output", str(out)])
    assert rc == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["exit_code"] == 1


def test_repair_all_bootstrap_without_apply_does_not_write(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    rc = main(["repair-all", "--bootstrap"])
    assert rc == 0
    assert not (repo / ".claude" / "skills" / "demo" / "SKILL.md").exists()


def test_repair_all_bootstrap_with_apply_writes(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    rc = main(["repair-all", "--bootstrap", "--apply"])
    assert rc == 0
    assert (repo / ".claude" / "skills" / "demo" / "SKILL.md").exists()


def test_repair_all_applied_count_excludes_warn_actions(monkeypatch, repo, capsys):
    from scripts.marketplace_ci.conversion import plan_exports
    from scripts.marketplace_ci.registry import Registry
    from scripts.marketplace_ci.sync import plan_hooks_merge, plan_plugin_sync

    orphan = repo / ".claude" / "skills" / "ghost" / "SKILL.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("no canonical source", encoding="utf-8")

    _write_registry(repo, plugin_mirrors=["sample-kit"])
    registry = Registry.load(repo / ".claude" / "marketplace-sync.json")
    mirror_plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=True)
    export_plan = plan_exports(repo, registry, previous=None, bootstrap=True)
    hooks_plan = plan_hooks_merge(repo, registry)
    all_actions = (*mirror_plan.actions, *export_plan.actions, *hooks_plan.actions)
    expected_applied = sum(1 for a in all_actions if a.operation != "warn")
    assert any(a.operation == "warn" for a in all_actions)  # the orphan is really in the plan

    monkeypatch.chdir(repo)
    rc = main(["repair-all", "--bootstrap", "--apply"])
    assert rc == 0

    out = capsys.readouterr().out
    summary_line = next(line for line in out.splitlines() if line.startswith("repair-all: applied"))
    applied_count = int(summary_line.split()[2])
    assert applied_count == expected_applied  # never inflated by the never-applied warn
    assert orphan.exists()  # untouched; warn actions are never executed


def test_registry_missing_returns_2(monkeypatch, repo):
    monkeypatch.chdir(repo)
    assert main(["check-plugin-mirrors"]) == 2


def test_help_text_lists_commands(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for command in (
        "check-plugin-mirrors",
        "sync-plugin-mirrors",
        "check-codex-exports",
        "convert-codex-exports",
        "check-all",
        "repair-all",
    ):
        assert command in out


def test_check_all_staged_fails_on_unstaged_mirror_repair(monkeypatch, git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.write(".claude/skills/demo/SKILL.md", "new")  # never staged
    monkeypatch.chdir(git_repo.root)
    assert main(["check-all", "--staged"]) == 1


def test_check_all_staged_passes_when_index_is_consistent(monkeypatch, git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.stage(".claude/skills/demo/SKILL.md", "new")
    monkeypatch.chdir(git_repo.root)
    assert main(["check-all", "--staged"]) == 0


def test_check_all_committed_rejects_unresolvable_ref(monkeypatch, git_repo):
    _write_registry(git_repo.root)
    monkeypatch.chdir(git_repo.root)
    assert main(["check-all", "--committed", "not-a-real-ref"]) == 2
