"""Tests for scripts.marketplace_ci.prefix_check -- plugin-rulebook's R33
component-file-prefix rule's mechanical enforcement counterpart."""

import json
from pathlib import Path

from scripts.marketplace_ci.prefix_check import find_prefix_violations


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
