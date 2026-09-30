"""Read-only checker for plugin-rulebook's component-file-prefix rule: every
recursively-discovered file under a registered plugin's in-scope directories
must have a basename starting with '<prefix>-' or '<domain_prefix>-' (R33
addendum, 2026-09-27 -- `domain_prefix` is a longer, human-readable alternative to
`prefix`). A '.py' file may additionally use snake_case for its entire
basename instead ('<prefix>_'/'<domain_prefix>_', no hyphen anywhere else) --
an optional alternative, not a replacement for the kebab-case form every
other extension uses. See
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
from typing import Any

# Mirrors inventory_common.pdk_models.PREFIX_PATTERN / the identical
# `^[a-z]{3,4}$` pattern hand-duplicated in marketplace-inventory.schema.json
# and plugin-inventory.schema.json -- keep all four in sync (R20). Not
# imported directly: this module lives under the top-level scripts/ tree,
# not inside any plugin, and importing a specific plugin's internal
# inventory_common package from here would be backwards coupling (top-level
# CI tooling depending on one plugin's own implementation detail).
PREFIX_PATTERN = re.compile(r"^[a-z]{3,4}$")

# Mirrors inventory_common.pdk_models.DOMAIN_PREFIX_PATTERN / the identical
# `^[a-z][a-z0-9]{2,11}$` pattern hand-duplicated in marketplace-inventory.schema.json
# and plugin-inventory.schema.json -- keep all four in sync (R20). `domain_prefix` is
# a longer, human-readable alternative to `prefix` a file's basename may
# start with instead (R33 addendum, 2026-09-27) -- e.g. context-kit's
# `context-audit.md` already reads naturally and doesn't need a `ctx-` rename.
DOMAIN_PREFIX_PATTERN = re.compile(r"^[a-z][a-z0-9]{2,11}$")

# R33 addendum: every .py file in scope uses snake_case (underscores), not
# kebab-case -- both for the prefix/domain_prefix separator and for the rest of the
# basename. Every other extension keeps kebab-case (hyphen separator).
PYTHON_SUFFIX = ".py"

# The full basename (minus '.py') must be snake_case -- lowercase letters,
# digits, and underscores only. A hyphen-only check isn't sufficient: a stem
# with no hyphen can still be invalid snake_case (uppercase letters, dots,
# spaces, etc.) while still starting with a registered prefix/domain_prefix.
# Found by a live Codex cross-model-review pass.
SNAKE_CASE_STEM_PATTERN = re.compile(r"^[a-z0-9_]+$")

# The .py kebab-case counterpart: a stem starting with a registered kebab
# prefix/domain_prefix candidate must be kebab-case throughout too --
# mixing separators (e.g. an underscore later in the name) is never valid
# for a .py file. A startswith-only check isn't sufficient: e.g.
# `git-check_pr_title.py` starts with the registered `git-` prefix but
# mixes in underscores. Found by a live round-2 Codex review pass on the
# same PR that introduced SNAKE_CASE_STEM_PATTERN above.
KEBAB_CASE_STEM_PATTERN = re.compile(r"^[a-z0-9-]+$")

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

# A Python package's __init__.py is a language-mandated filename, never a
# plugin-authored choice -- renaming it breaks the package itself, so it is
# exempt from prefixing (only this exact basename, and only under a plugin's
# root-level scripts/ directory -- the one place Python packages live; the
# package's other modules stay in scope, and an __init__.py under commands/,
# hooks/, etc. is still checked).
PYTHON_PACKAGE_MARKER_BASENAME = "__init__.py"
PYTHON_PACKAGE_SCOPE_DIR = "scripts"

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


def _object_records(
    inventory: dict, path: Path, violations: list[PrefixViolation]
) -> list[dict[str, Any]]:
    """Return `inventory["plugins"]`'s JSON-object entries, reporting (not
    crashing on) a `plugins` value that isn't a list or an entry that isn't
    an object -- either used to surface as an uncaught AttributeError
    traceback instead of a readable CI finding. A missing `plugins` key is
    reported too, rather than read as an empty inventory."""
    if "plugins" not in inventory:
        violations.append(PrefixViolation(plugin="?", path=path, reason="`plugins` key is missing"))
        return []
    plugins = inventory["plugins"]
    if not isinstance(plugins, list):
        violations.append(
            PrefixViolation(plugin="?", path=path, reason="`plugins` is not a JSON array")
        )
        return []
    records: list[dict[str, Any]] = []
    for index, entry in enumerate(plugins):
        if isinstance(entry, dict):
            records.append(entry)
        else:
            violations.append(
                PrefixViolation(
                    plugin=f"plugins[{index}]",
                    path=path,
                    reason="record is not a JSON object",
                )
            )
    return records


def _joinable_records(inventory: dict) -> list[dict[str, Any]]:
    """`inventory["plugins"]`'s object entries, or [] if `plugins` isn't a
    list (or the top level isn't an object)."""
    plugins = inventory.get("plugins", []) if isinstance(inventory, dict) else None
    if not isinstance(plugins, list):
        return []
    return [p for p in plugins if isinstance(p, dict)]


def _has_joinable_id(record: dict[str, Any]) -> bool:
    return isinstance(record.get("id"), str) and bool(record["id"].strip())


def _inventory_structure_problem(inventory: Any) -> str | None:
    """Why `inventory` can't be compared for permanence at all, or None.
    Reading a malformed one as an empty inventory would silently drop every
    registered prefix's protection (fail-open), so the caller reports it."""
    if not isinstance(inventory, dict):
        return "is not a JSON object"
    if "plugins" not in inventory:
        return "has no `plugins` key"
    if not isinstance(inventory["plugins"], list):
        return "has a `plugins` value that is not a JSON array"
    return None


def _records_by_id(inventory: dict) -> dict[str, Any]:
    """Index `inventory["plugins"]` by `id`, skipping records without a
    joinable one. Skipping is fail-closed on the head side (a head record
    that lost its `id` leaves its base counterpart unmatched, reported as
    "the record no longer exists at head"), but NOT on the base side -- the
    caller reports a base record that registers a prefix without a joinable
    `id` separately, since it would otherwise get no protection at all."""
    return {p["id"]: p for p in _joinable_records(inventory) if _has_joinable_id(p)}


def find_prefix_permanence_violations(
    base_inventory: dict, head_inventory: dict, repo: Path | None = None
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
    security-reviewer pass (M2).

    `repo` (optional) enables the rename-tolerance check below: a `name`
    change is only a violation when it breaks the head record's join to
    marketplace.json's authoritative entry. Without `repo` (e.g. a caller
    with no working tree to read a manifest from), every rename is
    conservatively flagged, matching this module's existing fail-closed
    posture.

    Covers both `prefix` and `domain_prefix` (R33 addendum, 2026-09-27) -- `domain_prefix`
    is permanent once assigned the same way `prefix` is, for the same
    reason: it's baked into shipped filenames the moment a plugin migrates."""
    for side, inventory in (("base", base_inventory), ("head", head_inventory)):
        problem = _inventory_structure_problem(inventory)
        if problem is not None:
            return [
                PrefixPermanenceViolation(
                    plugin_id="?",
                    plugin_name="?",
                    reason=f"{side} inventory {problem}, so prefix permanence cannot be checked",
                )
            ]
    # Deliberately a truthy check, not `is not None`: an empty-string or
    # other falsy base value is not a meaningful prior assignment to
    # protect -- find_prefix_violations' own format validation is what
    # flags a falsy/malformed value as a defect in whichever commit it
    # exists in; once corrected to a real first-time prefix/domain_prefix, that's a
    # legitimate first assignment here, not a permanence violation.
    base_by_id = {
        plugin_id: p
        for plugin_id, p in _records_by_id(base_inventory).items()
        if p.get("prefix") or p.get("domain_prefix")
    }
    head_by_id = _records_by_id(head_inventory)

    authoritative_sources: dict[str, str] = {}
    duplicate_manifest_names: set[str] = set()
    if repo is not None:
        authoritative_sources, duplicate_manifest_names = _load_authoritative_sources(repo)

    violations: list[PrefixPermanenceViolation] = []
    # A base record registering a prefix/domain_prefix but lacking a joinable
    # `id` can't be matched to its head counterpart at all, so it would get no
    # permanence protection -- report it rather than skip it. Exception: a
    # head record that now has a joinable `id` and keeps the same name,
    # prefix and domain_prefix is the repair of exactly this defect, so it
    # must not be blocked by the very violation it fixes (a PR that also
    # changes either value still is).
    head_identified = [p for p in _joinable_records(head_inventory) if _has_joinable_id(p)]
    for base_plugin in _joinable_records(base_inventory):
        if (base_plugin.get("prefix") or base_plugin.get("domain_prefix")) and not (
            _has_joinable_id(base_plugin)
        ):
            if any(
                h.get("name") == base_plugin.get("name")
                and h.get("prefix") == base_plugin.get("prefix")
                and h.get("domain_prefix") == base_plugin.get("domain_prefix")
                for h in head_identified
            ):
                continue
            violations.append(
                PrefixPermanenceViolation(
                    plugin_id="?",
                    plugin_name=str(base_plugin.get("name", "?")),
                    reason=(
                        "registers a prefix/domain_prefix at the base commit but has no "
                        "non-empty string `id`, so its permanence cannot be checked"
                    ),
                )
            )
    for plugin_id, base_plugin in base_by_id.items():
        registered_fields = [f for f in ("prefix", "domain_prefix") if base_plugin.get(f)]
        head_plugin = head_by_id.get(plugin_id)
        if head_plugin is None:
            registered = ", ".join(f"{f}={base_plugin[f]!r}" for f in registered_fields)
            violations.append(
                PrefixPermanenceViolation(
                    plugin_id=plugin_id,
                    plugin_name=base_plugin.get("name", "?"),
                    reason=(
                        f"had registered {registered} at the base commit, but the "
                        "record no longer exists at head"
                    ),
                )
            )
            continue
        for field in registered_fields:
            base_value = base_plugin[field]
            head_value = head_plugin.get(field)
            if head_value != base_value:
                violations.append(
                    PrefixPermanenceViolation(
                        plugin_id=plugin_id,
                        plugin_name=head_plugin.get("name", base_plugin.get("name", "?")),
                        reason=(
                            f"{field} changed from {base_value!r} (base) to {head_value!r} "
                            f"(head) -- a {field} is permanent once assigned, never reused or "
                            "reassigned"
                        ),
                    )
                )
        base_name = base_plugin.get("name")
        head_name = head_plugin.get("name")
        if head_name != base_name:
            # `name` is find_prefix_violations' own join key back to
            # marketplace.json's authoritative source (via
            # `_load_authoritative_sources`) -- an unchanged `id`/`prefix`/
            # `domain_prefix` with a renamed `name` un-joins a still-live,
            # still-installed plugin from its manifest entry unless the
            # rename is coordinated with a matching marketplace.json update
            # in the same PR, in which case find_prefix_violations still
            # finds and scans it under the new name. Only a rename that
            # breaks that join is a real permanence violation -- `reconcile.
            # apply_status_transition`'s own `new_name` field is a
            # supported, `naming_history`-tracked rename, not something
            # this check should make permanently impossible. Originally
            # found by a live security-reviewer pass (round 9) as an
            # unconditional rename-is-always-a-violation rule; loosened
            # after a live CodeRabbit + Codex review (PR #387) both
            # independently flagged that rule as over-broad.
            still_joins = (
                repo is not None
                and head_name is not None
                and head_name not in duplicate_manifest_names
                and head_plugin.get("source") is not None
                and authoritative_sources.get(head_name) == head_plugin.get("source")
            )
            if not still_joins:
                registered = ", ".join(f"{f}={base_plugin[f]!r}" for f in registered_fields)
                violations.append(
                    PrefixPermanenceViolation(
                        plugin_id=plugin_id,
                        plugin_name=head_name if head_name is not None else base_name,
                        reason=(
                            f"name changed from {base_name!r} (base) to {head_name!r} (head) "
                            f"while {registered} stayed registered, and the head "
                            "record does not join marketplace.json's authoritative entry for "
                            "the new name via a matching `source` -- renaming a prefixed "
                            "record must stay linked to its manifest entry, or it silently "
                            "escapes the prefix scan entirely"
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


def _basename_violation_reason(
    plugin_name: str, basename: str, prefix: str | None, domain_prefix: str | None
) -> str | None:
    """Check one file's basename against its plugin's registered prefix
    and/or domain_prefix (R33 addendum, 2026-09-27): the basename must start
    with `<prefix>-` or `<domain_prefix>-` (kebab-case) -- the same rule
    every other extension already follows. A `.py` file may *additionally*
    use snake_case for its ENTIRE basename instead (underscores throughout,
    including the prefix/domain_prefix separator: `<prefix>_`/
    `<domain_prefix>_`, no leftover hyphen anywhere else in the name) --
    snake_case is an optional alternative for Python files, not a
    replacement requirement; kebab-case stays valid for `.py` too, but must
    also be kebab-case throughout for a `.py` file -- mixing separators
    (e.g. a leftover underscore) is never valid there, same as the
    snake_case branch below. Non-`.py` files keep the simpler
    startswith-only check (no full-name kebab-case validation) -- unchanged
    by this addendum. (Relaxed 2026-09-27 from an earlier
    mandatory-snake_case-only design: CI's trust boundary restores this
    checker from the *base* SHA, which can't know about a brand-new rule
    introduced in the same PR, and `find_prefix_violations` scans every
    registered plugin's whole tree unconditionally -- a mandatory-only rule
    would force an immediate simultaneous rename of every
    already-registered plugin's `.py` files or break every future PR once
    merged.) Free mix is allowed: either registered identifier, in either
    accepted form, satisfies the rule for any file, new or existing -- the
    curator picks whichever reads better per file. Returns None on a pass,
    or a human-readable violation reason."""
    kebab_candidates = [f"{value}-" for value in (prefix, domain_prefix) if value]
    if not basename.endswith(PYTHON_SUFFIX):
        if any(basename.startswith(c) for c in kebab_candidates):
            return None
        expected = " or ".join(repr(c) for c in kebab_candidates)
        return (
            f"basename does not start with plugin {plugin_name!r}'s registered "
            f"prefix/domain_prefix ({expected})"
        )
    stem = basename[: -len(PYTHON_SUFFIX)]
    snake_candidates = [f"{value}_" for value in (prefix, domain_prefix) if value]
    if any(stem.startswith(c) for c in kebab_candidates):
        if KEBAB_CASE_STEM_PATTERN.fullmatch(stem):
            return None
        # Starts with a valid kebab-case prefix/domain_prefix but isn't
        # fully kebab-case throughout (e.g. a leftover underscore
        # elsewhere) -- mixing separators within one .py basename is never
        # valid. Found by a live round-2 Codex review pass:
        # `git-check_pr_title.py` starts with the registered `git-` prefix
        # but mixes in underscores.
        return (
            "Python basename starts with a kebab-case prefix/domain_prefix but isn't "
            "fully kebab-case throughout -- either use kebab-case throughout "
            f"({' or '.join(repr(c) for c in kebab_candidates)}) or full snake_case "
            f"throughout ({' or '.join(repr(c) for c in snake_candidates)}) "
            f"(plugin {plugin_name!r})"
        )
    if any(stem.startswith(c) for c in snake_candidates):
        if SNAKE_CASE_STEM_PATTERN.fullmatch(stem):
            return None
        # Starts with a valid snake_case prefix/domain_prefix but isn't
        # fully snake_case (e.g. a leftover hyphen, or an uppercase/dot
        # character elsewhere) -- not just a hyphen check, since a stem can
        # contain no hyphen at all and still not be snake_case. Found by a
        # live Codex cross-model-review pass: `git_Invalid.Name.py` starts
        # with the registered `git_` prefix and contains no hyphen, but
        # isn't valid snake_case.
        return (
            "Python basename starts with a snake_case prefix/domain_prefix but isn't "
            "fully snake_case throughout -- either use kebab-case throughout "
            f"({' or '.join(repr(c) for c in kebab_candidates)}) or full snake_case "
            f"throughout (plugin {plugin_name!r})"
        )
    expected = " or ".join(repr(c) for c in kebab_candidates + snake_candidates)
    return (
        f"basename does not start with plugin {plugin_name!r}'s registered "
        f"prefix/domain_prefix, in kebab-case or (for .py files) snake_case ({expected})"
    )


def find_prefix_violations(
    repo: Path,
    marketplace_inventory_path: Path | None = None,
) -> list[PrefixViolation]:
    """Read marketplace-inventory.json and return every file, across every
    registered active/deprecated plugin's in-scope directories, whose
    basename doesn't start with that plugin's own '<prefix>-'. Also
    validates every registered `prefix`'s own format and marketplace-wide
    uniqueness (regardless of plugin status, since a prefix is permanent
    and never reused even after retirement) -- `_validate_prefix_fields` in
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
    if not isinstance(inventory, dict):
        return [
            PrefixViolation(
                plugin="?",
                path=marketplace_inventory_path,
                reason="marketplace-inventory.json's top level is not a JSON object",
            )
        ]
    violations: list[PrefixViolation] = []
    plugins = _object_records(inventory, marketplace_inventory_path, violations)
    repo_resolved = repo.resolve()

    # Format + marketplace-wide uniqueness, across every plugin regardless
    # of status -- checked in its own pass, before the file-basename scan
    # below, since a plugin with a malformed prefix has no well-formed
    # `expected_prefix` to scan files against in the first place. Same pass
    # also validates `domain_prefix` (R33 addendum) -- a longer, human-readable
    # alternative to `prefix` a file's basename may start with instead, in
    # its own independent uniqueness namespace.
    invalid_prefix_plugins: set[str] = set()
    assigned_prefixes: dict[str, str] = {}
    invalid_domain_prefix_plugins: set[str] = set()
    assigned_domain_prefixes: dict[str, str] = {}
    seen_ids: dict[str, str] = {}
    for plugin in plugins:
        plugin_name = plugin.get("name", "?")
        # `id` is what find_prefix_permanence_violations joins base to head on,
        # so a record without a usable, unique one escapes that check: a
        # missing/non-string/empty `id` is skipped from the join, and with a
        # duplicate `id` a decoy record can stand in for the real one (last
        # duplicate wins). Reject both here so neither can reach the base.
        record_id = plugin.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=f"record `id` {record_id!r} is missing or not a non-empty string",
                )
            )
        elif record_id in seen_ids:
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        f"record `id` {record_id!r} is already used by {seen_ids[record_id]!r} "
                        "-- an id is unique, since prefix permanence joins base to head on it"
                    ),
                )
            )
        else:
            seen_ids[record_id] = plugin_name
        if "prefix" not in plugin:
            # `prefix` became a required key in #433: an explicit `null` is the
            # "none registered" opt-out and stays inert below, but an
            # omitted key is malformed. Both read as None via `.get()`, so
            # presence has to be checked here, before that collapse.
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        "record is missing the required `prefix` key -- use an explicit "
                        "`null` if no prefix is registered yet"
                    ),
                )
            )
        prefix = plugin.get("prefix")
        if prefix is not None:
            # fullmatch, not match -- see the identical comment on
            # inventory_common.pdk_models.validate_prefix (R20 sibling fix): with
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
                            f"registered prefix {prefix!r} does not match "
                            f"{PREFIX_PATTERN.pattern!r} (3-4 lowercase letters, no separator)"
                        ),
                    )
                )
            elif (
                prefix in assigned_domain_prefixes
                and assigned_domain_prefixes[prefix] != plugin_name
            ):
                # Cross-field collision: this plugin's `prefix` equals a
                # *different* plugin's `domain_prefix`. `prefix` and
                # `domain_prefix` are independent uniqueness namespaces by
                # design (a plugin may register the same value for both --
                # see the `!= plugin_name` guard), but a mirrored component
                # (commands/, skills/, etc.) lands at a shared, flat
                # `.claude/<dir>/<basename>` destination across every plugin
                # (sync_plan.py's `_resolve_destination`, no per-plugin
                # subdirectory) -- two different plugins could otherwise both
                # legally produce e.g. `commands/foo-status.md` and collide
                # at the same mirror destination. Found by a live CodeRabbit
                # + Codex cross-model review pass, independently.
                violations.append(
                    PrefixViolation(
                        plugin=plugin_name,
                        path=marketplace_inventory_path,
                        reason=(
                            f"registered prefix {prefix!r} is already used as a domain_prefix "
                            f"by {assigned_domain_prefixes[prefix]!r} -- prefix and "
                            "domain_prefix share a namespace across different plugins"
                        ),
                    )
                )
            elif prefix in assigned_prefixes:
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
            else:
                assigned_prefixes[prefix] = plugin_name

        domain_prefix = plugin.get("domain_prefix")
        if domain_prefix is not None:
            if not isinstance(domain_prefix, str) or not DOMAIN_PREFIX_PATTERN.fullmatch(
                domain_prefix
            ):
                invalid_domain_prefix_plugins.add(plugin_name)
                violations.append(
                    PrefixViolation(
                        plugin=plugin_name,
                        path=marketplace_inventory_path,
                        reason=(
                            f"registered domain_prefix {domain_prefix!r} does not match "
                            f"{DOMAIN_PREFIX_PATTERN.pattern!r} (3-12 lowercase alphanumeric "
                            "characters, starting with a letter, no separator)"
                        ),
                    )
                )
            elif (
                domain_prefix in assigned_prefixes
                and assigned_prefixes[domain_prefix] != plugin_name
            ):
                # Same cross-field collision as above, mirrored for the
                # reverse direction (this plugin's domain_prefix equals a
                # different plugin's prefix).
                violations.append(
                    PrefixViolation(
                        plugin=plugin_name,
                        path=marketplace_inventory_path,
                        reason=(
                            f"registered domain_prefix {domain_prefix!r} is already used as a "
                            f"prefix by {assigned_prefixes[domain_prefix]!r} -- prefix and "
                            "domain_prefix share a namespace across different plugins"
                        ),
                    )
                )
            elif domain_prefix in assigned_domain_prefixes:
                violations.append(
                    PrefixViolation(
                        plugin=plugin_name,
                        path=marketplace_inventory_path,
                        reason=(
                            f"registered domain_prefix {domain_prefix!r} is already used by "
                            f"{assigned_domain_prefixes[domain_prefix]!r} -- a domain_prefix "
                            "is unique marketplace-wide"
                        ),
                    )
                )
            else:
                assigned_domain_prefixes[domain_prefix] = plugin_name

    authoritative_sources, duplicate_manifest_names = _load_authoritative_sources(repo)

    # Select at most one inventory record to scan per plugin `name`, before
    # ever reaching the per-record checks below. Two records can
    # legitimately share a `name` (e.g. a retired copy and its active
    # successor both still present in marketplace-inventory.json) --
    # scanning both against their own distinct permanent prefixes would
    # check the same manifest-registered directory against two different
    # `<prefix>-` requirements at once, which no real file tree can
    # satisfy. `status` is a curated, separately human-editable field --
    # the same risk the `source` comment below already documents for that
    # field applies here too: a PR could set `status` to a skip-eligible
    # value (e.g. 'retired'/'planned') while marketplace.json still lists
    # the plugin as installed, exempting a still-live, still-installed
    # plugin from both this check and the file scan below. A plugin
    # present in the authoritative manifest (marketplace.json, via
    # `authoritative_sources`) is always checked regardless of its curated
    # status; only a plugin genuinely absent from the manifest is exempted
    # via CHECKED_STATUSES. Found by a live Codex cross-model-review pass
    # (P1), round 9; the multi-record-per-name gap found by a live
    # CodeRabbit review (Major), PR #387 round 2.
    by_name: dict[str, list[dict[str, Any]]] = {}
    for plugin in plugins:
        if plugin.get("prefix") is None and plugin.get("domain_prefix") is None:
            continue
        by_name.setdefault(plugin.get("name", "?"), []).append(plugin)

    scan_candidates: dict[str, dict[str, Any]] = {}
    for plugin_name, records in by_name.items():
        checked_records = [r for r in records if r.get("status") in CHECKED_STATUSES]
        if len(checked_records) > 1:
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        f"{len(checked_records)} active/deprecated marketplace-inventory.json "
                        f"records share name {plugin_name!r}, each with its own registered "
                        "prefix -- refusing to guess which one's prefix governs this plugin's "
                        "files"
                    ),
                )
            )
            continue
        if checked_records:
            scan_candidates[plugin_name] = checked_records[0]
            continue
        if plugin_name not in authoritative_sources:
            # Genuinely out of scope: no active/deprecated record, and
            # marketplace.json doesn't list this name either.
            continue
        if len(records) > 1:
            violations.append(
                PrefixViolation(
                    plugin=plugin_name,
                    path=marketplace_inventory_path,
                    reason=(
                        f"marketplace.json lists {plugin_name!r} but {len(records)} "
                        "non-active/deprecated marketplace-inventory.json records share that "
                        "name, each with its own registered prefix -- refusing to guess which "
                        "one's prefix governs this plugin's files"
                    ),
                )
            )
            continue
        scan_candidates[plugin_name] = records[0]

    for plugin_name, plugin in scan_candidates.items():
        # A malformed field is excluded from the scan individually (already
        # flagged above by the format pass), not treated as disqualifying
        # the whole plugin -- a plugin with a valid `prefix` and an invalid
        # `domain_prefix` (or vice versa) still gets scanned against whichever
        # field is well-formed.
        prefix = plugin.get("prefix") if plugin_name not in invalid_prefix_plugins else None
        domain_prefix = (
            plugin.get("domain_prefix")
            if plugin_name not in invalid_domain_prefix_plugins
            else None
        )
        if prefix is None and domain_prefix is None:
            # No well-formed prefix or domain_prefix left to scan this plugin's
            # files against.
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
        # `source is None` is checked explicitly, not folded into the `!=`
        # comparison alone: a plugin genuinely absent from marketplace.json
        # (checked-status but never installed, or removed) makes
        # `authoritative_source` None too, so `None != None` would be
        # False and let a null `source` slip through to `repo / source`
        # below -- a TypeError at runtime, not a reported violation. Found
        # via `ty check` surfacing the type of `source` for the first time
        # after this function's per-name selection refactor (PR #387
        # round 2); the underlying gap predates that refactor.
        if source is None or authoritative_source != source:
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
        hooks_manifest = plugin_dir / "hooks" / HOOKS_MANIFEST_BASENAME

        scope_dirs = list(IN_SCOPE_DIRS)
        if plugin_name == ANTIGRAVITY_PLUGIN_NAME:
            scope_dirs = [*scope_dirs, *ANTIGRAVITY_ONLY_DIRS]

        for dirname in scope_dirs:
            for file_path in _iter_files(plugin_dir / dirname, repo_resolved):
                # Symlink check must run before the hooks.json manifest
                # exemption below: `_iter_files` yields a symlinked
                # `hooks/hooks.json` as that same path, so checking the
                # exemption first would let a symlinked manifest silently
                # skip the symlink rejection and evade the prefix scan via
                # its real target. Found by a live Codex cross-model-review
                # pass (P1), PR #387 round 2.
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
                if file_path == hooks_manifest or (
                    dirname == PYTHON_PACKAGE_SCOPE_DIR
                    and file_path.name == PYTHON_PACKAGE_MARKER_BASENAME
                ):
                    continue
                reason = _basename_violation_reason(
                    plugin_name, file_path.name, prefix, domain_prefix
                )
                if reason is not None:
                    violations.append(
                        PrefixViolation(
                            plugin=plugin_name,
                            path=file_path,
                            reason=reason,
                        )
                    )

    return violations
