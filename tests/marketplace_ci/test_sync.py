import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.marketplace_ci.sync import (
    SyncError,
    apply_hooks_merge_plan,
    apply_sync_plan,
    plan_hooks_merge,
    stage_generated_destinations,
    stage_hooks_merge_result,
)
from scripts.marketplace_ci.sync_plan import plan_plugin_sync

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_REPO_HOOKS = FIXTURES / "repo-hooks" / "hooks.json"
FIXTURE_REPO_RULES = FIXTURES / "repo-rules"

# Windows' filesystem/CPython stat layer doesn't support real POSIX permission
# bits at all -- os.chmod on Windows only toggles the read-only attribute, so
# `path.chmod(0o755)` never actually sets an execute bit to observe, and
# `stat().st_mode & 0o111` is always 0 regardless of what's requested. This
# isn't a gap in sync.py/sync_plan.py (both are correctly POSIX-semantics code
# exercised for real on CI's ubuntu-latest runners) -- it's the same
# platform-can't-do-this shape as test_prefix_check.py's own `requires_symlinks`
# marker (symlink creation needing elevation on Windows), applied here to
# executable-bit tests instead.
requires_posix_permission_bits = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows' os.chmod/stat don't support real POSIX executable bits",
)


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


@requires_posix_permission_bits
def test_apply_sync_plan_preserves_executable_bit_on_create(repo, registry_for):
    # Regression guard (Codex PR #349 review): _atomic_write used to always create the
    # destination at write_bytes()'s own default mode, silently dropping an executable
    # source's execute bit -- a hook/bin script mirrored this way fails at runtime with
    # "Permission denied" (exit 126) even though its content is byte-identical.
    source = repo / "plugins" / "sample-kit-two" / "hooks" / "scripts" / "guard.sh"
    source.chmod(0o755)
    plan = plan_plugin_sync(repo, registry_for("sample-kit-two"), previous=None, bootstrap=True)
    apply_sync_plan(plan)
    dest = repo / ".claude" / "hooks" / "scripts" / "guard.sh"
    assert dest.exists()
    assert dest.stat().st_mode & 0o777 == 0o755


@requires_posix_permission_bits
def test_plan_plugin_sync_detects_executable_bit_only_drift(repo, registry_for):
    # Codex review finding on PR #349: the content-only `dest.read_bytes() ==
    # source_bytes` comparison treated a byte-identical destination as fully synced
    # forever, even if its mode drifted afterward (e.g. a mirror lost its +x bit while
    # keeping identical content) -- apply_sync_plan's copymode fix (the test above)
    # never re-runs for an already-existing, byte-identical-but-wrongly-moded file.
    source = repo / "plugins" / "sample-kit-two" / "hooks" / "scripts" / "guard.sh"
    source.chmod(0o755)
    registry = registry_for("sample-kit-two")
    apply_sync_plan(plan_plugin_sync(repo, registry, previous=None, bootstrap=True))
    dest = repo / ".claude" / "hooks" / "scripts" / "guard.sh"
    assert dest.stat().st_mode & 0o777 == 0o755

    # Simulate mode drift with content left untouched (identical bytes).
    dest.chmod(0o644)

    drift_plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=True)
    update_actions = [a for a in drift_plan.actions if a.destination == dest]
    assert len(update_actions) == 1
    assert update_actions[0].operation == "update"
    assert "executable bit" in update_actions[0].reason

    apply_sync_plan(drift_plan)
    assert dest.stat().st_mode & 0o777 == 0o755
    assert dest.read_bytes() == source.read_bytes()


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


def test_stage_generated_destinations_sets_executable_bit_via_git_index(git_repo, registry_for):
    # Regression guard (issue #413): on native Windows, `shutil.copymode`'s `os.chmod()` call
    # (exercised by apply_sync_plan, above) is a no-op for the executable bit -- Windows only
    # supports toggling the read-only DOS attribute -- and NTFS has no native execute permission
    # for Git for Windows' own new-path mode heuristic to reliably detect either. Neither the
    # filesystem write nor a bare `git add` can be trusted to record 100755 for a brand-new
    # destination there. `stage_generated_destinations` must instead force the destination's
    # git-INDEX mode directly from the source's own recorded index mode, a mechanism that's
    # honored identically on every platform.
    #
    # Verified here via `git ls-files -s` (the index), never a filesystem `stat()` -- a stat is
    # exactly the check that's unreliable on Windows, which is the whole point of this regression
    # guard; unlike the `requires_posix_permission_bits`-marked tests above, this one must run on
    # every platform, including Windows.
    plan = plan_plugin_sync(
        git_repo.root, registry_for("sample-kit-two"), previous=None, bootstrap=True
    )
    apply_sync_plan(plan)
    source = "plugins/sample-kit-two/hooks/scripts/guard.sh"
    # Real chmod (works on this POSIX test runner) keeps the working-tree file consistent with
    # the index mode forced below -- without it, `git status` reports a spurious unstaged "AM"
    # (index says 100755, working tree stat says 100644) that would make `_is_fully_staged`
    # reject the source as not fully staged. `git update-index --chmod=+x` is what actually
    # matters cross-platform: it's the same index-forcing mechanism the fix itself uses, and
    # -- unlike the chmod -- it isn't a no-op on Windows.
    (git_repo.root / source).chmod(0o755)
    subprocess.run(["git", "add", "-f", "--", source], cwd=git_repo.root, check=True)
    subprocess.run(
        ["git", "update-index", "--chmod=+x", "--", source], cwd=git_repo.root, check=True
    )
    executable = tuple(a for a in plan.actions if a.operation in ("create", "update"))

    stage_generated_destinations(git_repo.root, executable)

    result = subprocess.run(
        ["git", "ls-files", "-s", "--", ".claude/hooks/scripts/guard.sh"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.startswith("100755")


def test_stage_generated_destinations_clears_executable_bit_via_git_index(git_repo, registry_for):
    # Regression guard (cross-model-review finding on the issue #413 fix): the fix must be
    # symmetric. `stage_generated_destinations` forcing the destination's index mode to 100755
    # when the source is executable is only half the fix -- on Windows, a source that is later
    # demoted from executable to non-executable can't signal that change at the filesystem layer
    # either, so the destination's index entry must be explicitly forced back to 100644 too, not
    # just left at a stale 100755. Verified here via `git ls-files -s` (the index), the same
    # discipline as the sibling +x test above, for the same reason: a filesystem `stat()` is
    # exactly the check that's unreliable on Windows.
    plan = plan_plugin_sync(
        git_repo.root, registry_for("sample-kit-two"), previous=None, bootstrap=True
    )
    apply_sync_plan(plan)
    source = "plugins/sample-kit-two/hooks/scripts/guard.sh"
    executable = tuple(a for a in plan.actions if a.operation in ("create", "update"))

    # First, get the destination into a stale-executable state (100755), the same way the
    # sibling +x test establishes it.
    (git_repo.root / source).chmod(0o755)
    subprocess.run(["git", "add", "-f", "--", source], cwd=git_repo.root, check=True)
    subprocess.run(
        ["git", "update-index", "--chmod=+x", "--", source], cwd=git_repo.root, check=True
    )
    stage_generated_destinations(git_repo.root, executable)
    precondition = subprocess.run(
        ["git", "ls-files", "-s", "--", ".claude/hooks/scripts/guard.sh"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert precondition.stdout.startswith("100755")

    # Now demote the source back to non-executable and re-stage -- the destination's index
    # entry must follow, not stay stuck at 100755.
    (git_repo.root / source).chmod(0o644)
    subprocess.run(["git", "add", "-f", "--", source], cwd=git_repo.root, check=True)
    subprocess.run(
        ["git", "update-index", "--chmod=-x", "--", source], cwd=git_repo.root, check=True
    )

    stage_generated_destinations(git_repo.root, executable)

    result = subprocess.run(
        ["git", "ls-files", "-s", "--", ".claude/hooks/scripts/guard.sh"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.startswith("100644")


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


def test_bootstrap_does_not_flag_external_hook_scripts_mirror_as_orphan(repo, registry_for):
    # Regression test for the CodeRabbit-found gap (Fix 4): .claude/hooks/_external-scripts/
    # is plan_external_hook_scripts_mirror's own destination tree, not a hand-authored
    # plugin component -- it has no canonical source in any plugin's own hooks/
    # directory, so before this fix, bootstrap's orphan-scan flagged every file mirrored
    # there as a spurious "no canonical source found... requires manual classification"
    # warning.
    mirrored = (
        repo / ".claude" / "hooks" / "_external-scripts" / "widget-kit" / "scripts" / "widget.py"
    )
    mirrored.parent.mkdir(parents=True)
    mirrored.write_text("mirrored external hook script content", encoding="utf-8")

    plan = plan_plugin_sync(repo, registry_for("sample-kit"), previous=None, bootstrap=True)
    warnings = [a for a in plan.actions if a.operation == "warn"]
    assert not any(a.destination == mirrored.resolve() for a in warnings)


# --- plugin-root references/ assets/ (always) and scripts/ (per-plugin opt-in), issue #446 ---


def _write_file(repo, rel_path, text="x\n"):
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _registry(mirrors, scripts=()):
    from scripts.marketplace_ci.registry import Registry

    return Registry(
        version=1,
        plugin_mirrors=tuple(mirrors),
        skills=(),
        agents=(),
        scripts_mirrors=tuple(scripts),
    )


def _destinations(repo, plan, operation):
    return {
        a.destination.relative_to(repo).as_posix() for a in plan.actions if a.operation == operation
    }


def test_references_and_assets_mirror_for_every_registered_plugin(repo):
    _write_file(repo, "plugins/sample-kit/references/sk-guide.md")
    _write_file(repo, "plugins/sample-kit/assets/sk-logo.txt")
    plan = plan_plugin_sync(repo, _registry(["sample-kit"]), previous=None, bootstrap=False)
    created = _destinations(repo, plan, "create")
    assert ".claude/references/sk-guide.md" in created
    assert ".claude/assets/sk-logo.txt" in created


def test_scripts_not_mirrored_without_opt_in(repo):
    _write_file(repo, "plugins/sample-kit/scripts/sk-run.sh")
    plan = plan_plugin_sync(repo, _registry(["sample-kit"]), previous=None, bootstrap=False)
    assert ".claude/scripts/sk-run.sh" not in _destinations(repo, plan, "create")


def test_scripts_mirrored_for_opted_in_plugin_including_nested_paths(repo):
    _write_file(repo, "plugins/sample-kit/scripts/sk-run.sh")
    _write_file(repo, "plugins/sample-kit/scripts/lib/sk-util.py")
    plan = plan_plugin_sync(
        repo, _registry(["sample-kit"], ["sample-kit"]), previous=None, bootstrap=False
    )
    created = _destinations(repo, plan, "create")
    assert ".claude/scripts/sk-run.sh" in created
    assert ".claude/scripts/lib/sk-util.py" in created


def test_scripts_opt_in_is_per_plugin(repo):
    _write_file(repo, "plugins/sample-kit/scripts/sk-run.sh")
    _write_file(repo, "plugins/sample-kit-two/scripts/sk2-run.sh")
    plan = plan_plugin_sync(
        repo,
        _registry(["sample-kit", "sample-kit-two"], ["sample-kit"]),
        previous=None,
        bootstrap=False,
    )
    created = _destinations(repo, plan, "create")
    assert ".claude/scripts/sk-run.sh" in created
    assert ".claude/scripts/sk2-run.sh" not in created


def test_bytecode_caches_are_never_mirrored(repo):
    _write_file(repo, "plugins/sample-kit/scripts/sk-run.py")
    _write_file(repo, "plugins/sample-kit/scripts/__pycache__/sk-run.cpython-312.pyc")
    _write_file(repo, "plugins/sample-kit/references/__pycache__/stray.pyc")
    _write_file(repo, "plugins/sample-kit/references/sk-stray.pyc")
    plan = plan_plugin_sync(
        repo, _registry(["sample-kit"], ["sample-kit"]), previous=None, bootstrap=False
    )
    created = _destinations(repo, plan, "create")
    assert ".claude/scripts/sk-run.py" in created
    assert not any("__pycache__" in d or d.endswith(".pyc") for d in created)


def test_two_opted_in_plugins_sharing_a_script_path_collide(repo):
    _write_file(repo, "plugins/sample-kit/scripts/shared.sh")
    _write_file(repo, "plugins/sample-kit-two/scripts/shared.sh")
    plan = plan_plugin_sync(
        repo,
        _registry(["sample-kit", "sample-kit-two"], ["sample-kit", "sample-kit-two"]),
        previous=None,
        bootstrap=False,
    )
    assert ".claude/scripts/shared.sh" in _destinations(repo, plan, "collision")
    with pytest.raises(SyncError, match="collision"):
        apply_sync_plan(plan)


def test_removing_a_plugin_prunes_its_previously_mirrored_scripts(repo):
    from scripts.marketplace_ci.registry import Registry

    _write_file(repo, "plugins/sample-kit/scripts/sk-run.sh")
    previous = _registry(["sample-kit"], ["sample-kit"])
    plan = plan_plugin_sync(repo, Registry.empty(), previous=previous, bootstrap=False)
    assert ".claude/scripts/sk-run.sh" in _destinations(repo, plan, "delete")


def test_opting_out_prunes_scripts_but_keeps_other_mirrors(repo):
    _write_file(repo, "plugins/sample-kit/scripts/sk-run.sh")
    previous = _registry(["sample-kit"], ["sample-kit"])
    plan = plan_plugin_sync(repo, _registry(["sample-kit"]), previous=previous, bootstrap=False)
    deleted = _destinations(repo, plan, "delete")
    assert ".claude/scripts/sk-run.sh" in deleted
    assert not any(d.startswith(".claude/skills/") for d in deleted)


def test_bootstrap_flags_ownerless_scripts_only_when_scripts_are_mirrored(repo):
    _write_file(repo, ".claude/scripts/ownerless.sh")
    without = plan_plugin_sync(repo, _registry(["sample-kit"]), previous=None, bootstrap=True)
    assert ".claude/scripts/ownerless.sh" not in _destinations(repo, without, "warn")
    _write_file(repo, "plugins/sample-kit/scripts/sk-run.sh")
    with_scripts = plan_plugin_sync(
        repo, _registry(["sample-kit"], ["sample-kit"]), previous=None, bootstrap=True
    )
    assert ".claude/scripts/ownerless.sh" in _destinations(repo, with_scripts, "warn")


def test_bootstrap_flags_ownerless_references_and_assets(repo):
    _write_file(repo, ".claude/references/ownerless.md")
    _write_file(repo, ".claude/assets/ownerless.png")
    plan = plan_plugin_sync(repo, _registry(["sample-kit"]), previous=None, bootstrap=True)
    warned = _destinations(repo, plan, "warn")
    assert ".claude/references/ownerless.md" in warned
    assert ".claude/assets/ownerless.png" in warned


@requires_posix_permission_bits
def test_mirrored_script_keeps_its_executable_bit(repo):
    source = _write_file(repo, "plugins/sample-kit/scripts/sk-run.sh", "#!/bin/sh\n")
    source.chmod(0o755)
    plan = plan_plugin_sync(
        repo, _registry(["sample-kit"], ["sample-kit"]), previous=None, bootstrap=False
    )
    apply_sync_plan(plan)
    assert (repo / ".claude" / "scripts" / "sk-run.sh").stat().st_mode & 0o111


# --- a destination still owned by a registered plugin is never scheduled for deletion ---
# (PR #455 review: Codex P2 and CodeRabbit Major on the delete plan)


def test_opting_out_keeps_a_script_another_plugin_still_owns(repo):
    _write_file(repo, "plugins/sample-kit/scripts/shared.sh", "from sample-kit\n")
    _write_file(repo, "plugins/sample-kit-two/scripts/shared.sh", "from sample-kit-two\n")
    _write_file(repo, ".claude/scripts/shared.sh", "from sample-kit-two\n")
    mirrors = ["sample-kit", "sample-kit-two"]
    previous = _registry(mirrors, mirrors)
    current = _registry(mirrors, ["sample-kit-two"])

    plan = plan_plugin_sync(repo, current, previous=previous, bootstrap=False)

    assert ".claude/scripts/shared.sh" not in _destinations(repo, plan, "delete")
    apply_sync_plan(plan)
    assert (repo / ".claude/scripts/shared.sh").read_text(
        encoding="utf-8"
    ) == "from sample-kit-two\n"


def test_script_ownership_transfer_ends_with_the_new_owners_mirror(repo):
    _write_file(repo, "plugins/sample-kit/scripts/shared.sh", "from sample-kit\n")
    _write_file(repo, "plugins/sample-kit-two/scripts/shared.sh", "from sample-kit-two\n")
    _write_file(repo, ".claude/scripts/shared.sh", "from sample-kit\n")
    mirrors = ["sample-kit", "sample-kit-two"]
    previous = _registry(mirrors, ["sample-kit"])
    current = _registry(mirrors, ["sample-kit-two"])

    plan = plan_plugin_sync(repo, current, previous=previous, bootstrap=False)

    assert ".claude/scripts/shared.sh" in _destinations(repo, plan, "update")
    assert ".claude/scripts/shared.sh" not in _destinations(repo, plan, "delete")
    apply_sync_plan(plan)
    assert (repo / ".claude/scripts/shared.sh").read_text(
        encoding="utf-8"
    ) == "from sample-kit-two\n"


def test_removing_a_plugin_keeps_a_script_another_plugin_still_owns(repo):
    _write_file(repo, "plugins/sample-kit/scripts/shared.sh", "from sample-kit\n")
    _write_file(repo, "plugins/sample-kit-two/scripts/shared.sh", "from sample-kit-two\n")
    _write_file(repo, ".claude/scripts/shared.sh", "from sample-kit-two\n")
    previous = _registry(["sample-kit", "sample-kit-two"], ["sample-kit", "sample-kit-two"])
    current = _registry(["sample-kit-two"], ["sample-kit-two"])

    plan = plan_plugin_sync(repo, current, previous=previous, bootstrap=False)

    assert ".claude/scripts/shared.sh" not in _destinations(repo, plan, "delete")
    apply_sync_plan(plan)
    assert (repo / ".claude/scripts/shared.sh").exists()
