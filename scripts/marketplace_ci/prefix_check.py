"""Read-only checker for plugin-rulebook's component-file-prefix rule: every
recursively-discovered file under a registered plugin's in-scope directories
must have a basename starting with '<prefix>-'. See
plugins/plugin-devkit/skills/plugin-rulebook/SKILL.md's R33 rule and
.draft/_open/marketplace/prefixes/2026-09-23-plugin-file-prefixes-concept-v3.md
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
from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class PrefixViolation:
    plugin: str
    path: Path
    reason: str


def _iter_files(root: Path):
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def find_prefix_violations(
    repo: Path,
    marketplace_inventory_path: Path | None = None,
) -> list[PrefixViolation]:
    """Read marketplace-inventory.json and return every file, across every
    registered active/deprecated plugin's in-scope directories, whose
    basename doesn't start with that plugin's own '<prefix>-'. Returns an
    empty list -- never raises -- when no marketplace-inventory.json exists
    at all (this repo/target has never bootstrapped one) or when no plugin
    has a registered prefix yet; both are the same "inert until registered"
    gate plugin-rulebook's own R33 and this checker are required to agree
    on."""
    if marketplace_inventory_path is None:
        marketplace_inventory_path = repo / DEFAULT_MARKETPLACE_INVENTORY_PATH
    if not marketplace_inventory_path.is_file():
        return []

    inventory = json.loads(marketplace_inventory_path.read_text(encoding="utf-8"))
    violations: list[PrefixViolation] = []

    for plugin in inventory.get("plugins", []):
        prefix = plugin.get("prefix")
        if not prefix:
            continue
        if plugin.get("status") not in CHECKED_STATUSES:
            continue
        source = plugin.get("source")
        if not source:
            continue
        plugin_dir = (repo / source).resolve()
        plugin_name = plugin["name"]
        expected_prefix = f"{prefix}-"
        hooks_manifest = plugin_dir / "hooks" / HOOKS_MANIFEST_BASENAME

        scope_dirs = list(IN_SCOPE_DIRS)
        if plugin_name == ANTIGRAVITY_PLUGIN_NAME:
            scope_dirs = [*scope_dirs, *ANTIGRAVITY_ONLY_DIRS]

        for dirname in scope_dirs:
            for file_path in _iter_files(plugin_dir / dirname):
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
