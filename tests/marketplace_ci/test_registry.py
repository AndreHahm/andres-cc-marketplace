import json

import pytest

from scripts.marketplace_ci.registry import Registry, RegistryError, RemovalSet


def test_registry_rejects_globs(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        '{"version":1,"plugin_mirrors":["*-kit"],"codex_exports":{"skills":[],"agents":[]}}',
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="exact plugin name"):
        Registry.load(path)


def test_removed_since_preserves_prior_ownership():
    old = Registry(version=1, plugin_mirrors=("git-kit",), skills=("commit",), agents=("reviewer",))
    new = Registry(version=1, plugin_mirrors=(), skills=(), agents=())
    assert new.removed_since(old) == RemovalSet(("git-kit",), ("commit",), ("reviewer",))


def test_registry_rejects_absolute_path(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps({"version": 1, "plugin_mirrors": ["/etc/passwd"], "codex_exports": {}}),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="exact plugin name"):
        Registry.load(path)


def test_registry_rejects_traversal(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps({"version": 1, "plugin_mirrors": ["../outside"], "codex_exports": {}}),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="exact plugin name"):
        Registry.load(path)


def test_registry_rejects_slashes_in_component_name(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps(
            {"version": 1, "plugin_mirrors": [], "codex_exports": {"skills": ["a/b"], "agents": []}}
        ),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="exact plugin name"):
        Registry.load(path)


def test_registry_rejects_duplicate_names(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps({"version": 1, "plugin_mirrors": ["git-kit", "git-kit"], "codex_exports": {}}),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="duplicate"):
        Registry.load(path)


def test_registry_rejects_unknown_top_level_key(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps({"version": 1, "plugin_mirrors": [], "codex_exports": {}, "extra": True}),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="unknown top-level key"):
        Registry.load(path)


def test_registry_rejects_unknown_codex_exports_key(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "plugin_mirrors": [],
                "codex_exports": {"skills": [], "agents": [], "extra": []},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="unknown codex_exports key"):
        Registry.load(path)


def test_registry_rejects_unsupported_version(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps({"version": 2, "plugin_mirrors": [], "codex_exports": {}}),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="unsupported version"):
        Registry.load(path)


def test_registry_loads_valid_document(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "plugin_mirrors": ["git-kit", "codex-kit"],
                "codex_exports": {
                    "skills": ["plugin-marketplace-review"],
                    "agents": ["security-reviewer"],
                },
            }
        ),
        encoding="utf-8",
    )
    registry = Registry.load(path)
    assert registry.plugin_mirrors == ("git-kit", "codex-kit")
    assert registry.skills == ("plugin-marketplace-review",)
    assert registry.agents == ("security-reviewer",)


def test_empty_registry_has_no_members():
    registry = Registry.empty()
    assert registry.plugin_mirrors == ()
    assert registry.skills == ()
    assert registry.agents == ()
