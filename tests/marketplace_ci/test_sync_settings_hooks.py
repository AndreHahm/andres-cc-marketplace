"""Tests for plan_settings_hooks_sync / plan_external_hook_scripts_mirror -- the
project-relative ${CLAUDE_PLUGIN_ROOT} -> ${CLAUDE_PROJECT_DIR} rewrite that makes
.claude/settings.json's own `hooks` key live-loadable (issue #374).

Uses the `widget-kit` fixture plugin (tests/marketplace_ci/fixtures/plugins/widget-kit)
rather than this repo's own real codex-kit/context-kit content, and always passes an
explicit `external_mirrors` override -- so these tests exercise the rewrite mechanism
itself, independent of EXTERNAL_HOOK_SCRIPT_MIRRORS's real, currently-live entries.
"""

import json

import pytest

from scripts.marketplace_ci.sync import (
    SyncError,
    apply_sync_plan,
    plan_external_hook_scripts_mirror,
    plan_hooks_merge,
    plan_settings_hooks_sync,
)

WIDGET_EXTERNAL_MIRRORS = (("widget-kit", "scripts/widget.py"),)


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
