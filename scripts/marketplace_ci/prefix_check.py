"""Read-only checker for plugin-rulebook's component-file-prefix rule: every
recursively-discovered file under a registered plugin's in-scope directories
must have a basename starting with '<prefix>-'. See
plugins/plugin-devkit/skills/plugin-rulebook/SKILL.md's R33 rule and
plugins/plugin-devkit/skills/plugin-rulebook/references/component-file-prefix.md
for the full design this mirrors.

Deliberately its own read-only module rather than folded into sync.py/
sync_plan.py's COMPONENT_DIRS mirroring: the five in-scope directories here
(scripts/references/assets/hooks/commands) are not the same set sync_plan.py
mirrors (skills/agents/commands/hooks/rules) -- root-level scripts/,
references/, and assets/ are never mirrored into .claude/ at all (see
.claude/hooks/README.md on why scripts/ specifically stays unmirrored). This
module never writes, stages, or moves a file -- it only reads
marketplace-inventory.json and the plugin trees it names.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# Mirrors inventory_common.models.PREFIX_PATTERN / the identical
# `^[a-z]{3,4}$` pattern hand-duplicated in marketplace-inventory.schema.json
# and plugin-inventory.schema.json -- keep all four in sync (R20). Not
# imported directly: this module lives under the top-level scripts/ tree,
# not inside any plugin, and importing a specific plugin's internal
# inventory_common package from here would be backwards coupling (top-level
# CI tooling depending on one plugin's own implementation detail).
PREFIX_PATTERN = re.compile(r"^[a-z]{3,4}$")

# Root-level directories this rule governs, checked recursively. Distinct
# from sync_plan.py's COMPONENT_DIRS (skills/agents/commands/hooks/rules) --
# this set is a policy scope (what plugin-rulebook's R33 requires), not a
# mirror scope (what gets copied into .claude/).
IN_SCOPE_DIRS = ("scripts", "references", "assets", "hooks", "commands")

# Temporary, single-plugin exception (concept v3's own "Open Item: bin/ and
# docs/" -- antigravity-kit's own planned refactor is expected to retire
# this; do not extend it to any other plugin without an explicit rule
# update).
ANTIGRAVITY_PLUGIN_NAME = "antigravity-kit"
ANTIGRAVITY_ONLY_DIRS = ("bin", "docs")

# hooks/hooks.json itself is structurally merged by sync.py's plan_hooks_merge
# -- never a plugin-authored filename choice, so it's exempt from prefixing
# the same way sync.py's own mirroring already treats it specially.
HOOKS_MANIFEST_BASENAME = "hooks.json"

# A plugin is only checked once it is both actually live (active/deprecated)
# and carries a registered prefix -- a superseded/retired plugin keeps its
# permanent prefix forever (concept v3's own prefix-lifecycle decision) but
# its source files may no longer be canonical or even present, so checking
# them would produce false positives on content nobody maintains anymore.
CHECKED_STATUSES = frozenset({"active", "deprecated"})

DEFAULT_MARKETPLACE_INVENTORY_PATH = Path(".claude-plugin/marketplace-inventory.json")
DEFAULT_MARKETPLACE_MANIFEST_PATH = Path(".claude-plugin/marketplace.json")


@dataclass(frozen=True)
class PrefixViolation:
    plugin: str
    path: Path
    reason: str


@dataclass(frozen=True)
class PrefixPermanenceViolation:
    plugin_id: str
    plugin_name: str
    reason: str


def find_prefix_permanence_violations(
    base_inventory: dict, head_inventory: dict
) -> list[PrefixPermanenceViolation]:
    """Compare `plugins[].prefix` between a base and a head marketplace-
    inventory.json and return every record whose base-assigned prefix was
    reassigned or dropped. This is the enforcement boundary that actually
    matters for "a prefix is permanent once assigned": `reconcile.
    apply_update`'s own write-once guard only protects the marketplace-
    inventory.py CLI's own `update` path -- it does nothing against a
    hand-edited marketplace-inventory.json, or a delete-and-rebootstrap,
    committed directly in a PR. Comparing the file's own content across the
    PR's diff (base vs head) is the only layer that catches either of
    those, since it runs at the point that matters -- PR review -- rather
    than trusting that every change went through the tool. Found by a live
    security-reviewer pass (M2)."""
    # Deliberately a truthy check, not `is not None`: an empty-string or
    # other falsy base value is not a meaningful prior assignment to
    # protect -- find_prefix_violations' own format validation is what
    # flags a falsy/malformed value as a defect in whichever commit it
    # exists in; once corrected to a real first-time prefix, that's a
    # legitimate first assignment here, not a permanence violation.
    base_by_id = {p["id"]: p for p in base_inventory.get("plugins", []) if p.get("prefix")}
    head_by_id = {p["id"]: p for p in head_inventory.get("plugins", [])}

    violations: list[PrefixPermanenceViolation] = []
    for plugin_id, base_plugin in base_by_id.items():
        base_prefix = base_plugin["prefix"]
        head_plugin = head_by_id.get(plugin_id)
        if head_plugin is None:
            violations.append(
                PrefixPermanenceViolation(
                    plugin_id=plugin_id,
                    plugin_name=base_plugin.get("name", "?"),
                    reason=(
                        f"had registered prefix {base_prefix!r} at the base commit, but the "
                        "record no longer exists at head"
                    ),
                )
            )
            continue
        head_prefix = head_plugin.get("prefix")
        if head_prefix != base_prefix:
            violations.append(
                PrefixPermanenceViolation(
                    plugin_id=plugin_id,
                    plugin_name=head_plugin.get("name", base_plugin.get("name", "?")),
                    reason=(
                        f"prefix changed from {base_prefix!r} (base) to {head_prefix!r} (head) "
                        "-- a prefix is permanent once assigned, never reused or reassigned"
                    ),
                )
            )
    return violations


def _load_authoritative_sources(
    repo: Path, marketplace_manifest_path: Path | None = None
) -> dict[str, str]:
    """Read `.claude-plugin/marketplace.json` (the actual plugin registry
    `discover_plugins()` in marketplace-inventory.py derives every record's
    `source` from) and return `{plugin_name: source}`. `marketplace-
    inventory.json`'s own per-record `source` field is a curated, separately
    human-update-able copy (it's in ALLOWED_UPDATE_FIELDS) -- not
    necessarily kept live-in-sync with the manifest -- so trusting it alone
    for the directory to scan lets a PR redirect a prefixed plugin's `source`
    to an empty or nonexistent in-repo path while leaving unprefixed files
    in the plugin's real, still-registered location untouched. Returns an
    empty dict (never raises) if the manifest itself is missing -- callers
    treat "not found in the authoritative manifest" as its own violation,
    the same fail-visible discipline `find_prefix_violations` already uses
    for every other malformed-input case."""
    if marketplace_manifest_path is None:
        marketplace_manifest_path = repo / DEFAULT_MARKETPLACE_MANIFEST_PATH
    if not marketplace_manifest_path.is_file():
        return {}
    manifest = json.loads(marketplace_manifest_path.read_text(encoding="utf-8"))
    return {
        entry["name"]: entry["source"]
        for entry in manifest.get("plugins", [])
        if entry.get("name") and entry.get("source")
    }


def _iter_files(root: Path, repo_resolved: Path):
    """Yield every file under `root`, refusing to cross a symlink at any
    level -- the scope directory itself (e.g. a committed `scripts -> /`
    symlink), or a symlinked entry partway down the tree. `recurse_symlinks
    =False` (Python 3.13+) already stops `rglob` descending into a symlinked
    subdirectory, but it still yields the symlink itself as a path, and does
    nothing about the *starting* directory being a symlink -- both are
    checked explicitly here rather than relied on implicitly. Found by a
    live security-reviewer pass: a plugin tree is ordinary contributor-
    controlled content, so a committed symlink pointing outside the repo is
    a realistic PR-contributed input, not a hypothetical."""
    if root.is_symlink() or not root.is_dir():
        return
    if not root.resolve().is_relative_to(repo_resolved):
        return
    for path in sorted(root.rglob("*", recurse_symlinks=False)):
        if path.is_symlink():
            continue
        if path.is_file():
            yield path


def find_prefix_violations(
    repo: Path,
    marketplace_inventory_path: Path | None = None,
) -> list[PrefixViolation]:
    """Read marketplace-inventory.json and return every file, across every
    registered active/deprecated plugin's in-scope directories, whose
    basename doesn't start with that plugin's own '<prefix>-'. Also
    validates every registered `prefix`'s own format and marketplace-wide
    uniqueness (regardless of plugin status, since a prefix is permanent
    and never reused even after retirement) -- `_validate_prefixes` in
    marketplace-inventory.py's own CLI path already enforces both, but only
    on the CLI's own apply/bootstrap path; a marketplace-inventory.json
    hand-edited directly in a PR (bypassing the CLI entirely) previously
    reached this checker with neither ever checked, letting a malformed or
    duplicated prefix pass as long as the matching files were renamed to
    match it. Found by a live Codex cross-model-review pass, round 4.
    Returns an empty list when no marketplace-inventory.json exists at all
    (this repo/target has never bootstrapped one) or when no plugin has a
    registered prefix yet; both are the same "inert until registered" gate
    plugin-rulebook's own R33 and this checker are required to agree on.
    Malformed input (invalid JSON, a plugin record missing a required
    field) raises rather than silently passing -- a broken inventory file
    should fail CI loudly, not be treated as "nothing to check"."""
    if marketplace_inventory_path is None:
        marketplace_inventory_path = repo / DEFAULT_MARKETPLACE_INVENTORY_PATH
    if not marketplace_inventory_path.is_file():
        return []

    inventory = json.loads(marketplace_inventory_path.read_text(encoding="utf-8"))
    violations: list[PrefixViolation] = []
    repo_resolved = repo.resolve()

    # Format + marketplace-wide uniqueness, across every plugin regardless
    # of status -- checked in its own pass, before the file-basename scan
    # below, since a plugin with a malformed prefix has no well-formed
    # `expected_prefix` to scan files against in the first place.
    invalid_prefix_plugins: set[str] = set()
    assigned_prefixes: dict[str, str] = {}
    for plugin in inventory.get("plugins", []):
        prefix = plugin.get("prefix")
        if prefix is None:
            continue
        plugin_name = plugin.get("name", "?")
        if not isinstance(prefix, str) or not PREFIX_PATTERN.match(prefix):
            invalid_prefix_plugins.add(plugin_name)
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        f"registered prefix {prefix!r} does not match {PREFIX_PATTERN.pattern!r} "
                        "(3-4 lowercase letters, no separator)"
                    ),
                )
            )
            continue
        if prefix in assigned_prefixes:
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        f"registered prefix {prefix!r} is already used by "
                        f"{assigned_prefixes[prefix]!r} -- a prefix is unique marketplace-wide"
                    ),
                )
            )
            continue
        assigned_prefixes[prefix] = plugin_name

    authoritative_sources = _load_authoritative_sources(repo)

    for plugin in inventory.get("plugins", []):
        prefix = plugin.get("prefix")
        if prefix is None:
            continue
        if plugin.get("status") not in CHECKED_STATUSES:
            continue
        if plugin.get("name", "?") in invalid_prefix_plugins:
            # Already flagged above; a malformed prefix has no well-formed
            # `<prefix>-` pattern to scan this plugin's files against.
            continue
        source = plugin.get("source")
        if not source:
            continue
        plugin_name = plugin["name"]
        authoritative_source = authoritative_sources.get(plugin_name)
        if authoritative_source != source:
            # marketplace-inventory.json's own `source` is a curated,
            # separately human-update-able copy (ALLOWED_UPDATE_FIELDS),
            # not necessarily live-synced with marketplace.json -- trusting
            # it alone lets a PR redirect a prefixed plugin's scan target to
            # an empty/nonexistent in-repo path while leaving unprefixed
            # files in the plugin's real, still-registered location
            # untouched. Only the manifest's own value is the plugin's real
            # location; refuse to scan on any mismatch (including the
            # manifest not listing this plugin at all) rather than trust
            # the inventory's unverified copy. Found by a live Codex
            # cross-model-review pass, round 5.
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        f"source {source!r} does not match the authoritative "
                        f"marketplace.json entry ({authoritative_source!r}) -- refusing to scan "
                        "a location marketplace.json doesn't confirm is this plugin's real one"
                    ),
                )
            )
            continue
        plugin_dir = (repo / source).resolve()
        if not plugin_dir.is_relative_to(repo_resolved) or plugin_dir == repo_resolved:
            # `source` is repo-tracked, curated input -- not remote-attacker
            # data -- but a mistyped '../' or an absolute path must never
            # send an rglob() walk outside the checkout, and a source that
            # resolves to the repo root itself (e.g. '.') must never trigger
            # a scan of the repo root's own scripts/hooks/etc -- a flood of
            # unrelated false violations, not a real plugin tree. Report it
            # as a violation (visible in check-prefixes output) rather than
            # silently skipping, since either case is a data-integrity
            # problem worth surfacing.
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=plugin_dir,
                    reason=(
                        f"source {source!r} resolves outside the repository root, or to the "
                        "repository root itself -- refusing to scan it"
                    ),
                )
            )
            continue
        expected_prefix = f"{prefix}-"
        hooks_manifest = plugin_dir / "hooks" / HOOKS_MANIFEST_BASENAME

        scope_dirs = list(IN_SCOPE_DIRS)
        if plugin_name == ANTIGRAVITY_PLUGIN_NAME:
            scope_dirs = [*scope_dirs, *ANTIGRAVITY_ONLY_DIRS]

        for dirname in scope_dirs:
            for file_path in _iter_files(plugin_dir / dirname, repo_resolved):
                if file_path == hooks_manifest:
                    continue
                if not file_path.name.startswith(expected_prefix):
                    violations.append(
                        PrefixViolation(
                            plugin=plugin_name,
                            path=file_path,
                            reason=(
                                f"basename does not start with plugin {plugin_name!r}'s "
                                f"registered prefix {expected_prefix!r}"
                            ),
                        )
                    )

    return violations
