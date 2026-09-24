"""Tests for scripts.marketplace_ci.prefix_check -- plugin-rulebook's R33
component-file-prefix rule's mechanical enforcement counterpart."""

import json
from pathlib import Path

import pytest

from scripts.marketplace_ci.prefix_check import (
    find_prefix_permanence_violations,
    find_prefix_violations,
)

# Creating a symlink without elevation is denied on some Windows configs
# (requires Developer Mode or an elevated shell) -- skip rather than fail
# the whole suite on a machine where symlink creation itself isn't possible.
_SYMLINK_UNAVAILABLE = False
try:
    import tempfile

    with tempfile.TemporaryDirectory() as _probe_dir:
        _probe_target = Path(_probe_dir) / "t"
        _probe_target.mkdir()
        (Path(_probe_dir) / "l").symlink_to(_probe_target, target_is_directory=True)
except OSError:
    _SYMLINK_UNAVAILABLE = True

requires_symlinks = pytest.mark.skipif(
    _SYMLINK_UNAVAILABLE, reason="symlink creation not permitted on this machine/user"
)


def _write_inventory(repo: Path, plugins: list[dict]) -> Path:
    path = repo / ".claude-plugin" / "marketplace-inventory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "marketplace_name": "fixture",
                "updated_on": "2026-01-01",
                "plugins": plugins,
            }
        ),
        encoding="utf-8",
    )
    return path


def _plugin(name, source, prefix=None, status="active"):
    entry = {"id": f"plugin_{name}", "name": name, "source": source, "status": status}
    if prefix is not None:
        entry["prefix"] = prefix
    return entry


def test_no_inventory_file_is_inert(tmp_path):
    assert find_prefix_violations(tmp_path) == []


def test_unregistered_plugin_no_findings(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "check-pr-title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit")])  # no prefix yet
    assert find_prefix_violations(tmp_path) == []


def test_registered_plugin_conformant_tree_passes(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check-pr-title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


def test_registered_plugin_one_bad_file_fails(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "check-pr-title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert violations[0].path.name == "check-pr-title.py"


def test_nested_file_checked_recursively(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "hooks" / "scripts").mkdir(parents=True)
    (plugin_dir / "hooks" / "scripts" / "guard-raw-commit.sh").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].path.name == "guard-raw-commit.sh"


def test_hooks_json_always_exempt(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "hooks").mkdir(parents=True)
    (plugin_dir / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


def test_antigravity_bin_and_docs_checked_only_for_that_plugin(tmp_path):
    plugin_dir = tmp_path / "antigravity-kit"
    (plugin_dir / "bin").mkdir(parents=True)
    (plugin_dir / "bin" / "doctor.sh").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("antigravity-kit", "./antigravity-kit", prefix="agy")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].path.name == "doctor.sh"


def test_bin_ignored_for_non_antigravity_plugin(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "bin").mkdir(parents=True)
    (plugin_dir / "bin" / "not-prefixed.sh").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


def test_retired_plugin_skipped_even_with_prefix(tmp_path):
    plugin_dir = tmp_path / "old-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "not-prefixed.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("old-kit", "./old-kit", prefix="old", status="retired")])
    assert find_prefix_violations(tmp_path) == []


def test_superseded_plugin_skipped_even_with_prefix(tmp_path):
    plugin_dir = tmp_path / "old-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "not-prefixed.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("old-kit", "./old-kit", prefix="old", status="superseded")])
    assert find_prefix_violations(tmp_path) == []


def test_relative_traversal_source_reported_not_scanned(tmp_path):
    # A '../'-style source escaping the repo root must never be walked --
    # found by cross-model-review (Codex + Claude, both independently):
    # repo / source was resolved with no containment check.
    outside_dir = tmp_path.parent / f"{tmp_path.name}-outside"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("evil-kit", f"../{outside_dir.name}", prefix="evi")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "evil-kit"
    assert "outside the repository root" in violations[0].reason


def test_absolute_source_outside_repo_reported_not_scanned(tmp_path):
    outside_dir = tmp_path.parent / f"{tmp_path.name}-abs-outside"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("evil-kit", str(outside_dir), prefix="evi")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "evil-kit"
    assert "outside the repository root" in violations[0].reason


def test_source_resolving_to_repo_root_rejected(tmp_path):
    # source: '.' (or anything resolving to the repo root itself) must be
    # rejected, not scanned -- it would otherwise flood violations from the
    # repo root's own scripts/hooks/etc, none of which belong to any plugin.
    _write_inventory(tmp_path, [_plugin("root-kit", ".", prefix="roo")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "root-kit"
    assert "repository root itself" in violations[0].reason


@requires_symlinks
def test_symlinked_scope_dir_not_walked(tmp_path):
    # Found by a live security-reviewer pass: the containment check on
    # plugin_dir doesn't protect a *scope directory* (scripts/references/
    # etc) that is itself a symlink pointing outside the repo -- a plugin
    # tree is ordinary contributor-controlled content, so a committed
    # symlink is a realistic input, not hypothetical.
    outside_dir = tmp_path.parent / f"{tmp_path.name}-symlink-target"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("", encoding="utf-8")

    plugin_dir = tmp_path / "git-kit"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "scripts").symlink_to(outside_dir, target_is_directory=True)
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])

    assert find_prefix_violations(tmp_path) == []


@requires_symlinks
def test_symlinked_file_inside_scope_dir_skipped(tmp_path):
    outside_dir = tmp_path.parent / f"{tmp_path.name}-file-target"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("", encoding="utf-8")

    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "linked.py").symlink_to(outside_file)
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])

    assert find_prefix_violations(tmp_path) == []


def test_source_inside_repo_via_traversal_still_scanned_normally(tmp_path):
    # A source that resolves back inside the repo despite using '../'
    # segments (e.g. './a/../b') must not be falsely rejected -- only a
    # source that actually escapes the repo root is a violation.
    plugin_dir = tmp_path / "nested" / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./nested/../nested/git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


# --- find_prefix_permanence_violations (pure-function unit tests; the CLI
# integration tests for `check-prefix-permanence` live in test_cli.py) ---


def test_permanence_unchanged_prefix_no_violation():
    base = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    head = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    assert find_prefix_permanence_violations(base, head) == []


def test_permanence_no_prefix_at_base_no_violation():
    base = {"plugins": [{"id": "p1", "name": "a"}]}
    head = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    assert find_prefix_permanence_violations(base, head) == []


def test_permanence_reassigned_prefix_is_violation():
    base = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    head = {"plugins": [{"id": "p1", "name": "a", "prefix": "xyz"}]}
    violations = find_prefix_permanence_violations(base, head)
    assert len(violations) == 1
    assert violations[0].plugin_id == "p1"
    assert "abc" in violations[0].reason and "xyz" in violations[0].reason


def test_permanence_dropped_prefix_is_violation():
    base = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    head = {"plugins": [{"id": "p1", "name": "a"}]}
    violations = find_prefix_permanence_violations(base, head)
    assert len(violations) == 1
    assert violations[0].plugin_id == "p1"


def test_permanence_record_removed_is_violation():
    base = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    head = {"plugins": []}
    violations = find_prefix_permanence_violations(base, head)
    assert len(violations) == 1
    assert "no longer exists" in violations[0].reason
