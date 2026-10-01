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
    assert registry.divergence_exceptions == ()


def test_registry_loads_divergence_exceptions(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "plugin_mirrors": [],
                "codex_exports": {},
                "divergence_exceptions": [
                    {
                        "source": "plugins/x/skills/y/SKILL.md",
                        "dest": ".claude/skills/y/SKILL.md",
                        "reason": "documented reason",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    registry = Registry.load(path)
    assert len(registry.divergence_exceptions) == 1
    exc = registry.divergence_exceptions[0]
    assert exc.source == "plugins/x/skills/y/SKILL.md"
    assert exc.dest == ".claude/skills/y/SKILL.md"
    assert exc.reason == "documented reason"


def test_registry_rejects_divergence_exception_missing_reason(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "plugin_mirrors": [],
                "codex_exports": {},
                "divergence_exceptions": [
                    {"source": "a", "dest": "b"},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="missing key"):
        Registry.load(path)


def test_registry_rejects_divergence_exception_empty_reason(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "plugin_mirrors": [],
                "codex_exports": {},
                "divergence_exceptions": [
                    {"source": "a", "dest": "b", "reason": "   "},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="non-empty string"):
        Registry.load(path)


def test_registry_rejects_divergence_exception_unknown_key(tmp_path):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "plugin_mirrors": [],
                "codex_exports": {},
                "divergence_exceptions": [
                    {"source": "a", "dest": "b", "reason": "r", "extra": "nope"},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="unknown divergence_exceptions key"):
        Registry.load(path)


def _write_registry(tmp_path, **fields):
    path = tmp_path / "marketplace-sync.json"
    path.write_text(
        json.dumps({"version": 1, "codex_exports": {}, **fields}),
        encoding="utf-8",
    )
    return path


def test_registry_loads_scripts_mirrors(tmp_path):
    path = _write_registry(
        tmp_path, plugin_mirrors=["git-kit", "analysis-kit"], scripts_mirrors=["git-kit"]
    )
    assert Registry.load(path).scripts_mirrors == ("git-kit",)


def test_scripts_mirrors_defaults_to_empty(tmp_path):
    path = _write_registry(tmp_path, plugin_mirrors=["git-kit"])
    assert Registry.load(path).scripts_mirrors == ()
    assert Registry.empty().scripts_mirrors == ()


def test_registry_rejects_scripts_mirror_that_is_not_a_plugin_mirror(tmp_path):
    path = _write_registry(tmp_path, plugin_mirrors=["git-kit"], scripts_mirrors=["analysis-kit"])
    with pytest.raises(RegistryError, match="plugin_mirrors"):
        Registry.load(path)


def test_registry_rejects_duplicate_scripts_mirrors(tmp_path):
    path = _write_registry(
        tmp_path, plugin_mirrors=["git-kit"], scripts_mirrors=["git-kit", "git-kit"]
    )
    with pytest.raises(RegistryError, match="duplicate"):
        Registry.load(path)


def test_registry_rejects_traversal_in_scripts_mirrors(tmp_path):
    path = _write_registry(tmp_path, plugin_mirrors=["git-kit"], scripts_mirrors=["../git-kit"])
    with pytest.raises(RegistryError, match="exact plugin name"):
        Registry.load(path)


def test_registry_rejects_non_list_scripts_mirrors(tmp_path):
    path = _write_registry(tmp_path, plugin_mirrors=["git-kit"], scripts_mirrors="git-kit")
    with pytest.raises(RegistryError, match="scripts_mirrors must be a list"):
        Registry.load(path)


def test_removed_since_reports_scripts_mirror_opt_out():
    old = Registry(
        version=1,
        plugin_mirrors=("git-kit",),
        skills=(),
        agents=(),
        scripts_mirrors=("git-kit",),
    )
    new = Registry(version=1, plugin_mirrors=("git-kit",), skills=(), agents=())
    assert new.removed_since(old).scripts_mirrors == ("git-kit",)
