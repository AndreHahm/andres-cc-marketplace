import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.marketplace_ci.sync import (
    SyncError,
    apply_hooks_merge_plan,
    apply_sync_plan,
    plan_hooks_merge,
    plan_plugin_sync,
    stage_generated_destinations,
    stage_hooks_merge_result,
)

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_REPO_HOOKS = FIXTURES / "repo-hooks" / "hooks.json"
FIXTURE_REPO_RULES = FIXTURES / "repo-rules"


def test_registered_plugin_syncs_only_executable_surface(repo, registry_for):
    plan = plan_plugin_sync(repo, registry_for("sample-kit"), previous=None, bootstrap=True)
    destinations = {action.destination.relative_to(repo).as_posix() for action in plan.actions}
    assert ".claude/skills/demo/SKILL.md" in destinations
    assert ".claude/README.md" not in destinations


def test_removed_plugin_prunes_destinations_from_previous_registry(repo, registry_for):
    from scripts.marketplace_ci.registry import Registry

    plan = plan_plugin_sync(
        repo, Registry.empty(), previous=registry_for("sample-kit"), bootstrap=False
    )
    assert any(action.operation == "delete" for action in plan.actions)


def test_two_plugins_hooks_json_concatenate_without_collision(repo, registry_for):
    plan = plan_hooks_merge(
        repo, registry_for("sample-kit", "sample-kit-two"), repo_hooks_path=FIXTURE_REPO_HOOKS
    )
    merged = plan.merged_document["hooks"]["PreToolUse"]
    matchers = [entry["matcher"] for entry in merged]
    assert matchers == ["Bash", "^(Bash|PowerShell)$"]
    assert not any(a.operation == "collision" for a in plan.actions)


def test_hooks_scripts_still_collide_normally(repo, registry_for):
    plan = plan_plugin_sync(
        repo, registry_for("sample-kit-two", "sample-kit-two-clone"), previous=None, bootstrap=True
    )
    assert any(
        a.operation == "collision" and a.destination.name == "guard.sh" for a in plan.actions
    )


def test_repo_owned_rule_maps_1to1_into_claude_rules(repo, registry_for):
    plan = plan_plugin_sync(
        repo,
        registry_for("sample-kit"),
        previous=None,
        bootstrap=True,
        repo_rules_path=FIXTURE_REPO_RULES,
    )
    destinations = {action.destination.relative_to(repo).as_posix() for action in plan.actions}
    assert ".claude/rules/example-rule.md" in destinations
    assert not any(a.operation == "collision" for a in plan.actions)


def test_apply_sync_plan_writes_created_files(repo, registry_for):
    plan = plan_plugin_sync(repo, registry_for("sample-kit"), previous=None, bootstrap=True)
    result = apply_sync_plan(plan)
    # "warn" actions (bootstrap orphan detection) are intentionally never applied;
    # only create/update/delete actions should come back in `applied`.
    executable = [a for a in plan.actions if a.operation in ("create", "update", "delete")]
    assert len(result.applied) == len(executable)
    dest = repo / ".claude" / "skills" / "demo" / "SKILL.md"
    assert dest.exists()
    assert (
        dest.read_bytes()
        == (repo / "plugins" / "sample-kit" / "skills" / "demo" / "SKILL.md").read_bytes()
    )


def test_apply_sync_plan_rejects_collisions(repo, registry_for):
    plan = plan_plugin_sync(
        repo, registry_for("sample-kit-two", "sample-kit-two-clone"), previous=None, bootstrap=True
    )
    with pytest.raises(SyncError, match="collision"):
        apply_sync_plan(plan)


def test_apply_sync_plan_deletes_pruned_destination(repo, registry_for):
    from scripts.marketplace_ci.registry import Registry

    create_plan = plan_plugin_sync(repo, registry_for("sample-kit"), previous=None, bootstrap=True)
    apply_sync_plan(create_plan)
    dest = repo / ".claude" / "skills" / "demo" / "SKILL.md"
    assert dest.exists()

    delete_plan = plan_plugin_sync(
        repo, Registry.empty(), previous=registry_for("sample-kit"), bootstrap=False
    )
    apply_sync_plan(delete_plan)
    assert not dest.exists()


def test_apply_hooks_merge_plan_writes_merged_document(repo, registry_for):
    plan = plan_hooks_merge(
        repo, registry_for("sample-kit", "sample-kit-two"), repo_hooks_path=FIXTURE_REPO_HOOKS
    )
    result = apply_hooks_merge_plan(plan)
    assert len(result.applied) == 1
    dest = repo / ".claude" / "hooks" / "hooks.json"
    assert dest.exists()
    import json

    on_disk = json.loads(dest.read_text(encoding="utf-8"))
    assert [e["matcher"] for e in on_disk["hooks"]["PreToolUse"]] == ["Bash", "^(Bash|PowerShell)$"]


def test_stage_generated_destinations_stages_only_actions_with_staged_source(
    git_repo, registry_for
):
    plan = plan_plugin_sync(
        git_repo.root, registry_for("sample-kit"), previous=None, bootstrap=True
    )
    apply_sync_plan(plan)
    subprocess.run(
        ["git", "add", "-f", "--", "plugins/sample-kit/skills/demo/SKILL.md"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )
    executable = tuple(a for a in plan.actions if a.operation in ("create", "update"))

    staged = stage_generated_destinations(git_repo.root, executable)

    dest = (git_repo.root / ".claude" / "skills" / "demo" / "SKILL.md").resolve()
    assert dest in staged
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ".claude/skills/demo/SKILL.md" in result.stdout.splitlines()


def test_stage_generated_destinations_skips_actions_without_staged_source(git_repo, registry_for):
    plan = plan_plugin_sync(
        git_repo.root, registry_for("sample-kit"), previous=None, bootstrap=True
    )
    apply_sync_plan(plan)
    executable = tuple(a for a in plan.actions if a.operation in ("create", "update"))

    staged = stage_generated_destinations(git_repo.root, executable)

    assert staged == ()
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == ""


def test_stage_generated_destinations_skips_partially_staged_source(git_repo, registry_for):
    plan = plan_plugin_sync(
        git_repo.root, registry_for("sample-kit"), previous=None, bootstrap=True
    )
    apply_sync_plan(plan)
    source = git_repo.root / "plugins" / "sample-kit" / "skills" / "demo" / "SKILL.md"
    subprocess.run(["git", "add", "-f", "--", str(source)], cwd=git_repo.root, check=True)
    # Further, unstaged edit on top of the already-staged content -- a partial stage.
    source.write_text(source.read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
    executable = tuple(a for a in plan.actions if a.operation in ("create", "update"))

    staged = stage_generated_destinations(git_repo.root, executable)

    assert staged == ()
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ".claude/skills/demo/SKILL.md" not in result.stdout.splitlines()


def test_stage_generated_destinations_wraps_git_add_failure_as_sync_error(git_repo, registry_for):
    plan = plan_plugin_sync(
        git_repo.root, registry_for("sample-kit"), previous=None, bootstrap=True
    )
    apply_sync_plan(plan)
    subprocess.run(
        ["git", "add", "-f", "--", "plugins/sample-kit/skills/demo/SKILL.md"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )
    executable = list(a for a in plan.actions if a.operation in ("create", "update"))
    real_action = next(
        a for a in executable if a.destination.name == "SKILL.md" and "demo" in a.destination.parts
    )
    outside_destination = git_repo.root.parent / "outside-the-repo.md"
    bad_action = replace(real_action, destination=outside_destination)

    with pytest.raises(SyncError, match="git add failed"):
        stage_generated_destinations(git_repo.root, (bad_action,))


def test_stage_hooks_merge_result_stages_when_contributing_source_staged(git_repo, registry_for):
    plan = plan_hooks_merge(
        git_repo.root,
        registry_for("sample-kit", "sample-kit-two"),
        repo_hooks_path=FIXTURE_REPO_HOOKS,
    )
    apply_hooks_merge_plan(plan)
    subprocess.run(
        ["git", "add", "-f", "--", "plugins/sample-kit/hooks/hooks.json"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )

    staged = stage_hooks_merge_result(git_repo.root, plan)

    dest = (git_repo.root / ".claude" / "hooks" / "hooks.json").resolve()
    assert dest in staged
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ".claude/hooks/hooks.json" in result.stdout.splitlines()


def test_stage_hooks_merge_result_skips_when_no_contributing_source_staged(git_repo, registry_for):
    plan = plan_hooks_merge(
        git_repo.root,
        registry_for("sample-kit", "sample-kit-two"),
        repo_hooks_path=FIXTURE_REPO_HOOKS,
    )
    apply_hooks_merge_plan(plan)

    staged = stage_hooks_merge_result(git_repo.root, plan)

    assert staged == ()
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == ""


def test_bootstrap_flags_orphan_destination_with_no_source(repo, registry_for):
    orphan = repo / ".claude" / "skills" / "ghost" / "SKILL.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("no canonical source", encoding="utf-8")

    plan = plan_plugin_sync(repo, registry_for("sample-kit"), previous=None, bootstrap=True)
    warnings = [a for a in plan.actions if a.operation == "warn"]
    assert any(a.destination == orphan.resolve() for a in warnings)
