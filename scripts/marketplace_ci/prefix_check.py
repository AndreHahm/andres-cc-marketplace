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
        base_name = base_plugin.get("name")
        head_name = head_plugin.get("name")
        if head_name != base_name:
            # `name` is find_prefix_violations' own join key back to
            # marketplace.json's authoritative source (via
            # `_load_authoritative_sources`) -- an unchanged `id`/`prefix`
            # with a renamed `name` un-joins a still-live, still-installed
            # plugin from its manifest entry, so find_prefix_violations
            # never scans it again under either the old or the new name
            # (the manifest still lists the old name; no inventory record
            # holds it anymore). Same permanence posture as `prefix` itself
            # above: once registered, both stay fixed together. Found by a
            # live security-reviewer pass, round 9.
            violations.append(
                PrefixPermanenceViolation(
                    plugin_id=plugin_id,
                    plugin_name=head_name if head_name is not None else base_name,
                    reason=(
                        f"name changed from {base_name!r} (base) to {head_name!r} (head) "
                        f"while prefix {base_prefix!r} stayed registered -- renaming a "
                        "prefixed record un-links it from marketplace.json's authoritative "
                        "entry, hiding it from the prefix scan entirely"
                    ),
                )
            )
    return violations


def _load_authoritative_sources(
    repo: Path, marketplace_manifest_path: Path | None = None
) -> tuple[dict[str, str], set[str]]:
    """Read `.claude-plugin/marketplace.json` (the actual plugin registry
    `discover_plugins()` in marketplace-inventory.py derives every record's
    `source` from) and return `({plugin_name: source}, {duplicate_names})`.
    `marketplace-inventory.json`'s own per-record `source` field is a
    curated, separately human-update-able copy (it's in
    ALLOWED_UPDATE_FIELDS) -- not necessarily kept live-in-sync with the
    manifest -- so trusting it alone for the directory to scan lets a PR
    redirect a prefixed plugin's `source` to an empty or nonexistent in-repo
    path while leaving unprefixed files in the plugin's real, still-
    registered location untouched. Returns an empty dict/set (never raises)
    if the manifest itself is missing -- callers treat "not found in the
    authoritative manifest" as its own violation, the same fail-visible
    discipline `find_prefix_violations` already uses for every other
    malformed-input case. A `name` appearing more than once in the manifest
    is reported in the second return value rather than silently resolved by
    last-entry-wins: a second, spoofed entry sharing a live prefixed
    plugin's name could otherwise redirect its scan target to an
    attacker-controlled directory while the dict comprehension's overwrite
    hid the collision entirely. Found by a live security-reviewer pass,
    round 9."""
    if marketplace_manifest_path is None:
        marketplace_manifest_path = repo / DEFAULT_MARKETPLACE_MANIFEST_PATH
    if not marketplace_manifest_path.is_file():
        return {}, set()
    manifest = json.loads(marketplace_manifest_path.read_text(encoding="utf-8"))
    sources: dict[str, str] = {}
    duplicate_names: set[str] = set()
    for entry in manifest.get("plugins", []):
        name = entry.get("name")
        source = entry.get("source")
        if not name or not source:
            continue
        if name in sources:
            duplicate_names.add(name)
            continue
        sources[name] = source
    return sources, duplicate_names


def _iter_files(root: Path, repo_resolved: Path):
    """Yield every real file under `root`, plus every symlink encountered
    -- including `root` itself -- so the caller can flag it as a violation
    rather than have it silently vanish from the scan. `recurse_symlinks
    =False` (Python 3.13+) already stops `rglob` descending into a symlinked
    subdirectory; it still yields the symlink itself as a path, which this
    function now surfaces instead of discarding. Never follows a symlink to
    decide what it points to (file vs. directory) -- a symlink's mere
    presence in a prefix-scoped directory is what gets flagged, regardless
    of target. Found by a live security-reviewer pass (a committed symlink
    pointing outside the repo is realistic contributor-controlled input,
    not hypothetical) and a later cross-model-review round (round 7: the
    prior 'continue'/'return' silently dropped the symlink from the scan
    entirely instead of flagging it, letting an unprefixed file bypass R33
    via a symlink)."""
    if root.is_symlink():
        yield root
        return
    if not root.is_dir():
        return
    if not root.resolve().is_relative_to(repo_resolved):
        return
    for path in sorted(root.rglob("*", recurse_symlinks=False)):
        if path.is_symlink():
            yield path
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
        # fullmatch, not match -- see the identical comment on
        # inventory_common.models.validate_prefix (R20 sibling fix): with
        # `match`, `$` matches just before a trailing newline, letting
        # e.g. "abc\n" pass this format check despite not being a real
        # 3-4-letter prefix.
        if not isinstance(prefix, str) or not PREFIX_PATTERN.fullmatch(prefix):
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

    authoritative_sources, duplicate_manifest_names = _load_authoritative_sources(repo)

    for plugin in inventory.get("plugins", []):
        prefix = plugin.get("prefix")
        if prefix is None:
            continue
        plugin_name = plugin.get("name", "?")
        # `status` is a curated, separately human-editable field -- the
        # same risk the `source` comment below already documents for that
        # field applies here too: a PR could set `status` to a
        # skip-eligible value (e.g. 'retired'/'planned') while
        # marketplace.json still lists the plugin as installed, exempting
        # a still-live, still-installed plugin from both this check and the
        # file scan below. A plugin present in the authoritative manifest
        # (marketplace.json, via `authoritative_sources`) is always
        # checked regardless of its curated status; only a plugin genuinely
        # absent from the manifest is exempted via CHECKED_STATUSES. Found
        # by a live Codex cross-model-review pass (P1), round 9.
        if (
            plugin.get("status") not in CHECKED_STATUSES
            and plugin_name not in authoritative_sources
        ):
            continue
        if plugin_name in invalid_prefix_plugins:
            # Already flagged above; a malformed prefix has no well-formed
            # `<prefix>-` pattern to scan this plugin's files against.
            continue
        if plugin_name in duplicate_manifest_names:
            # marketplace.json lists this name more than once -- a spoofed
            # second entry sharing a live prefixed plugin's name could
            # otherwise redirect the scan to an attacker-controlled
            # directory while `authoritative_sources.get(plugin_name)`
            # silently returned whichever entry happened to win. Refuse to
            # trust any single source for a duplicate-named entry rather
            # than guess which one is real. Found by a live security-
            # reviewer pass (M1), round 9.
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        f"marketplace.json lists {plugin_name!r} more than once -- refusing to "
                        "trust any single source for a duplicate-named manifest entry"
                    ),
                )
            )
            continue
        # No `if not source: continue` short-circuit here -- a null/empty
        # inventory `source` on an active, prefixed plugin must be treated
        # exactly like a mismatched one below, not silently skipped. An
        # earlier version of this check exempted a falsy `source` from
        # ever reaching the authoritative-manifest comparison, letting a PR
        # bypass R33 entirely by setting `source: null` on a prefixed
        # record -- its real, manifest-registered directory was then never
        # scanned, while check-prefix-permanence's own comparison (prefix
        # values only) stayed satisfied throughout. Found by a live Codex
        # cross-model-review pass, round 6.
        source = plugin.get("source")
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
            # manifest not listing this plugin at all, or this record's own
            # `source` being null/absent) rather than trust the inventory's
            # unverified copy. Found by a live Codex cross-model-review
            # pass, round 5 (mismatch case) and round 6 (null-source case).
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
                if file_path.is_symlink():
                    violations.append(
                        PrefixViolation(
                            plugin=plugin_name,
                            path=file_path,
                            reason=(
                                "symlinked path found in a prefix-scoped directory -- "
                                "symlinks are not permitted here, since a symlink's "
                                "basename and target both evade the prefix scan"
                            ),
                        )
                    )
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
