import json
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci.git_state import ChangedPath
from scripts.marketplace_ci.validators import (
    Finding,
    PluginValidatorEntry,
    ValidatorCatalog,
    load_catalog,
    run_catalog,
    run_delta_structural_checks,
)


@pytest.fixture
def catalog() -> ValidatorCatalog:
    return ValidatorCatalog(
        plugin_validators=(
            PluginValidatorEntry(
                id="sample-kit.validate",
                plugin="sample-kit",
                path=Path("plugins/sample-kit/scripts/validate.py"),
                interpreter="python",
                platforms=("linux", "macos", "windows"),
            ),
            PluginValidatorEntry(
                id="sample-kit.bash-check",
                plugin="sample-kit",
                path=Path("plugins/sample-kit/scripts/check.sh"),
                interpreter="bash",
                platforms=("linux", "macos"),
            ),
        )
    )


def test_plugin_validator_runs_as_subprocess_not_import(monkeypatch, catalog, completed):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: calls.append(argv) or completed(0))
    run_catalog(catalog, platform="linux")
    assert ["python", "plugins/sample-kit/scripts/validate.py"] in calls
    assert ["bash", "plugins/sample-kit/scripts/check.sh"] in calls


def test_windows_skips_bash_only_black_box_with_explicit_result(monkeypatch, catalog, completed):
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: completed(0))
    results = run_catalog(catalog, platform="windows")
    by_id = {r.id: r for r in results}
    assert by_id["sample-kit.bash-check"].status == "skipped"
    assert by_id["sample-kit.bash-check"].reason == "Bash prerequisite unavailable on Windows"
    assert by_id["sample-kit.validate"].status == "passed"


def test_run_catalog_reports_nonzero_exit_as_failed(monkeypatch, catalog, completed):
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: completed(1))
    results = run_catalog(catalog, platform="linux")
    assert all(r.status == "failed" for r in results)


def test_run_catalog_skips_out_of_scope_entries(monkeypatch, completed):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: calls.append(argv) or completed(0))
    catalog = ValidatorCatalog(
        plugin_validators=(
            PluginValidatorEntry(
                id="example.teaching-script",
                plugin="sample-kit",
                path=Path("plugins/sample-kit/examples/demo.sh"),
                interpreter="bash",
                platforms=("linux", "macos"),
                kind="out-of-scope",
            ),
        )
    )
    results = run_catalog(catalog, platform="linux")
    assert results == ()
    assert calls == []


def test_load_catalog_reads_real_marketplace_validators_json():
    path = Path(__file__).parents[2] / ".github" / "marketplace-validators.json"
    catalog = load_catalog(path)
    assert len(catalog.repository_validators) >= 1
    assert len(catalog.plugin_validators) >= 1
    ids = {e.id for e in catalog.plugin_validators}
    assert len(ids) == len(catalog.plugin_validators)  # no duplicate ids


def test_run_delta_structural_checks_scopes_to_changed_component(repo, change):
    registry_path = repo / ".claude" / "marketplace-sync.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps({"version": 1, "plugin_mirrors": ["sample-kit"], "codex_exports": {}}),
        encoding="utf-8",
    )

    findings = run_delta_structural_checks(
        repo, (change("plugins/sample-kit/skills/demo/SKILL.md"),)
    )
    assert all(f.path.startswith("plugins/sample-kit/skills/demo") for f in findings)
    assert isinstance(findings, tuple)
    assert all(isinstance(f, Finding) for f in findings)
    # this changed component actually has un-synced content, so it must produce
    # at least one real, correctly-scoped finding, not just satisfy the check vacuously
    assert len(findings) >= 1


def test_run_delta_structural_checks_ignores_unrelated_changes(repo, change):
    registry_path = repo / ".claude" / "marketplace-sync.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps({"version": 1, "plugin_mirrors": ["sample-kit"], "codex_exports": {}}),
        encoding="utf-8",
    )

    findings = run_delta_structural_checks(repo, (change("some/unrelated/file.md"),))
    assert findings == ()


def test_run_delta_structural_checks_returns_empty_without_registry(repo, change):
    findings = run_delta_structural_checks(
        repo, (change("plugins/sample-kit/skills/demo/SKILL.md"),)
    )
    assert findings == ()


def test_run_delta_structural_checks_checks_rename_source_component_too(repo):
    """PR #50 external-review regression: a rename away from a component
    (e.g. onto an inert plugin-root basename) must still check that
    component's own key for stale mirror/export actions -- keying only off
    new_path would silently drop the source component's parity check."""
    registry_path = repo / ".claude" / "marketplace-sync.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps({"version": 1, "plugin_mirrors": ["sample-kit"], "codex_exports": {}}),
        encoding="utf-8",
    )

    rename = ChangedPath(
        status="R",
        old_path="plugins/sample-kit/skills/demo/SKILL.md",
        new_path="plugins/sample-kit/LICENSE",
    )
    findings = run_delta_structural_checks(repo, (rename,))
    assert any(f.path.startswith("plugins/sample-kit/skills/demo") for f in findings)
