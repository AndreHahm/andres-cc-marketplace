import shutil
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


def test_divergent_mirror_without_exception_is_scheduled_for_update(repo, registry_for):
    # Regression guard: proves the exception in the next test actually changes behavior,
    # rather than the destination never having been flagged as drifted in the first place.
    (repo / ".claude" / "skills" / "demo").mkdir(parents=True, exist_ok=True)
    (repo / ".claude" / "skills" / "demo" / "SKILL.md").write_text(
        "genuinely different mirror content", encoding="utf-8"
    )
    plan = plan_plugin_sync(repo, registry_for("sample-kit"), previous=None, bootstrap=False)
    updates = {
        action.destination.relative_to(repo).as_posix()
        for action in plan.actions
        if action.operation == "update"
    }
    assert ".claude/skills/demo/SKILL.md" in updates


def test_divergence_exception_prevents_post_edit_sync_from_overwriting_mirror(repo):
    # This is the Codex-found gap this test closes: check_staged_parity respecting the
    # exception isn't enough on its own -- plan_plugin_sync (run on every watched edit via
    # run_post_edit, independent of any commit-time check) must respect it too, or the very
    # next unrelated edit silently overwrites the intentionally-divergent mirror. An
    # informational "warn" action is expected (see the Devin-found "unrelated drift can hide
    # indefinitely" gap) -- what must never happen is a "create"/"update" that would touch
    # the file on disk.
    from scripts.marketplace_ci.registry import DivergenceException, Registry

    (repo / ".claude" / "skills" / "demo").mkdir(parents=True, exist_ok=True)
    (repo / ".claude" / "skills" / "demo" / "SKILL.md").write_text(
        "genuinely different mirror content", encoding="utf-8"
    )
    registry = Registry(
        version=1,
        plugin_mirrors=("sample-kit",),
        skills=(),
        agents=(),
        divergence_exceptions=(
            DivergenceException(
                source="plugins/sample-kit/skills/demo/SKILL.md",
                dest=".claude/skills/demo/SKILL.md",
                reason="test: intentionally divergent for a documented reason",
            ),
        ),
    )
    plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=False)
    matching = [
        action
        for action in plan.actions
        if action.destination.relative_to(repo).as_posix() == ".claude/skills/demo/SKILL.md"
    ]
    assert len(matching) == 1
    assert matching[0].operation == "warn"
    assert (
        repo / ".claude" / "skills" / "demo" / "SKILL.md"
    ).read_text() == "genuinely different mirror content"


def test_divergence_exception_missing_destination_stays_blocking(repo):
    # Devin's original finding: an excepted destination that doesn't exist yet (not just
    # mismatched) must never be silently created from the canonical source's own bytes --
    # those bytes are, by definition, wrong for this destination. Must produce a distinct,
    # blocking "missing_excepted" action, never "create" -- and, per Codex's follow-up
    # finding on the same case, never a non-blocking "warn" either: the exception permits
    # divergent CONTENT, never absence, so a missing destination stays a real problem.
    from scripts.marketplace_ci.registry import DivergenceException, Registry

    registry = Registry(
        version=1,
        plugin_mirrors=("sample-kit",),
        skills=(),
        agents=(),
        divergence_exceptions=(
            DivergenceException(
                source="plugins/sample-kit/skills/demo/SKILL.md",
                dest=".claude/skills/demo/SKILL.md",
                reason="test: intentionally divergent for a documented reason",
            ),
        ),
    )
    plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=False)
    matching = [
        action
        for action in plan.actions
        if action.destination.relative_to(repo).as_posix() == ".claude/skills/demo/SKILL.md"
    ]
    assert len(matching) == 1
    assert matching[0].operation == "missing_excepted"
    assert not (repo / ".claude" / "skills" / "demo" / "SKILL.md").exists()


def test_divergence_exception_typo_warns_as_unmatched(repo):
    # Devin-found gap: a divergence_exceptions entry whose (source, dest) doesn't match any
    # real, registered mirror pair is dead configuration (most likely a typo) and leaves its
    # intended pair unprotected. Must be surfaced, not silently ignored.
    from scripts.marketplace_ci.registry import DivergenceException, Registry

    registry = Registry(
        version=1,
        plugin_mirrors=("sample-kit",),
        skills=(),
        agents=(),
        divergence_exceptions=(
            DivergenceException(
                source="plugins/sample-kit/skills/demo/SKILL.mdd",  # typo: trailing "d"
                dest=".claude/skills/demo/SKILL.md",
                reason="test: a typo'd source path",
            ),
        ),
    )
    plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=False)
    warn_reasons = [
        action.reason
        for action in plan.actions
        if action.operation == "warn"
        and "does not match any registered mirror pair" in action.reason
    ]
    assert len(warn_reasons) == 1
    assert "SKILL.mdd" in warn_reasons[0]


def test_divergence_exception_matched_pair_produces_no_typo_warning(repo, registry_for):
    # Regression guard: a correctly-declared exception (matching a real pair, files identical)
    # must never trigger the unmatched-exception warning above.
    from scripts.marketplace_ci.registry import DivergenceException, Registry

    registry = Registry(
        version=1,
        plugin_mirrors=("sample-kit",),
        skills=(),
        agents=(),
        divergence_exceptions=(
            DivergenceException(
                source="plugins/sample-kit/skills/demo/SKILL.md",
                dest=".claude/skills/demo/SKILL.md",
                reason="test: correctly declared, dest not created yet",
            ),
        ),
    )
    plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=False)
    assert not any(
        "does not match any registered mirror pair" in action.reason for action in plan.actions
    )


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
    # repo_rules_path must live under `repo` -- plan_plugin_sync resolves every source's
    # path relative to `repo` (for divergence-exception lookups), matching how the real
    # CLI always calls this with a repo-relative path (see __main__.py's _repo_rules_path).
    repo_rules_path = repo / "repo-rules"
    shutil.copytree(FIXTURE_REPO_RULES, repo_rules_path)
    plan = plan_plugin_sync(
        repo,
        registry_for("sample-kit"),
        previous=None,
        bootstrap=True,
        repo_rules_path=repo_rules_path,
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


def _commit_baseline(git_repo) -> None:
    """Commit every fixture file as-is -- the state before the change under test. Without this,
    every plugin file starts genuinely untracked ("??"), which `_is_fully_staged` correctly treats
    as unsafe (an untracked file is not reflected in any commit yet); a realistic test needs an
    already-committed, untouched sibling plugin to exercise "this one's fine, that one isn't"."""
    subprocess.run(["git", "add", "-A"], cwd=git_repo.root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "baseline"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )


def test_stage_hooks_merge_result_stages_when_contributing_source_staged(git_repo, registry_for):
    _commit_baseline(git_repo)
    plan = plan_hooks_merge(
        git_repo.root,
        registry_for("sample-kit", "sample-kit-two"),
        repo_hooks_path=FIXTURE_REPO_HOOKS,
    )
    apply_hooks_merge_plan(plan)
    source_a = git_repo.root / "plugins" / "sample-kit" / "hooks" / "hooks.json"
    source_a.write_text(source_a.read_text(encoding="utf-8") + "\n", encoding="utf-8")
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
    _commit_baseline(git_repo)
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


def test_stage_hooks_merge_result_skips_when_another_contributor_is_partially_staged(
    git_repo, registry_for
):
    _commit_baseline(git_repo)
    plan = plan_hooks_merge(
        git_repo.root,
        registry_for("sample-kit", "sample-kit-two"),
        repo_hooks_path=FIXTURE_REPO_HOOKS,
    )
    apply_hooks_merge_plan(plan)
    source_a = git_repo.root / "plugins" / "sample-kit" / "hooks" / "hooks.json"
    source_b = git_repo.root / "plugins" / "sample-kit-two" / "hooks" / "hooks.json"
    source_a.write_text(source_a.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", "--", str(source_a)], cwd=git_repo.root, check=True)
    # source_b gets an unstaged edit -- merged_document already reflects it (plan_hooks_merge reads
    # working-tree bytes), but it was never staged for source_b.
    source_b.write_text(source_b.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    staged = stage_hooks_merge_result(git_repo.root, plan)

    assert staged == ()
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ".claude/hooks/hooks.json" not in result.stdout.splitlines()


def test_stage_hooks_merge_result_stages_when_a_contributing_source_is_deleted(
    git_repo, registry_for
):
    _commit_baseline(git_repo)
    plan = plan_hooks_merge(
        git_repo.root,
        registry_for("sample-kit", "sample-kit-two"),
        repo_hooks_path=FIXTURE_REPO_HOOKS,
    )
    apply_hooks_merge_plan(plan)
    source_b = git_repo.root / "plugins" / "sample-kit-two" / "hooks" / "hooks.json"
    subprocess.run(["git", "rm", "-f", "--", str(source_b)], cwd=git_repo.root, check=True)
    # The deletion changes what the merge should contain -- re-plan against the now-single-source
    # registry to get the merged_document/actions a real caller would apply and stage.
    post_delete_plan = plan_hooks_merge(
        git_repo.root, registry_for("sample-kit"), repo_hooks_path=FIXTURE_REPO_HOOKS
    )
    apply_hooks_merge_plan(post_delete_plan)

    # A real caller (the CLI) always re-plans against the *current* registry/filesystem state --
    # post_delete_plan.sources no longer lists sample-kit-two's hooks.json at all (it's gone from
    # disk), which is exactly the shape that needs the staged-deletion detection to notice.
    staged = stage_hooks_merge_result(git_repo.root, post_delete_plan)

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


def test_bootstrap_flags_orphan_destination_with_no_source(repo, registry_for):
    orphan = repo / ".claude" / "skills" / "ghost" / "SKILL.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("no canonical source", encoding="utf-8")

    plan = plan_plugin_sync(repo, registry_for("sample-kit"), previous=None, bootstrap=True)
    warnings = [a for a in plan.actions if a.operation == "warn"]
    assert any(a.destination == orphan.resolve() for a in warnings)
