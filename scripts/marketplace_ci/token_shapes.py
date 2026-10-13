"""Shared secret token shapes: plan the copy of one canonical JSON into each consumer plugin.

Plugins install independently and cannot import from each other or from `scripts/`, so each
consumer reads its own byte-identical copy of `scripts/marketplace_ci/token_shapes.json`. This
module validates the canonical file and plans the create/update actions that bring the copies
back in line; `check-token-shapes` reports a non-empty plan as drift and `sync-token-shapes`
applies it. Nothing here deletes a file.

Imports only `sync_plan` (the read-only plan side), so the check never pulls in sync.py's
write/staging side; the sync handler imports that lazily.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.marketplace_ci.sync_plan import SyncAction, SyncError, SyncPlan

CANONICAL = "scripts/marketplace_ci/token_shapes.json"

# One copy per consumer; basenames differ because each plugin's component-file prefix rule (R33)
# requires its own prefix, but the bytes must be identical. The plugin-devkit hooks keep their own
# partial AKIA copies on purpose (they are fail-closed hooks with a narrower job).
CONSUMERS = (
    "plugins/analysis-kit/scripts/anls-token-shapes.json",
    "plugins/promptlibrary-kit/scripts/plib-token-shapes.json",
    "plugins/codex-kit/scripts/lib/cdx-token-shapes.json",
)

_SHAPE_KEYS = {"name", "pattern"}

# Syntax the Python and JavaScript engines do not both accept: a shape must mean the same thing
# in both, and only Python compiles here. Groups are a whitelist, not a blacklist: any "(?" group
# other than (?: (?= (?! (?<= (?<! is rejected, which covers named groups, inline comments, atomic
# groups, conditionals and inline flags in one rule. The other alternatives are the \A / \Z
# anchors and a possessive quantifier (a quantifier followed by "+"). Every alternative is anchored
# after an even run of backslashes, so an escaped "(" or "+" is not mistaken for syntax.
_PYTHON_ONLY_SYNTAX = re.compile(r"(?<!\\)(?:\\\\)*(?:\(\?(?![:=!]|<[=!])|\\[AZ]|[*+?}]\+)")

# A shape that can match an empty string matches between every two characters; the redactors
# would then insert a marker everywhere and the shapes after it would never run.
_ZERO_WIDTH_PROBES = ("", "a", "a b", "-_.", "A1")


def load_shapes(text: str) -> list[tuple[str, str]]:
    """Parse and validate canonical JSON text into ordered (name, pattern) pairs."""
    try:
        document = json.loads(text)
    except ValueError as exc:
        raise SyncError(f"token shapes: not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or document.get("version") != 1:
        raise SyncError("token shapes: expected a JSON object with version 1")
    shapes = document.get("shapes")
    if not isinstance(shapes, list) or not shapes:
        raise SyncError("token shapes: 'shapes' must be a non-empty list")
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, shape in enumerate(shapes):
        if not isinstance(shape, dict) or set(shape) != _SHAPE_KEYS:
            raise SyncError(f"token shapes: shape {index} must have exactly 'name' and 'pattern'")
        name, pattern = shape["name"], shape["pattern"]
        if not isinstance(name, str) or not name or name in seen:
            raise SyncError(f"token shapes: shape {index} needs a unique non-empty string name")
        if not isinstance(pattern, str) or not pattern:
            raise SyncError(f"token shapes: shape {name!r} needs a non-empty string pattern")
        try:
            compiled: re.Pattern[str] = re.compile(pattern, re.ASCII)
        except re.error as exc:
            raise SyncError(f"token shapes: shape {name!r} does not compile: {exc}") from exc
        if _PYTHON_ONLY_SYNTAX.search(pattern):
            raise SyncError(f"token shapes: shape {name!r} uses syntax JavaScript does not share")
        if any(
            m.end() == m.start() for probe in _ZERO_WIDTH_PROBES for m in compiled.finditer(probe)
        ):
            raise SyncError(
                f"token shapes: shape {name!r} can match zero characters, which would "
                "redact (or erase the redaction of) everything"
            )
        seen.add(name)
        result.append((name, pattern))
    return result


def plan_token_shapes_sync(repo: Path) -> SyncPlan:
    """Create or update each consumer copy so it matches the canonical file byte for byte."""
    source = repo / CANONICAL
    _refuse_symlink(repo, source)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise SyncError(f"token shapes: cannot read {CANONICAL}: {exc}") from exc
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SyncError(f"token shapes: {CANONICAL} is not valid UTF-8: {exc}") from exc
    load_shapes(text)

    actions: list[SyncAction] = []
    for relative in CONSUMERS:
        destination = repo / relative
        _refuse_symlink(repo, destination)
        if not destination.exists():
            actions.append(
                SyncAction("create", source, destination, "missing; copy of the canonical file")
            )
            continue
        try:
            current = destination.read_bytes()
        except OSError as exc:
            raise SyncError(f"token shapes: cannot read {relative}: {exc}") from exc
        if current != data:
            actions.append(
                SyncAction("update", source, destination, "differs from the canonical file")
            )
    return SyncPlan(actions=tuple(actions))


def _refuse_symlink(repo: Path, path: Path) -> None:
    """A symlink (the file itself or any directory between it and the repo root) would pass a
    byte comparison yet break on checkouts without symlink support and in packaging, and could
    redirect a sync write or a loader read outside the repo."""
    current = path
    while current != repo and current != current.parent:
        if current.is_symlink():
            raise SyncError(
                f"token shapes: {path.relative_to(repo).as_posix()} sits under a symlink"
            )
        current = current.parent
