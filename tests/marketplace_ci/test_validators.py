import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci.validators import (
    PluginValidatorEntry,
    ValidatorCatalog,
    load_catalog,
    run_catalog,
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
