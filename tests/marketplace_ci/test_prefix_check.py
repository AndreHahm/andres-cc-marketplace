"""Tests for scripts.marketplace_ci.prefix_check -- plugin-rulebook's R33
component-file-prefix rule's mechanical enforcement counterpart."""

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.marketplace_ci.prefix_check import (
    CHECKED_STATUSES,
    DOMAIN_PREFIX_PATTERN,
    PREFIX_PATTERN,
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


def _write_inventory(repo: Path, plugins: list[dict], write_manifest: bool = True) -> Path:
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
    if write_manifest:
        # Every existing test's inventory `source` must match an
        # authoritative marketplace.json entry (find_prefix_violations now
        # cross-checks the two) -- derive one automatically from the same
        # plugins list so tests that aren't specifically about the
        # authoritative-source check don't each need to write their own.
        # Only a genuinely-live (active/deprecated) plugin is listed here --
        # matching real repo state, where a retired/superseded/planned
        # plugin is removed from (or not yet added to) marketplace.json. A
        # test that needs to model a *mismatched* status/manifest state
        # (a curated `status` saying retired while the manifest still lists
        # the plugin) writes its own manifest explicitly instead of relying
        # on this default.
        _write_marketplace_manifest(
            repo,
            [
                {"name": p["name"], "source": p["source"]}
                for p in plugins
                if p.get("source") and p.get("status", "active") in CHECKED_STATUSES
            ],
        )
    return path


def _write_marketplace_manifest(repo: Path, plugins: list[dict]) -> Path:
    path = repo / ".claude-plugin" / "marketplace.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"name": "fixture", "plugins": plugins}),
        encoding="utf-8",
    )
    return path


def _plugin(name, source, prefix=None, domain_prefix=None, status="active"):
    # `prefix` became a required key in #433, so a record always carries it --
    # `None` here is the explicit-null opt-out, not an absent key.
    entry = {
        "id": f"plugin_{name}",
        "name": name,
        "source": source,
        "status": status,
        "prefix": prefix,
    }
    if domain_prefix is not None:
        entry["domain_prefix"] = domain_prefix
    return entry


def test_no_inventory_file_is_inert(tmp_path):
    assert find_prefix_violations(tmp_path) == []


def test_explicit_null_prefix_is_inert(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "check-pr-title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit")])
    assert find_prefix_violations(tmp_path) == []


def test_absent_prefix_key_is_flagged(tmp_path):
    entry = _plugin("git-kit", "./git-kit")
    del entry["prefix"]  # key omitted entirely, unlike an explicit null
    path = _write_inventory(tmp_path, [entry])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert violations[0].path == path
    assert "required `prefix` key" in violations[0].reason


def test_absent_prefix_key_flagged_even_with_domain_prefix_registered(tmp_path):
    # A registered domain_prefix makes the plugin scannable, but the missing
    # required key is still its own defect.
    plugin_dir = tmp_path / "context-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "context-audit.py").write_text("", encoding="utf-8")
    entry = _plugin("context-kit", "./context-kit", domain_prefix="context")
    del entry["prefix"]
    _write_inventory(tmp_path, [entry])
    violations = find_prefix_violations(tmp_path)
    assert [v.reason for v in violations if "required `prefix` key" in v.reason] != []
    assert len(violations) == 1


def test_non_object_plugin_entry_reported_not_crashed(tmp_path):
    path = _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit")])
    data = json.loads(path.read_text(encoding="utf-8"))
    data["plugins"].append("not-an-object")
    path.write_text(json.dumps(data), encoding="utf-8")
    violations = find_prefix_violations(tmp_path)
    assert [v.reason for v in violations] == ["record is not a JSON object"]
    assert violations[0].plugin == "plugins[1]"


def test_non_list_plugins_value_reported_not_crashed(tmp_path):
    path = _write_inventory(tmp_path, [])
    path.write_text(json.dumps({"plugins": {"git-kit": {}}}), encoding="utf-8")
    violations = find_prefix_violations(tmp_path)
    assert [v.reason for v in violations] == ["`plugins` is not a JSON array"]


def test_non_object_top_level_reported_not_crashed(tmp_path):
    path = _write_inventory(tmp_path, [])
    path.write_text("[]", encoding="utf-8")
    violations = find_prefix_violations(tmp_path)
    assert [v.reason for v in violations] == [
        "marketplace-inventory.json's top level is not a JSON object"
    ]


def test_absent_prefix_key_flagged_regardless_of_status(tmp_path):
    entry = _plugin("old-kit", "./old-kit", status="retired")
    del entry["prefix"]
    _write_inventory(tmp_path, [entry])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "required `prefix` key" in violations[0].reason


def test_registered_plugin_conformant_tree_passes(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git_check_pr_title.py").write_text("", encoding="utf-8")
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


def test_python_package_init_exempt_but_sibling_modules_checked(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts" / "shared").mkdir(parents=True)
    (plugin_dir / "scripts" / "shared" / "__init__.py").write_text("", encoding="utf-8")
    (plugin_dir / "scripts" / "shared" / "git_models.py").write_text("", encoding="utf-8")
    (plugin_dir / "scripts" / "shared" / "models.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert [v.path.name for v in violations] == ["models.py"]


def test_init_outside_scripts_dir_not_exempt(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    for dirname in ("commands", "hooks"):
        (plugin_dir / dirname).mkdir(parents=True)
        (plugin_dir / dirname / "__init__.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert sorted(v.path.parent.name for v in violations) == ["commands", "hooks"]


def test_init_lookalike_basename_not_exempt(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "__init__.txt").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert [v.path.name for v in violations] == ["__init__.txt"]


@requires_symlinks
def test_symlinked_hooks_json_not_exempt(tmp_path):
    # Codex P1 finding (PR #387 round 2): the hooks.json manifest exemption
    # matched on path equality before the symlink check ran, so a
    # symlinked hooks/hooks.json skipped the symlink rejection and evaded
    # the prefix scan via its real target. The symlink check must run
    # first.
    outside_dir = tmp_path.parent / f"{tmp_path.name}-hooks-target"
    outside_dir.mkdir()
    (outside_dir / "real.json").write_text("{}", encoding="utf-8")

    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "hooks").mkdir(parents=True)
    (plugin_dir / "hooks" / "hooks.json").symlink_to(outside_dir / "real.json")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])

    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].path.name == "hooks.json"
    assert "symlink" in violations[0].reason


def test_duplicate_active_records_same_name_rejected_not_scanned(tmp_path):
    # CodeRabbit Major finding (PR #387 round 2): two active/deprecated
    # inventory records sharing the same `name` each carry their own
    # permanent prefix -- scanning the one real, manifest-registered
    # directory against both would require every file to satisfy two
    # different prefixes at once. Refuse to guess which record's prefix
    # governs the directory instead of silently scanning under one of
    # them, or scanning it twice.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check.py").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path,
        [
            {
                "id": "plugin_git-kit-1",
                "name": "git-kit",
                "source": "./git-kit",
                "status": "active",
                "prefix": "git",
            },
            {
                "id": "plugin_git-kit-2",
                "name": "git-kit",
                "source": "./git-kit",
                "status": "deprecated",
                "prefix": "old",
            },
        ],
        write_manifest=False,
    )
    _write_marketplace_manifest(tmp_path, [{"name": "git-kit", "source": "./git-kit"}])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "2 active/deprecated" in violations[0].reason
    assert "git-kit" in violations[0].reason


def test_active_record_prefix_wins_over_retired_same_name(tmp_path):
    # A retired copy and its active successor can legitimately share a
    # `name` in marketplace-inventory.json -- the single active/deprecated
    # record must win; the retired record's own prefix is never applied to
    # the manifest-registered directory.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "old-check.sh").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path,
        [
            {
                "id": "plugin_git-kit-old",
                "name": "git-kit",
                "source": "./git-kit",
                "status": "retired",
                "prefix": "old",
            },
            {
                "id": "plugin_git-kit-new",
                "name": "git-kit",
                "source": "./git-kit",
                "status": "active",
                "prefix": "git",
            },
        ],
        write_manifest=False,
    )
    _write_marketplace_manifest(tmp_path, [{"name": "git-kit", "source": "./git-kit"}])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "'git-'" in violations[0].reason


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


def test_status_retired_but_still_manifest_listed_is_still_checked(tmp_path):
    # Codex P1 finding: `status` is a curated, separately human-editable
    # field, just like `source` (see the null-source regression above) --
    # a PR could set status to 'retired'/'planned' while marketplace.json
    # still lists the plugin as installed, exempting a still-live plugin
    # from the entire check. A plugin present in the authoritative manifest
    # must be checked regardless of its curated status.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "not-prefixed.py").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path,
        [_plugin("git-kit", "./git-kit", prefix="git", status="retired")],
        write_manifest=False,
    )
    # Unlike the default helper above, explicitly list this plugin in
    # marketplace.json despite its curated 'retired' status -- modeling the
    # exact mismatch this check must catch.
    _write_marketplace_manifest(tmp_path, [{"name": "git-kit", "source": "./git-kit"}])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].path.name == "not-prefixed.py"


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
def test_symlinked_scope_dir_flagged_not_silently_skipped(tmp_path):
    # Found by a live security-reviewer pass: the containment check on
    # plugin_dir doesn't protect a *scope directory* (scripts/references/
    # etc) that is itself a symlink pointing outside the repo -- a plugin
    # tree is ordinary contributor-controlled content, so a committed
    # symlink is a realistic input, not hypothetical. A later cross-model-
    # review round (7) found the original fix merely stopped the walk from
    # crossing the symlink -- it never flagged the symlink itself, so the
    # whole directory's worth of unprefixed content silently vanished from
    # the scan instead of failing CI loudly.
    outside_dir = tmp_path.parent / f"{tmp_path.name}-symlink-target"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("", encoding="utf-8")

    plugin_dir = tmp_path / "git-kit"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "scripts").symlink_to(outside_dir, target_is_directory=True)
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])

    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].path == plugin_dir / "scripts"
    assert "symlink" in violations[0].reason


@requires_symlinks
def test_symlinked_file_inside_scope_dir_flagged_not_silently_skipped(tmp_path):
    # Round-7 cross-model-review companion to the scope-dir case above: a
    # symlink nested *inside* an otherwise-real scope directory must also
    # be flagged, not silently dropped from the scan -- its own basename
    # and its target both evade the ordinary prefix check.
    outside_dir = tmp_path.parent / f"{tmp_path.name}-file-target"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("", encoding="utf-8")

    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    linked = plugin_dir / "scripts" / "linked.py"
    linked.symlink_to(outside_file)
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])

    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].path == linked
    assert "symlink" in violations[0].reason


def test_source_inside_repo_via_traversal_still_scanned_normally(tmp_path):
    # A source that resolves back inside the repo despite using '../'
    # segments (e.g. './a/../b') must not be falsely rejected -- only a
    # source that actually escapes the repo root is a violation.
    plugin_dir = tmp_path / "nested" / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git_check.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./nested/../nested/git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


# --- find_prefix_permanence_violations (pure-function unit tests; the CLI
# integration tests for `check-prefix-permanence` live in test_cli.py) ---


def test_permanence_unchanged_prefix_no_violation():
    base = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    head = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    assert find_prefix_permanence_violations(base, head) == []


def test_permanence_head_omitting_prefix_key_is_violation():
    base = {"plugins": [_plugin("git-kit", "./git-kit", prefix="git")]}
    head_entry = _plugin("git-kit", "./git-kit")
    del head_entry["prefix"]  # omitted, not nulled
    violations = find_prefix_permanence_violations(base, {"plugins": [head_entry]})
    assert len(violations) == 1
    assert "prefix changed from 'git' (base) to None (head)" in violations[0].reason


def test_permanence_head_record_missing_id_reported_as_removed_not_crashed():
    base = {"plugins": [_plugin("git-kit", "./git-kit", prefix="git")]}
    head_entry = _plugin("git-kit", "./git-kit", prefix="git")
    del head_entry["id"]
    violations = find_prefix_permanence_violations(base, {"plugins": [head_entry]})
    assert len(violations) == 1
    assert "no longer exists at head" in violations[0].reason


def test_permanence_malformed_records_do_not_crash():
    # Nothing registered at base (a non-object entry, an id-less record with
    # no prefix), so there is nothing to protect and no violation either way.
    base = {"plugins": ["junk", {"name": "no-id"}]}
    head = {"plugins": [{"id": "plugin_a", "name": "a"}]}
    assert find_prefix_permanence_violations(base, head) == []


_MALFORMED_INVENTORIES: list[Any] = [[], "x", {"plugins": {"a": 1}}, {"plugins": "x"}, {}]


@pytest.mark.parametrize("malformed", _MALFORMED_INVENTORIES)
def test_permanence_malformed_base_fails_closed(malformed):
    # A structurally malformed base used to be read as an empty inventory,
    # so every registered prefix silently lost its protection.
    head = {"plugins": [_plugin("git-kit", "./git-kit", prefix="git")]}
    violations = find_prefix_permanence_violations(malformed, head)
    assert len(violations) == 1
    assert violations[0].reason.startswith("base inventory ")
    assert "cannot be checked" in violations[0].reason


@pytest.mark.parametrize("malformed", _MALFORMED_INVENTORIES)
def test_permanence_malformed_head_fails_closed(malformed):
    base = {"plugins": [_plugin("git-kit", "./git-kit", prefix="git")]}
    violations = find_prefix_permanence_violations(base, malformed)
    assert len(violations) == 1
    assert violations[0].reason.startswith("head inventory ")
    assert "cannot be checked" in violations[0].reason


@pytest.mark.parametrize("bad_id", [None, "", "   ", 123])
def test_permanence_base_prefixed_record_without_joinable_id_is_violation(bad_id):
    # Skipping it would leave the prefix with no permanence protection at all.
    entry = _plugin("foo-kit", "./foo-kit", prefix="foo")
    if bad_id is None:
        del entry["id"]
    else:
        entry["id"] = bad_id
    violations = find_prefix_permanence_violations({"plugins": [entry]}, {"plugins": [entry]})
    assert len(violations) == 1
    assert violations[0].plugin_name == "foo-kit"
    assert "no non-empty string `id`" in violations[0].reason


def test_permanence_base_record_repaired_by_adding_id_is_not_blocked():
    # The PR that adds the missing id must not be rejected by the violation
    # it fixes.
    broken = _plugin("foo-kit", "./foo-kit", prefix="foo")
    del broken["id"]
    repaired = _plugin("foo-kit", "./foo-kit", prefix="foo")
    assert find_prefix_permanence_violations({"plugins": [broken]}, {"plugins": [repaired]}) == []


@pytest.mark.parametrize("field, value", [("prefix", "bar"), ("domain_prefix", "foobar")])
def test_permanence_id_repair_that_also_changes_a_prefix_field_still_violates(field, value):
    broken = _plugin("foo-kit", "./foo-kit", prefix="foo")
    del broken["id"]
    repaired = _plugin("foo-kit", "./foo-kit", prefix="foo")
    repaired[field] = value
    violations = find_prefix_permanence_violations({"plugins": [broken]}, {"plugins": [repaired]})
    assert any("no non-empty string `id`" in v.reason for v in violations)


def test_missing_plugins_key_flagged(tmp_path):
    path = _write_inventory(tmp_path, [])
    path.write_text(json.dumps({"schema_version": "1.0.0"}), encoding="utf-8")
    violations = find_prefix_violations(tmp_path)
    assert [v.reason for v in violations] == ["`plugins` key is missing"]


def test_permanence_whitespace_only_head_id_does_not_count_as_a_repair():
    broken = _plugin("foo-kit", "./foo-kit", prefix="foo")
    del broken["id"]
    blank = _plugin("foo-kit", "./foo-kit", prefix="foo")
    blank["id"] = "   "
    violations = find_prefix_permanence_violations({"plugins": [broken]}, {"plugins": [blank]})
    assert any("no non-empty string `id`" in v.reason for v in violations)


@pytest.mark.parametrize("bad_id", [None, "", "   ", 123])
def test_missing_or_non_string_id_flagged(tmp_path, bad_id):
    entry = _plugin("foo-kit", "./foo-kit")
    if bad_id is None:
        del entry["id"]
    else:
        entry["id"] = bad_id
    _write_inventory(tmp_path, [entry])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "missing or not a non-empty string" in violations[0].reason


def test_duplicate_id_flagged_so_a_decoy_record_cannot_stand_in(tmp_path):
    real = _plugin("foo-kit", "./foo-kit", prefix="xyz")
    decoy = _plugin("foo-kit", "./foo-kit", prefix="abc", status="retired")
    decoy["id"] = real["id"]  # same id as the real record
    _write_inventory(tmp_path, [real, decoy])
    violations = find_prefix_violations(tmp_path)
    assert any(
        "is already used by" in v.reason and "an id is unique" in v.reason for v in violations
    )


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


def test_permanence_renamed_prefixed_record_is_violation():
    # Security-reviewer finding (round 9, Critical): renaming a prefixed
    # record while keeping id and prefix unchanged un-joins it from
    # marketplace.json's authoritative entry (find_prefix_violations looks
    # up the manifest by the inventory's own `name` field) -- the manifest
    # still lists the old name as installed, but no inventory record holds
    # it anymore, so the plugin escapes the prefix scan entirely under
    # either name.
    base = {"plugins": [{"id": "p1", "name": "git-kit", "prefix": "git"}]}
    head = {"plugins": [{"id": "p1", "name": "git-kit-legacy", "prefix": "git"}]}
    violations = find_prefix_permanence_violations(base, head)
    assert len(violations) == 1
    assert violations[0].plugin_id == "p1"
    assert "git-kit" in violations[0].reason and "git-kit-legacy" in violations[0].reason


def test_permanence_unrenamed_prefixed_record_no_violation():
    base = {"plugins": [{"id": "p1", "name": "git-kit", "prefix": "git"}]}
    head = {"plugins": [{"id": "p1", "name": "git-kit", "prefix": "git"}]}
    assert find_prefix_permanence_violations(base, head) == []


def test_permanence_coordinated_rename_with_matching_manifest_no_violation(tmp_path):
    # Live CodeRabbit + Codex review (PR #387 round 2): a rename
    # coordinated with a matching marketplace.json update in the same PR
    # keeps the head record joined to its authoritative entry --
    # find_prefix_violations still finds and scans it under the new name,
    # so this isn't a real permanence violation. `reconcile.
    # apply_status_transition`'s own `new_name` field is exactly this
    # supported, `naming_history`-tracked rename.
    _write_marketplace_manifest(tmp_path, [{"name": "git-kit-legacy", "source": "./git-kit"}])
    base = {"plugins": [{"id": "p1", "name": "git-kit", "source": "./git-kit", "prefix": "git"}]}
    head = {
        "plugins": [{"id": "p1", "name": "git-kit-legacy", "source": "./git-kit", "prefix": "git"}]
    }
    assert find_prefix_permanence_violations(base, head, repo=tmp_path) == []


def test_permanence_uncoordinated_rename_with_repo_still_violation(tmp_path):
    # The manifest wasn't updated to match the rename -- the join is
    # broken, so this is still a violation even when `repo` is supplied.
    _write_marketplace_manifest(tmp_path, [{"name": "git-kit", "source": "./git-kit"}])
    base = {"plugins": [{"id": "p1", "name": "git-kit", "source": "./git-kit", "prefix": "git"}]}
    head = {
        "plugins": [{"id": "p1", "name": "git-kit-legacy", "source": "./git-kit", "prefix": "git"}]
    }
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert len(violations) == 1
    assert "git-kit" in violations[0].reason and "git-kit-legacy" in violations[0].reason


def test_permanence_id_takeover_by_unrelated_plugin_is_violation(tmp_path):
    # #440 item 6 (reproduced bypass): permanence joins base to head on `id`
    # alone. Plugin A (id X, prefix `abc`) gets a NEW unique id with
    # `prefix: null`, while an unrelated, manifest-backed plugin B takes over
    # id X and the prefix. Both ids stay unique, so the duplicate-id check
    # stays quiet; B's "rename" from A joins marketplace.json, so the rename
    # check accepts it. Net effect: the prefix moved to another plugin, A is
    # silently prefix-less, and nothing is reported.
    _write_marketplace_manifest(
        tmp_path,
        [{"name": "a", "source": "./a"}, {"name": "b", "source": "./b"}],
    )
    base = {"plugins": [{"id": "X", "name": "a", "source": "./a", "prefix": "abc"}]}
    head = {
        "plugins": [
            {"id": "Y", "name": "a", "source": "./a", "prefix": None},
            {"id": "X", "name": "b", "source": "./b", "prefix": "abc"},
        ]
    }
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert violations, "prefix `abc` moved from plugin a to unrelated plugin b unreported"
    assert any(v.plugin_id == "X" and "source changed" in v.reason for v in violations)


def test_permanence_source_change_under_same_id_is_violation():
    # Same id and prefix but a different `source` is a different plugin
    # wearing the old id, even with no second record involved.
    base = {"plugins": [{"id": "X", "name": "a", "source": "./a", "prefix": "abc"}]}
    head = {"plugins": [{"id": "X", "name": "a", "source": "./other", "prefix": "abc"}]}
    violations = find_prefix_permanence_violations(base, head)
    assert len(violations) == 1
    assert "source changed" in violations[0].reason


def _src_rec(id_, name, source, prefix, status="active"):
    return {"id": id_, "name": name, "source": source, "prefix": prefix, "status": status}


def test_permanence_manifest_confirmed_source_move_is_allowed(tmp_path):
    # marketplace-inventory's own `update source` flow: the manifest lists the
    # new directory under the same name and nothing claims the old one.
    _write_marketplace_manifest(tmp_path, [{"name": "a", "source": "./plugins/a-v2"}])
    base = {"plugins": [_src_rec("X", "a", "./plugins/a", "abc")]}
    head = {"plugins": [_src_rec("X", "a", "./plugins/a-v2", "abc")]}
    assert find_prefix_permanence_violations(base, head, repo=tmp_path) == []


def test_permanence_source_move_not_confirmed_by_manifest_is_violation(tmp_path):
    _write_marketplace_manifest(tmp_path, [{"name": "a", "source": "./plugins/a"}])
    base = {"plugins": [_src_rec("X", "a", "./plugins/a", "abc")]}
    head = {"plugins": [_src_rec("X", "a", "./plugins/a-v2", "abc")]}
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("source changed" in v.reason for v in violations)


def test_permanence_source_move_without_repo_is_violation():
    base = {"plugins": [_src_rec("X", "a", "./plugins/a", "abc")]}
    head = {"plugins": [_src_rec("X", "a", "./plugins/a-v2", "abc")]}
    assert find_prefix_permanence_violations(base, head)


def test_permanence_planned_record_gaining_first_source_is_allowed():
    base = {"plugins": [_src_rec("X", "a", None, "abc", status="planned")]}
    head = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    assert find_prefix_permanence_violations(base, head) == []


def test_permanence_first_source_under_a_different_name_is_violation():
    base = {"plugins": [_src_rec("X", "a", None, "abc", status="planned")]}
    head = {"plugins": [_src_rec("X", "b", "./b", "abc")]}
    assert find_prefix_permanence_violations(base, head)


@pytest.mark.parametrize("spelling", ["a", "./a/", ".\\a", "./A"])
def test_permanence_source_spelling_change_is_not_a_move(spelling):
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {"plugins": [_src_rec("X", "a", spelling, "abc")]}
    assert find_prefix_permanence_violations(base, head) == []


def test_permanence_name_moved_to_new_id_while_old_id_keeps_source_is_violation(tmp_path):
    # M2 (security-reviewer, delta pass): the swap in the other direction. The
    # old id keeps its source and prefix under a dummy name, the real plugin
    # name goes to a new unprefixed id pointing at a new directory.
    _write_marketplace_manifest(
        tmp_path, [{"name": "a", "source": "./a-new"}, {"name": "b", "source": "./a"}]
    )
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {"plugins": [_src_rec("X", "b", "./a", "abc"), _src_rec("Y", "a", "./a-new", None)]}
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("holds that name" in v.reason for v in violations)


def test_permanence_source_reregistered_under_new_id_is_violation(tmp_path):
    # M3 (security-reviewer, delta pass): retire the record, register the same
    # directory under a new name and id with no prefix -- the scan then skips
    # both records and never looks at the directory.
    _write_marketplace_manifest(tmp_path, [{"name": "a2", "source": "./a"}])
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc", status="retired"),
            _src_rec("Y", "a2", "./a", None),
        ]
    }
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("now claims that directory" in v.reason for v in violations)


@pytest.mark.parametrize("spelling", ["./x/../a", "./a/./", "./a/../a"])
def test_permanence_dotdot_respelling_cannot_hide_the_old_directory(tmp_path, spelling):
    # Second security pass, M1: `./x/../a` is `./a`. Respelling the old
    # directory must neither make it look released (confirmed_move) nor hide
    # a new record's claim on it.
    _write_marketplace_manifest(
        tmp_path, [{"name": "a-new", "source": spelling}, {"name": "b", "source": "./b"}]
    )
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {"plugins": [_src_rec("Y", "a-new", spelling, None), _src_rec("X", "b", "./b", "abc")]}
    assert find_prefix_permanence_violations(base, head, repo=tmp_path)


def test_permanence_dotdot_respelled_directory_reregistered_is_violation(tmp_path):
    _write_marketplace_manifest(tmp_path, [{"name": "a2", "source": "./a/../a"}])
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc", status="retired"),
            _src_rec("Y", "a2", "./a/../a", None),
        ]
    }
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("now claims that directory" in v.reason for v in violations)


def test_permanence_path_escaping_the_repo_never_reads_as_no_source():
    # A `..`-escaping source gets a sentinel, not None: None would let it
    # pass as a prefixed record that simply has no source yet.
    base = {"plugins": [_src_rec("X", "a", "../outside", "abc")]}
    head = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    assert find_prefix_permanence_violations(base, head)


def test_permanence_sibling_sharing_directory_at_base_cannot_be_reactivated(tmp_path):
    # Second security pass, M2: a retired sibling that already shared the
    # directory at base is exempt only while it is untouched. Reactivating it
    # under a new name while the prefixed record retires must still be caught.
    _write_marketplace_manifest(tmp_path, [{"name": "a2", "source": "./a"}])
    base = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc"),
            _src_rec("D", "old", "./a", None, status="retired"),
        ]
    }
    head = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc", status="retired"),
            _src_rec("D", "a2", "./a", None),
        ]
    }
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("now claims that directory" in v.reason for v in violations)


def test_permanence_sibling_sharing_name_at_base_cannot_take_the_name_to_a_new_directory(
    tmp_path,
):
    _write_marketplace_manifest(
        tmp_path, [{"name": "zz", "source": "./a"}, {"name": "a", "source": "./a-new"}]
    )
    base = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc"),
            _src_rec("D", "a", "./old", None, status="retired"),
        ]
    }
    head = {"plugins": [_src_rec("X", "zz", "./a", "abc"), _src_rec("D", "a", "./a-new", None)]}
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("holds that name" in v.reason for v in violations)


def test_permanence_source_move_allowed_despite_untouched_retired_sibling_on_old_path(tmp_path):
    # Second security pass, M3: marketplace-inventory's `update source` only
    # touches the active record; a retired sibling keeps the old path. That
    # untouched sibling must not block the move.
    _write_marketplace_manifest(tmp_path, [{"name": "a", "source": "./a2"}])
    base = {
        "plugins": [
            _src_rec("Z", "a", "./a", "xyz"),
            _src_rec("W", "a", "./a", None, status="retired"),
        ]
    }
    head = {
        "plugins": [
            _src_rec("Z", "a", "./a2", "xyz"),
            _src_rec("W", "a", "./a", None, status="retired"),
        ]
    }
    assert find_prefix_permanence_violations(base, head, repo=tmp_path) == []


def test_permanence_prefixed_record_becoming_another_plugin_is_violation(tmp_path):
    # Third security pass, M1: the original attack mirrored. X keeps its id and
    # prefix but turns into plugin `b` (new name AND new source), while the
    # real plugin `a` is re-registered under a new unprefixed id.
    _write_marketplace_manifest(
        tmp_path, [{"name": "b", "source": "./b"}, {"name": "a-new", "source": "./a-new"}]
    )
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {"plugins": [_src_rec("X", "b", "./b", "abc"), _src_rec("Y", "a-new", "./a-new", None)]}
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("at once" in v.reason and v.plugin_id == "X" for v in violations)


@pytest.mark.parametrize("root", [".", "./", "./."])
def test_permanence_repo_root_source_is_a_real_source_not_no_source(tmp_path, root):
    # Fourth security pass, M1: a root-sourced plugin (common in single-plugin
    # marketplaces) must not normalize to "no source", or the identity and
    # directory rules all switch off and the mirrored takeover reopens for it.
    _write_marketplace_manifest(
        tmp_path, [{"name": "b", "source": "./b"}, {"name": "a-new", "source": root}]
    )
    base = {"plugins": [_src_rec("X", "a", root, "abc")]}
    head = {"plugins": [_src_rec("X", "b", "./b", "abc"), _src_rec("Y", "a-new", root, None)]}
    assert find_prefix_permanence_violations(base, head, repo=tmp_path)


def test_permanence_root_source_is_not_treated_as_a_first_source():
    # `.` is a real source, so a planned record "gaining" it is not the
    # no-source -> first-source case; the same holds in reverse.
    base = {"plugins": [_src_rec("X", "a", None, "abc", status="planned")]}
    head = {"plugins": [_src_rec("X", "a", "./", "abc")]}
    assert find_prefix_permanence_violations(base, head) == []
    assert find_prefix_permanence_violations(head, base)


def test_permanence_prefixed_record_cannot_take_a_live_plugins_name_or_directory(tmp_path):
    # Acquiring side of the same takeover: X renames onto / moves onto a live
    # base plugin B's name or directory -- one change only, so the
    # both-fields rule does not fire and the claim rule must.
    _write_marketplace_manifest(tmp_path, [{"name": "b", "source": "./a"}])
    base = {"plugins": [_src_rec("X", "a", "./a", "abc"), _src_rec("B", "b", "./b", None)]}
    renamed_onto_b = {
        "plugins": [_src_rec("X", "b", "./a", "abc"), _src_rec("B", "b2", "./b", None)]
    }
    violations = find_prefix_permanence_violations(base, renamed_onto_b, repo=tmp_path)
    assert any("belonged to live plugin" in v.reason for v in violations)

    _write_marketplace_manifest(tmp_path, [{"name": "a", "source": "./b"}])
    moved_onto_b = {"plugins": [_src_rec("X", "a", "./b", "abc"), _src_rec("B", "b", "./b2", None)]}
    violations = find_prefix_permanence_violations(base, moved_onto_b, repo=tmp_path)
    assert any("belonged to live plugin" in v.reason for v in violations)


def test_permanence_manifest_only_entry_cannot_take_the_old_name(tmp_path):
    # Third security pass, M2a: no inventory record is involved -- the old
    # name is simply listed in marketplace.json at a new directory after the
    # prefixed record was (validly) renamed away from it.
    _write_marketplace_manifest(
        tmp_path, [{"name": "a-old", "source": "./a"}, {"name": "a", "source": "./new"}]
    )
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {"plugins": [_src_rec("X", "a-old", "./a", "abc")]}
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("marketplace.json still lists name" in v.reason for v in violations)


def test_permanence_manifest_only_entry_cannot_take_the_old_directory(tmp_path):
    # Third security pass, M2b: X retires and the directory is re-listed in
    # marketplace.json under another name with no inventory record at all.
    _write_marketplace_manifest(tmp_path, [{"name": "a2", "source": "./a"}])
    base = {"plugins": [_src_rec("X", "a", "./a", "abc")]}
    head = {"plugins": [_src_rec("X", "a", "./a", "abc", status="retired")]}
    violations = find_prefix_permanence_violations(base, head, repo=tmp_path)
    assert any("under a different name" in v.reason for v in violations)


def test_permanence_sibling_status_only_change_is_not_a_violation(tmp_path):
    # Third security pass, m1: a superseded -> retired edit on a sibling that
    # already shared the name at base is not a takeover (it never went live).
    _write_marketplace_manifest(tmp_path, [{"name": "a", "source": "./a"}])
    base = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc"),
            _src_rec("W", "a", "./a-old", None, status="superseded"),
        ]
    }
    head = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc"),
            _src_rec("W", "a", "./a-old", None, status="retired"),
        ]
    }
    assert find_prefix_permanence_violations(base, head, repo=tmp_path) == []


def test_permanence_unchanged_shared_source_and_name_at_base_is_not_a_violation():
    # A pair that already coexisted at base (a retired prefixed record and an
    # active one sharing its directory or name) must not trip the new checks.
    base = {
        "plugins": [
            _src_rec("X", "a", "./a", "abc", status="retired"),
            _src_rec("Y", "a", "./a", None),
        ]
    }
    assert find_prefix_permanence_violations(base, base) == []


def test_malformed_prefix_rejected(tmp_path):
    # Found by a live Codex cross-model-review pass (round 4): a
    # hand-edited marketplace-inventory.json bypassing the CLI's own
    # validate_prefix() call previously reached find_prefix_violations
    # with no format check at all.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "TOOLONG-check-pr-title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="TOOLONG")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert "does not match" in violations[0].reason


def test_trailing_newline_prefix_rejected(tmp_path):
    # CodeRabbit finding (round 9): PREFIX_PATTERN.match("abc\n") succeeds
    # because `$` matches just before a trailing newline -- fullmatch is
    # required to actually reject it as an invalid 3-4-letter prefix.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git\n")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert "does not match" in violations[0].reason


def test_duplicate_prefix_across_two_plugins_rejected(tmp_path):
    plugin_a = tmp_path / "git-kit"
    (plugin_a / "scripts").mkdir(parents=True)
    (plugin_a / "scripts" / "git-check.py").write_text("", encoding="utf-8")
    plugin_b = tmp_path / "go-kit"
    (plugin_b / "scripts").mkdir(parents=True)
    (plugin_b / "scripts" / "git-other.py").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path,
        [
            _plugin("git-kit", "./git-kit", prefix="git"),
            _plugin("go-kit", "./go-kit", prefix="git"),
        ],
    )
    violations = find_prefix_violations(tmp_path)
    duplicate_violations = [v for v in violations if "unique marketplace-wide" in v.reason]
    assert len(duplicate_violations) == 1
    assert duplicate_violations[0].plugin == "go-kit"


def test_duplicate_prefix_flagged_even_when_second_plugin_retired(tmp_path):
    # _validate_prefix_fields' own CLI-path equivalent checks uniqueness across
    # every status, not just active/deprecated -- a prefix is permanent
    # and never reused even after a plugin is retired. This checker must
    # agree, even though retired plugins are otherwise skipped for the
    # file-basename scan.
    plugin_a = tmp_path / "git-kit"
    (plugin_a / "scripts").mkdir(parents=True)
    (plugin_a / "scripts" / "git-check.py").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path,
        [
            _plugin("git-kit", "./git-kit", prefix="git"),
            _plugin("old-kit", "./old-kit", prefix="git", status="retired"),
        ],
    )
    violations = find_prefix_violations(tmp_path)
    duplicate_violations = [v for v in violations if "unique marketplace-wide" in v.reason]
    assert len(duplicate_violations) == 1
    assert duplicate_violations[0].plugin == "old-kit"


def test_source_mismatching_authoritative_manifest_rejected(tmp_path):
    # Found by a live Codex cross-model-review pass (round 5): the
    # inventory's own `source` field is a separately update-able copy, not
    # necessarily synced with marketplace.json -- a PR could redirect a
    # prefixed plugin's inventory `source` to an empty in-repo directory
    # while leaving unprefixed files in the plugin's real, still-registered
    # (per marketplace.json) location, untouched and unscanned.
    real_plugin_dir = tmp_path / "git-kit"
    (real_plugin_dir / "scripts").mkdir(parents=True)
    (real_plugin_dir / "scripts" / "not-prefixed.py").write_text("", encoding="utf-8")
    decoy_dir = tmp_path / "decoy-empty-dir"
    decoy_dir.mkdir()
    _write_inventory(
        tmp_path, [_plugin("git-kit", "./decoy-empty-dir", prefix="git")], write_manifest=False
    )
    _write_marketplace_manifest(tmp_path, [{"name": "git-kit", "source": "./git-kit"}])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert "does not match the authoritative" in violations[0].reason


def test_source_matching_authoritative_manifest_still_scanned_normally(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git_check.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


def test_plugin_absent_from_authoritative_manifest_rejected(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check.py").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")], write_manifest=False
    )
    _write_marketplace_manifest(tmp_path, [])  # git-kit not listed at all
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert "does not match the authoritative" in violations[0].reason


def test_duplicate_manifest_name_rejected_not_silently_resolved(tmp_path):
    # Security-reviewer finding (round 9, Major): a second, spoofed
    # marketplace.json entry sharing a live prefixed plugin's name was
    # previously resolved by silent last-entry-wins in
    # _load_authoritative_sources' dict comprehension -- an attacker-
    # controlled second entry could redirect the scan to an empty/
    # nonexistent directory while the real, unprefixed files sat untouched
    # under the first entry's real source.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "not-prefixed.py").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")], write_manifest=False
    )
    _write_marketplace_manifest(
        tmp_path,
        [
            {"name": "git-kit", "source": "./git-kit"},
            {"name": "git-kit", "source": "./empty-decoy"},
        ],
    )
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert "more than once" in violations[0].reason


def test_falsy_prefix_values_validated_not_silently_skipped(tmp_path):
    # Found by a live Codex cross-model-review pass (round 5): `if not
    # prefix` treated "", 0, and False the same as an absent prefix,
    # silently skipping format validation instead of rejecting them.
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "does not match" in violations[0].reason


def test_permanence_falsy_base_prefix_treated_as_no_prior_prefix():
    # Sibling fix to the check-prefixes falsy-prefix gap, applied to
    # find_prefix_permanence_violations' own base_by_id filter.
    base = {"plugins": [{"id": "p1", "name": "a", "prefix": ""}]}
    head = {"plugins": [{"id": "p1", "name": "a", "prefix": "abc"}]}
    assert find_prefix_permanence_violations(base, head) == []


def test_null_source_on_prefixed_plugin_rejected_not_silently_skipped(tmp_path):
    # Found by a live Codex cross-model-review pass (round 6): an earlier
    # version of the authoritative-source check had `if not source:
    # continue` before ever comparing against marketplace.json, so a PR
    # could set source: null on a prefixed record and bypass R33 entirely
    # -- the plugin's real, manifest-registered directory (still containing
    # unprefixed files) was never scanned, and check-prefix-permanence
    # alone doesn't compensate since it only compares prefix values.
    real_plugin_dir = tmp_path / "git-kit"
    (real_plugin_dir / "scripts").mkdir(parents=True)
    (real_plugin_dir / "scripts" / "not-prefixed.py").write_text("", encoding="utf-8")
    entry = _plugin("git-kit", "./git-kit", prefix="git")
    entry["source"] = None
    _write_inventory(tmp_path, [entry], write_manifest=False)
    _write_marketplace_manifest(tmp_path, [{"name": "git-kit", "source": "./git-kit"}])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"
    assert "does not match the authoritative" in violations[0].reason


def test_null_source_and_absent_from_manifest_rejected_not_crash(tmp_path):
    # A checked-status (active/deprecated) prefixed plugin can reach the
    # scan loop even when it's genuinely absent from marketplace.json
    # (never installed, or removed) -- in that case `authoritative_source`
    # is also None, so `None != None` alone would be False and let a null
    # `source` fall through to `repo / source`, a TypeError at runtime.
    # `source is None` must be checked explicitly rather than folded into
    # that comparison. Surfaced by `ty check` after PR #387 round 2's
    # per-name selection refactor made `source`'s type visible.
    entry = _plugin("git-kit", "./git-kit", prefix="git")
    entry["source"] = None
    _write_inventory(tmp_path, [entry], write_manifest=False)
    _write_marketplace_manifest(tmp_path, [])  # git-kit not listed at all
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].plugin == "git-kit"


def _prefix_schema_pattern(prefix_schema: dict) -> str:
    """Extract the `pattern` from a schema's `prefix` property, whether
    declared as a plain `{"type": "string", "pattern": ...}` or as
    `{"anyOf": [{"type": "null"}, {"type": "string", "pattern": ...}]}`."""
    if "pattern" in prefix_schema:
        return prefix_schema["pattern"]
    for option in prefix_schema.get("anyOf", []):
        if "pattern" in option:
            return option["pattern"]
    raise AssertionError(f"no 'pattern' found in prefix schema: {prefix_schema!r}")


def test_prefix_pattern_stays_in_sync_across_all_duplicated_locations():
    # R33's prefix format '^[a-z]{3,4}$' is intentionally hand-duplicated in
    # 4 places -- prefix_check.py's own PREFIX_PATTERN comment explains it
    # deliberately avoids importing plugin-devkit code to avoid backwards
    # coupling, so it can't just reuse inventory_common.pdk_models.PREFIX_PATTERN
    # directly. Nothing else asserted they stay identical (Qodo review
    # finding, PR #387) -- this closes that gap.
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    models_path = (
        repo_root / "plugins" / "plugin-devkit" / "scripts" / "inventory_common" / "pdk_models.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_inventory_common_models_for_sync_test", models_path
    )
    assert spec is not None and spec.loader is not None
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)

    marketplace_schema = json.loads(
        (
            repo_root
            / "plugins/plugin-devkit/skills/marketplace-inventory/assets"
            / "marketplace-inventory.schema.json"
        ).read_text(encoding="utf-8")
    )
    plugin_schema = json.loads(
        (
            repo_root
            / "plugins/plugin-devkit/skills/plugin-inventory/assets"
            / "plugin-inventory.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert models.PREFIX_PATTERN.pattern == PREFIX_PATTERN.pattern
    assert (
        _prefix_schema_pattern(marketplace_schema["definitions"]["plugin"]["properties"]["prefix"])
        == PREFIX_PATTERN.pattern
    )
    assert _prefix_schema_pattern(plugin_schema["properties"]["prefix"]) == PREFIX_PATTERN.pattern


def test_domain_prefix_pattern_stays_in_sync_across_all_duplicated_locations():
    # Same duplicated-constant risk as test_prefix_pattern_stays_in_sync_...
    # above, for `domain_prefix` (R33 addendum, 2026-09-27): '^[a-z][a-z0-9]{2,11}$'
    # is hand-duplicated across inventory_common.pdk_models, both inventory
    # schemas, and this module's own DOMAIN_PREFIX_PATTERN -- same reason
    # prefix_check.py avoids importing plugin-devkit code directly.
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    models_path = (
        repo_root / "plugins" / "plugin-devkit" / "scripts" / "inventory_common" / "pdk_models.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_inventory_common_models_for_domain_sync_test", models_path
    )
    assert spec is not None and spec.loader is not None
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)

    marketplace_schema = json.loads(
        (
            repo_root
            / "plugins/plugin-devkit/skills/marketplace-inventory/assets"
            / "marketplace-inventory.schema.json"
        ).read_text(encoding="utf-8")
    )
    plugin_schema = json.loads(
        (
            repo_root
            / "plugins/plugin-devkit/skills/plugin-inventory/assets"
            / "plugin-inventory.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert models.DOMAIN_PREFIX_PATTERN.pattern == DOMAIN_PREFIX_PATTERN.pattern
    assert (
        _prefix_schema_pattern(
            marketplace_schema["definitions"]["plugin"]["properties"]["domain_prefix"]
        )
        == DOMAIN_PREFIX_PATTERN.pattern
    )
    assert (
        _prefix_schema_pattern(plugin_schema["properties"]["domain_prefix"])
        == DOMAIN_PREFIX_PATTERN.pattern
    )


# --- R33 addendum (2026-09-27): `domain_prefix` OR-match + Python snake_case ---


def test_domain_prefix_only_match_passes_with_no_prefix_registered(tmp_path):
    plugin_dir = tmp_path / "context-kit"
    (plugin_dir / "references").mkdir(parents=True)
    (plugin_dir / "references" / "context-audit.md").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("context-kit", "./context-kit", domain_prefix="context")])
    assert find_prefix_violations(tmp_path) == []


def test_prefix_match_still_passes_when_domain_also_registered(tmp_path):
    plugin_dir = tmp_path / "context-kit"
    (plugin_dir / "references").mkdir(parents=True)
    (plugin_dir / "references" / "ctx-other.md").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path, [_plugin("context-kit", "./context-kit", prefix="ctx", domain_prefix="context")]
    )
    assert find_prefix_violations(tmp_path) == []


def test_free_mix_of_prefix_and_domain_files_both_pass(tmp_path):
    plugin_dir = tmp_path / "context-kit"
    (plugin_dir / "references").mkdir(parents=True)
    (plugin_dir / "references" / "ctx-a.md").write_text("", encoding="utf-8")
    (plugin_dir / "references" / "context-b.md").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path, [_plugin("context-kit", "./context-kit", prefix="ctx", domain_prefix="context")]
    )
    assert find_prefix_violations(tmp_path) == []


def test_neither_prefix_nor_domain_match_fails(tmp_path):
    plugin_dir = tmp_path / "context-kit"
    (plugin_dir / "references").mkdir(parents=True)
    (plugin_dir / "references" / "other.md").write_text("", encoding="utf-8")
    _write_inventory(
        tmp_path, [_plugin("context-kit", "./context-kit", prefix="ctx", domain_prefix="context")]
    )
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "'ctx-'" in violations[0].reason
    assert "'context-'" in violations[0].reason


def test_python_snake_case_prefix_passes(tmp_path):
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git_check_pr_title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


def test_python_snake_case_domain_prefix_passes(tmp_path):
    plugin_dir = tmp_path / "context-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "context_check.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("context-kit", "./context-kit", domain_prefix="context")])
    assert find_prefix_violations(tmp_path) == []


def test_python_kebab_case_prefix_passes(tmp_path):
    # A .py basename starting with 'git-' (kebab-case) is still valid --
    # snake_case is an optional alternative for .py files, not a
    # replacement requirement (relaxed 2026-09-27; see
    # _basename_violation_reason's own docstring for why: CI's trust
    # boundary restores this checker from the base SHA, which can't know
    # about a brand-new mandatory-only rule introduced in the same PR that
    # also needs simultaneous file renames across every registered plugin).
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check-pr-title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    assert find_prefix_violations(tmp_path) == []


def test_python_kebab_prefix_but_underscore_in_rest_fails(tmp_path):
    # Found by a live round-2 Codex review pass: starts with the correct
    # 'git-' kebab separator, but mixes in an underscore later in the
    # basename -- mixing separators within one .py basename is never valid,
    # the same rule the snake_case branch below already enforces in the
    # other direction.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check_pr_title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "kebab-case" in violations[0].reason


def test_python_underscore_prefix_but_hyphen_in_rest_fails(tmp_path):
    # Starts with the correct 'git_' underscore separator, but still has a
    # leftover hyphen later in the basename -- the whole basename must be
    # snake_case, not just the prefix/domain_prefix separator.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git_check-pr-title.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "snake_case" in violations[0].reason


def test_python_non_hyphen_non_snake_case_stem_fails(tmp_path):
    # Found by a live Codex cross-model-review pass: a hyphen-only check on
    # the stem misses a non-snake-case basename that contains no hyphen at
    # all (uppercase letters, dots) -- it still starts with the registered
    # 'git_' prefix and has no '-', so a hyphen-only check would wrongly pass it.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git_Invalid.Name.py").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "snake_case" in violations[0].reason


def test_non_python_file_still_requires_kebab_case_hyphen(tmp_path):
    # The snake_case carve-out is Python-only -- a non-.py file using an
    # underscore separator instead of the registered prefix's hyphen form
    # must still fail.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git_check.sh").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0].path.name == "git_check.sh"


def test_invalid_domain_prefix_format_reported(tmp_path):
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", domain_prefix="GIT")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "registered domain_prefix 'GIT'" in violations[0].reason


def test_duplicate_domain_prefix_reported(tmp_path):
    _write_inventory(
        tmp_path,
        [
            _plugin("git-kit", "./git-kit", domain_prefix="devtools"),
            _plugin("context-kit", "./context-kit", domain_prefix="devtools"),
        ],
    )
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "already used by 'git-kit'" in violations[0].reason


def test_cross_field_collision_prefix_vs_domain_prefix_rejected(tmp_path):
    # Found by a live CodeRabbit + Codex cross-model-review pass, independently:
    # a mirrored component lands at a shared, flat .claude/<dir>/<basename>
    # destination across every plugin (no per-plugin subdirectory) -- two
    # different plugins registering the same value, one as `prefix` and the
    # other as `domain_prefix`, could both legally produce the same basename
    # and collide at the same mirror destination.
    _write_inventory(
        tmp_path,
        [
            _plugin("git-kit", "./git-kit", prefix="abc"),
            _plugin("context-kit", "./context-kit", domain_prefix="abc"),
        ],
    )
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "share a namespace across different plugins" in violations[0].reason


def test_cross_field_collision_domain_prefix_vs_prefix_rejected(tmp_path):
    # Reverse direction of the above.
    _write_inventory(
        tmp_path,
        [
            _plugin("context-kit", "./context-kit", domain_prefix="abc"),
            _plugin("git-kit", "./git-kit", prefix="abc"),
        ],
    )
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "share a namespace across different plugins" in violations[0].reason


def test_same_plugin_may_register_identical_prefix_and_domain_prefix(tmp_path):
    # The cross-field collision check must not fire when the SAME plugin
    # registers the same value for both fields (git-kit's own real case:
    # prefix="git", domain_prefix="git").
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check.sh").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git", domain_prefix="git")])
    assert find_prefix_violations(tmp_path) == []


def test_invalid_domain_prefix_does_not_block_scan_against_valid_prefix(tmp_path):
    # A malformed `domain_prefix` is excluded from the scan individually (already
    # reported by the format check) -- it must not disqualify a plugin whose
    # `prefix` is otherwise valid from being scanned at all.
    plugin_dir = tmp_path / "git-kit"
    (plugin_dir / "scripts").mkdir(parents=True)
    (plugin_dir / "scripts" / "git-check.sh").write_text("", encoding="utf-8")
    _write_inventory(tmp_path, [_plugin("git-kit", "./git-kit", prefix="git", domain_prefix="GIT")])
    violations = find_prefix_violations(tmp_path)
    assert len(violations) == 1
    assert "registered domain_prefix 'GIT'" in violations[0].reason


def test_domain_prefix_permanence_violation_when_reassigned():
    base = {
        "plugins": [_plugin("context-kit", "./context-kit", domain_prefix="context")],
    }
    head = {
        "plugins": [_plugin("context-kit", "./context-kit", domain_prefix="ctxt")],
    }
    violations = find_prefix_permanence_violations(base, head)
    assert len(violations) == 1
    assert "domain_prefix changed from 'context'" in violations[0].reason


def test_prefix_is_required_and_present_on_every_real_record():
    # PR 11: `prefix` is a required key in both inventory schemas; `null` is
    # an explicit opt-out (example-plugin), so every live record must carry
    # the key rather than omit it.
    repo_root = Path(__file__).resolve().parents[2]
    skills = repo_root / "plugins/plugin-devkit/skills"
    marketplace_schema = json.loads(
        (skills / "marketplace-inventory/assets/marketplace-inventory.schema.json").read_text(
            encoding="utf-8"
        )
    )
    plugin_schema = json.loads(
        (skills / "plugin-inventory/assets/plugin-inventory.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert "prefix" in marketplace_schema["definitions"]["plugin"]["required"]
    assert "prefix" in plugin_schema["required"]

    marketplace = json.loads(
        (repo_root / ".claude-plugin/marketplace-inventory.json").read_text(encoding="utf-8")
    )
    missing = [p["name"] for p in marketplace["plugins"] if "prefix" not in p]
    for inventory_path in (repo_root / "plugins").glob("*/.claude-plugin/plugin-inventory.json"):
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        if "prefix" not in inventory:
            missing.append(inventory["plugin_name"])
    assert missing == []
