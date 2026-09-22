"""Tests for plan_settings_hooks_sync / plan_external_hook_scripts_mirror -- the
project-relative ${CLAUDE_PLUGIN_ROOT} -> ${CLAUDE_PROJECT_DIR} rewrite that makes
.claude/settings.json's own `hooks` key live-loadable (issue #374).

Uses the `widget-kit` fixture plugin (tests/marketplace_ci/fixtures/plugins/widget-kit)
rather than this repo's own real codex-kit/context-kit content, and always passes an
explicit `external_mirrors` override -- so these tests exercise the rewrite mechanism
itself, independent of EXTERNAL_HOOK_SCRIPT_MIRRORS's real, currently-live entries.
"""

import json
import subprocess

import pytest

from scripts.marketplace_ci.sync import (
    SyncError,
    apply_sync_plan,
    plan_external_hook_scripts_mirror,
    plan_hooks_merge,
    plan_settings_hooks_sync,
    stage_settings_hooks_result,
)

WIDGET_EXTERNAL_MIRRORS = (("widget-kit", "scripts/widget.py"),)


def _commit_baseline(git_repo) -> None:
    """Commit every fixture file as-is -- the state before the change under test."""
    subprocess.run(["git", "add", "-A"], cwd=git_repo.root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "baseline"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )


def test_plan_settings_hooks_sync_rewrites_component_dir_reference(repo, registry_for):
    hooks_plan = plan_hooks_merge(repo, registry_for("widget-kit"))
    settings_plan = plan_settings_hooks_sync(
        repo, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    commands = [
        h["command"]
        for entry in settings_plan.rewritten_hooks_document["hooks"]["PreToolUse"]
        for h in entry["hooks"]
    ]
    # Original fixture quoting is `"${CLAUDE_PLUGIN_ROOT}"/hooks/scripts/thing.sh` (quote
    # closes right after the variable) -- the rewrite re-attaches that closing quote at
    # the end of the full new path rather than leaving it mid-string; still shell-valid.
    assert '"${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/thing.sh"' in commands
    assert not any("CLAUDE_PLUGIN_ROOT" in c for c in commands)


def test_plan_settings_hooks_sync_rewrites_external_mirror_reference(repo, registry_for):
    hooks_plan = plan_hooks_merge(repo, registry_for("widget-kit"))
    settings_plan = plan_settings_hooks_sync(
        repo, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    commands = [
        h["command"]
        for entry in settings_plan.rewritten_hooks_document["hooks"]["PreToolUse"]
        for h in entry["hooks"]
    ]
    expected = (
        '"${CLAUDE_PROJECT_DIR}/.claude/hooks/_external-scripts/widget-kit/scripts/widget.py"'
    )
    assert any(expected in c for c in commands)


def test_plan_settings_hooks_sync_raises_on_unresolvable_reference(repo, registry_for):
    # No external_mirrors entry for widget-kit's scripts/widget.py reference -- the
    # generic component-dir rewrite can't resolve it either (scripts/ isn't a
    # mirrored component dir), so this must fail loud rather than ship a broken path.
    hooks_plan = plan_hooks_merge(repo, registry_for("widget-kit"))
    with pytest.raises(SyncError, match="unresolvable"):
        plan_settings_hooks_sync(repo, hooks_plan, external_mirrors=())


def test_plan_settings_hooks_sync_preserves_other_settings_keys(repo, registry_for):
    from scripts.marketplace_ci.sync_plan import SyncPlan

    settings_path = repo / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps({"worktree": {"bgIsolation": "none"}}, indent=2) + "\n", encoding="utf-8"
    )
    hooks_plan = plan_hooks_merge(repo, registry_for("widget-kit"))
    settings_plan = plan_settings_hooks_sync(
        repo, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    apply_sync_plan(SyncPlan(actions=settings_plan.actions))
    written = json.loads(settings_path.read_text(encoding="utf-8"))
    assert written["worktree"] == {"bgIsolation": "none"}
    assert "hooks" in written


def test_plan_settings_hooks_sync_create_action_when_settings_missing(repo, registry_for):
    hooks_plan = plan_hooks_merge(repo, registry_for("widget-kit"))
    settings_plan = plan_settings_hooks_sync(
        repo, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    assert len(settings_plan.actions) == 1
    assert settings_plan.actions[0].operation == "create"
    assert settings_plan.actions[0].destination.name == "settings.json"


def test_plan_settings_hooks_sync_no_action_once_applied(repo, registry_for):
    from scripts.marketplace_ci.sync_plan import SyncPlan

    hooks_plan = plan_hooks_merge(repo, registry_for("widget-kit"))
    first_plan = plan_settings_hooks_sync(
        repo, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    apply_sync_plan(SyncPlan(actions=first_plan.actions))

    second_plan = plan_settings_hooks_sync(
        repo, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    assert second_plan.actions == ()


def test_plan_external_hook_scripts_mirror_creates_destination(repo, registry_for):
    from scripts.marketplace_ci.sync_plan import SyncPlan

    plan = plan_external_hook_scripts_mirror(
        repo, registry_for("widget-kit"), external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    assert len(plan.actions) == 1
    assert plan.actions[0].operation == "create"
    apply_sync_plan(SyncPlan(actions=plan.actions))
    dest = repo / ".claude" / "hooks" / "_external-scripts" / "widget-kit" / "scripts" / "widget.py"
    assert dest.exists()
    source = repo / "plugins" / "widget-kit" / "scripts" / "widget.py"
    assert dest.read_bytes() == source.read_bytes()


def test_plan_external_hook_scripts_mirror_skips_unregistered_plugin(repo, registry_for):
    # widget-kit isn't in this registry at all -- the entry must be skipped
    # entirely, not raise, even though its own source file exists on disk.
    plan = plan_external_hook_scripts_mirror(
        repo, registry_for("sample-kit"), external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    assert plan.actions == ()


def test_plan_external_hook_scripts_mirror_raises_when_registered_source_missing(
    repo, registry_for
):
    stale_mirrors = (("widget-kit", "scripts/does-not-exist.py"),)
    with pytest.raises(SyncError, match="has no source file"):
        plan_external_hook_scripts_mirror(
            repo, registry_for("widget-kit"), external_mirrors=stale_mirrors
        )


def test_stage_settings_hooks_result_stages_when_contributing_source_staged(git_repo, registry_for):
    _commit_baseline(git_repo)
    hooks_plan = plan_hooks_merge(git_repo.root, registry_for("widget-kit"))
    source = git_repo.root / "plugins" / "widget-kit" / "hooks" / "hooks.json"
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", "--", "plugins/widget-kit/hooks/hooks.json"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )
    settings_plan = plan_settings_hooks_sync(
        git_repo.root, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    apply_sync_plan(_as_sync_plan(settings_plan))

    staged = stage_settings_hooks_result(git_repo.root, _as_hooks_merge_plan(settings_plan))

    dest = (git_repo.root / ".claude" / "settings.json").resolve()
    assert dest in staged
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ".claude/settings.json" in result.stdout.splitlines()


def test_stage_settings_hooks_result_skips_when_settings_json_has_unstaged_edit(
    git_repo, registry_for
):
    # The exact regression this test guards: Codex's cross-model review (round 3) found
    # that reusing stage_hooks_merge_result alone for settings.json only checks the
    # contributing hook-manifest sources are fully staged -- it never checks whether
    # .claude/settings.json ITSELF has an unstaged edit of its own, even though
    # plan_settings_hooks_sync reads that file's current content directly. Without
    # stage_settings_hooks_result's own extra check, an unrelated unstaged settings.json
    # tweak would be silently swept into the commit the moment the unrelated hook change
    # is staged.
    settings_path = git_repo.root / ".claude" / "settings.json"
    git_repo.stage(".claude/settings.json", json.dumps({"worktree": {"bgIsolation": "none"}}))
    _commit_baseline(git_repo)

    hooks_plan = plan_hooks_merge(git_repo.root, registry_for("widget-kit"))
    source = git_repo.root / "plugins" / "widget-kit" / "hooks" / "hooks.json"
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", "--", "plugins/widget-kit/hooks/hooks.json"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )
    # Unrelated, unstaged local edit directly to settings.json -- never `git add`-ed.
    settings_path.write_text(
        json.dumps({"worktree": {"bgIsolation": "full"}}, indent=2) + "\n", encoding="utf-8"
    )

    settings_plan = plan_settings_hooks_sync(
        git_repo.root, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    apply_sync_plan(_as_sync_plan(settings_plan))

    staged = stage_settings_hooks_result(git_repo.root, _as_hooks_merge_plan(settings_plan))

    assert staged == ()
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ".claude/settings.json" not in result.stdout.splitlines()


def test_stage_settings_hooks_result_skips_when_no_contributing_source_staged(
    git_repo, registry_for
):
    _commit_baseline(git_repo)
    hooks_plan = plan_hooks_merge(git_repo.root, registry_for("widget-kit"))
    settings_plan = plan_settings_hooks_sync(
        git_repo.root, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    apply_sync_plan(_as_sync_plan(settings_plan))

    staged = stage_settings_hooks_result(git_repo.root, _as_hooks_merge_plan(settings_plan))

    assert staged == ()


def test_stage_settings_hooks_result_skips_when_settings_json_preexists_untracked(
    git_repo, registry_for
):
    # The exact residual gap round-3's fix (tracked-in-index check) still had: Codex's
    # cross-model review round 4 found that a settings.json which existed on disk with
    # real, unrelated content -- but was NEVER tracked by git at all -- also isn't "fully
    # staged" (an untracked file has no staged baseline), yet the round-3 fix's
    # tracked-in-index gate skipped the check entirely for anything untracked, treating
    # it the same as a genuinely brand-new file. This exercises the fix that replaced
    # that gate with plan.actions[0].operation ("create" vs "update"), which correctly
    # tells a genuinely-new file apart from a pre-existing-but-untracked one.
    _commit_baseline(git_repo)
    settings_path = git_repo.root / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    # Pre-existing, real content -- never `git add`-ed, so it's untracked, not "new".
    settings_path.write_text(
        json.dumps({"worktree": {"bgIsolation": "none"}}, indent=2) + "\n", encoding="utf-8"
    )

    hooks_plan = plan_hooks_merge(git_repo.root, registry_for("widget-kit"))
    source = git_repo.root / "plugins" / "widget-kit" / "hooks" / "hooks.json"
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", "--", "plugins/widget-kit/hooks/hooks.json"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )

    settings_plan = plan_settings_hooks_sync(
        git_repo.root, hooks_plan, external_mirrors=WIDGET_EXTERNAL_MIRRORS
    )
    assert settings_plan.actions[0].operation == "update"  # pre-existing content, not "create"
    apply_sync_plan(_as_sync_plan(settings_plan))

    staged = stage_settings_hooks_result(git_repo.root, _as_hooks_merge_plan(settings_plan))

    assert staged == ()
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ".claude/settings.json" not in result.stdout.splitlines()


def _as_sync_plan(settings_plan):
    from scripts.marketplace_ci.sync_plan import SyncPlan

    return SyncPlan(actions=settings_plan.actions)


def _as_hooks_merge_plan(settings_plan):
    from scripts.marketplace_ci.sync import HooksMergePlan

    return HooksMergePlan(
        actions=settings_plan.actions,
        merged_document=settings_plan.rewritten_hooks_document,
        sources=settings_plan.sources,
    )
