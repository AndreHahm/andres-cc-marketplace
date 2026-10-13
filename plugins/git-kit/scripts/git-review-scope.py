#!/usr/bin/env python3
"""Decide what `cross-model-review` sends to its reviewers, and say what it left out (issue #541).

Reads the changed files (`git diff --name-only <merge-base>`, run in the caller's environment, so
an exported GIT_INDEX_FILE with intent-added untracked files is honored) and writes a manifest:

  - files:            what each reviewer should review, grouped into risk slices (protected,
                      grants, scripts, other, tests, prose) of at most `max_slice_bytes` of diff;
  - excluded:         every file left out, with the reason (config, run pick, byte-identical
                      mirror, lockfile paired with a reviewed manifest, unchanged since a prior
                      round that really reviewed it);
  - inspection_limits: the same facts as sentences, ready for the report. Nothing is cut silently;
  - planned_hashes / carried_hashes: fingerprints (content, mode, symlink target) of the files
                      planned for review this round and of those skipped as already reviewed;
  - candidate_dirs:   top-level folders that still carry diff bytes, for a per-run exclusion pick.

Round two. Pass the previous manifest as --prior-manifest and name each slice whose reviewer
actually finished with --completed-slice (repeatable). Only files in completed slices, plus files
that earlier rounds already carried, count as reviewed; a slice whose reviewer timed out or failed
is reviewed again. With no --completed-slice nothing planned last round counts as reviewed. The
manifest must live outside the repository (a PR could otherwise commit a forged one), be a regular
file, and be owned by the current user; anything else falls back to the full scope.

Trust: the tracked settings and the mirror map are read from the base ref, never the working tree,
so the diff under review cannot add an exclusion that hides itself. A local config file that is
tracked by git, reached through a symlink, a case variant, or not verifiable as untracked is
ignored for the same reason. The local file can only add exclusions. Dispatcher, settings,
.gitattributes, .gitmodules and this skill's own files can never be excluded by config, pick or
lockfile rules, and are kept ahead of the size budget (they do not count against it). A mirror
collapses only into a canonical copy with the same bytes and the same executable bit that is itself
reviewed this round (or already reviewed in an
earlier one, or identical on the base ref); a lockfile is excluded only beside a manifest reviewed
this round; no path through a symlink is ever read. If the budget drops such an anchor, what it
excused is put back. Residual risk: the budget still drops lowest-priority slices (disclosed), so
a dropped slice must be read, not skimmed; and a submodule's inner changes are not part of this
diff at all.

Exit codes: 0 manifest written, 2 could not run (bad input, git failure, or an --output path that
already exists; this script never overwrites anything).

This repository's own convention only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path, PurePosixPath

MANIFEST_VERSION = 2
SETTINGS_PATH = "plugins/git-kit/git-kit.settings.json"
LOCAL_PATH = ".claude/git-kit.local.json"
SYNC_PATH = ".claude/marketplace-sync.json"
# Provisional defaults: PR #505's 290 KB diff is the only measured failure (a 112 KB retry still
# timed out at 240 s), so these are starting points to tune against real runs, not findings.
DEFAULT_BUDGET_BYTES = 250_000
DEFAULT_MAX_SLICE_BYTES = 80_000
# Used only while the base ref's tracked settings lack the dirs key (the first run after it was
# introduced); a tracked `[]` is an explicit choice and wins.
DEFAULT_EXCLUDE_DIRS = ["issues/"]
MAX_MANIFEST_BYTES = 5_000_000
MAX_FILE_BYTES = 10_000_000
_SHA_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_GIT_TIMEOUT_SECONDS = 60
_LIST_KEYS = {
    "dirs": "cross_model_review_exclude_dirs",
    "extensions": "cross_model_review_exclude_extensions",
    "globs": "cross_model_review_exclude_globs",
}
_BUDGET_KEY = "cross_model_review_budget_bytes"
_SLICE_KEY = "cross_model_review_max_slice_bytes"
# A lockfile is excluded only beside its manifest, and only when that manifest is itself being
# reviewed this round; a lockfile changed alone is a supply-chain vector and stays in.
LOCK_MANIFESTS = {
    "uv.lock": "pyproject.toml",
    "poetry.lock": "pyproject.toml",
    "Pipfile.lock": "Pipfile",
    "package-lock.json": "package.json",
    "yarn.lock": "package.json",
    "pnpm-lock.yaml": "package.json",
    "Cargo.lock": "Cargo.toml",
    "go.sum": "go.mod",
    "Gemfile.lock": "Gemfile",
    "composer.lock": "composer.json",
}
# Config, run picks and the budget may never hide these; a mirror that is byte-identical to its
# canonical file may still collapse into it, because the canonical copy is what gets reviewed.
# Matching is case-insensitive on purpose.
NEVER_EXCLUDE = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"(^|/)codex-kit/(.*/)?(scripts|assets)/",
        r"(^|/)skills/(codex-review-bridge|codex-windows-guardrails)/",
        r"(^|/)git-kit\.(settings|local)\.json\Z",
        r"(^|/)skills/cross-model-review/",
        r"(^|/)git-review-scope\.py\Z",
        r"(^|/)marketplace-sync\.json\Z",
        r"(^|/)\.gitattributes\Z",
        r"(^|/)\.gitmodules\Z",
    )
)
_GITATTRIBUTES_RE = re.compile(r"(^|/)\.gitattributes\Z", re.IGNORECASE)
_GITMODULES_RE = re.compile(r"(^|/)\.gitmodules\Z", re.IGNORECASE)
MIRROR_COMPONENTS = ("skills", "agents", "commands", "hooks", "rules", "references", "assets")
CLASS_ORDER = ("protected", "grants", "scripts", "other", "tests", "prose")
_SCRIPT_EXTENSIONS = frozenset({".py", ".sh", ".bash", ".mjs", ".cjs", ".js", ".ts", ".ps1"})
_PROSE_EXTENSIONS = frozenset({".md", ".txt", ".rst"})
# Files that grant permissions, load into every session, or launch commands.
_GRANT_RE = re.compile(
    r"(^|/)(settings[^/]*\.json|hooks\.json|plugin\.json|marketplace\.json|CODEOWNERS"
    r"|\.mcp\.json|\.pre-commit-config\.yaml|SKILL\.md|CLAUDE(\.local)?\.md|AGENTS\.md)\Z"
    r"|(^|/)\.github/(workflows|actions)/"
    r"|(^|/)(agents|commands|rules)/[^/]+\.md\Z"
)
_HOOK_EXTENSIONS = _SCRIPT_EXTENSIONS | {".json"}
_EXECUTED_TEST_FILES = frozenset({"conftest.py", "noxfile.py", "pytest.ini", "tox.ini"})
_NAME_RE = re.compile(r"(?!\.{1,2}\Z)[A-Za-z0-9._-]+\Z")
_NEVER_SKIP = frozenset({"unreadable", "other"})
_MAX_LISTED_PATHS = 10

Reader = Callable[[str], "bytes | None"]


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """`**` crosses folders, `*` and `?` stay inside one path segment."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        else:
            c = pattern[i]
            out.append("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + r"\Z")


def _json_object(text: str | None, label: str, notes: list[str]) -> dict:
    if text is None:
        return {}
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        notes.append(f"{label}: unreadable JSON, ignored")
        return {}
    if not isinstance(data, dict):
        notes.append(f"{label}: not a JSON object, ignored")
        return {}
    return data


def _clean_entries(raw: object, kind: str, label: str, notes: list[str]) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        notes.append(f"{label}: not a list, ignored")
        return []
    out: list[str] = []
    for item in raw:
        ok = (
            isinstance(item, str)
            and 0 < len(item) <= 200
            and "\0" not in item
            and not item.startswith("/")
            and ".." not in item.split("/")
            and (kind != "extensions" or (item.startswith(".") and len(item) > 1))
        )
        if not ok:
            notes.append(f"{label}: invalid entry ignored: {item!r}")
        elif kind == "dirs":
            out.append(item if item.endswith("/") else item + "/")
        else:
            out.append(item.lower() if kind == "extensions" else item)
    return out


def _positive_int(raw: object, default: int) -> int:
    return raw if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0 else default


def load_config(tracked_text: str | None, local_text: str | None, local_is_tracked: bool) -> dict:
    """Tracked settings (from the base ref) plus an additive, untracked local override."""
    notes: list[str] = []
    if tracked_text is None:
        notes.append("tracked settings not found on the base ref: built-in defaults used")
    tracked = _json_object(tracked_text, "tracked settings", notes)
    config: dict = {
        "budget_bytes": _positive_int(tracked.get(_BUDGET_KEY), DEFAULT_BUDGET_BYTES),
        "max_slice_bytes": _positive_int(tracked.get(_SLICE_KEY), DEFAULT_MAX_SLICE_BYTES),
        "notes": notes,
        "local_entries": set(),
    }
    sources = [(tracked, "tracked settings", False)]
    if local_text is not None and local_is_tracked:
        notes.append(
            f"{LOCAL_PATH} is tracked by git or could not be verified as untracked: ignored"
        )
    elif local_text is not None:
        sources.append((_json_object(local_text, "local config", notes), "local config", True))
    for kind, key in _LIST_KEYS.items():
        merged: list[str] = []
        for data, label, is_local in sources:
            raw = data.get(key)
            if raw is None and kind == "dirs" and data is tracked:
                raw = DEFAULT_EXCLUDE_DIRS
            for entry in _clean_entries(raw, kind, f"{label} {key}", notes):
                if entry not in merged:
                    merged.append(entry)
                    if is_local:
                        config["local_entries"].add((kind, entry))
        config[kind] = merged
    if config["local_entries"]:
        notes.append(f"local config applied: {len(config['local_entries'])} exclusion(s) from it")
    return config


def parse_sync(text: str | None) -> dict:
    """Mirror map from `.claude/marketplace-sync.json`, tolerant of a missing or odd file."""
    notes: list[str] = []
    if text is None:
        notes.append("mirror map not found on the base ref: mirror collapsing disabled")
    data = _json_object(text, "mirror map", notes)

    def names(key: str) -> list[str]:
        raw = data.get(key)
        return (
            [n for n in raw if isinstance(n, str) and _NAME_RE.match(n)]
            if isinstance(raw, list)
            else []
        )

    raw_exceptions = data.get("divergence_exceptions", [])
    if not isinstance(raw_exceptions, list):
        notes.append("mirror map: divergence_exceptions is not a list, ignored")
        raw_exceptions = []
    exceptions = {
        e["dest"] for e in raw_exceptions if isinstance(e, dict) and isinstance(e.get("dest"), str)
    }
    return {
        "plugin_mirrors": names("plugin_mirrors"),
        "scripts_mirrors": names("scripts_mirrors"),
        "exceptions": exceptions,
        "notes": notes,
    }


def _hash_map(raw: object) -> dict[str, str] | None:
    if isinstance(raw, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in raw.items()
    ):
        return raw
    return None


def load_prior(
    text: str, merge_base: str, completed: Sequence[str] = ()
) -> tuple[dict | None, str | None]:
    """Validate a prior-round manifest; any doubt means a full-scope fallback, never a guess.

    The returned dict carries `reviewed_hashes`: carried files plus the planned files of the
    slices named in `completed`. A slice nobody reports as finished is not counted as reviewed.
    """
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return None, "prior manifest is not valid JSON"
    if not isinstance(data, dict) or data.get("version") != MANIFEST_VERSION:
        return None, "prior manifest has an unsupported shape or version"
    rnd = data.get("round")
    if not isinstance(rnd, int) or isinstance(rnd, bool) or rnd < 1:
        return None, "prior manifest has no valid round number"
    planned = _hash_map(data.get("planned_hashes"))
    carried = _hash_map(data.get("carried_hashes"))
    slices = data.get("slices")
    if planned is None or carried is None or not isinstance(slices, list):
        return None, "prior manifest has malformed reviewed hashes"
    if data.get("base") != merge_base:
        return None, "prior manifest was built against a different merge-base"
    reviewed = dict(carried)
    done = set(completed)
    for entry in slices:
        if not isinstance(entry, dict) or not isinstance(entry.get("files"), list):
            return None, "prior manifest has malformed slices"
        if entry.get("name") in done:
            for path in entry["files"]:
                if isinstance(path, str) and path in planned:
                    reviewed[path] = planned[path]
    return {"round": rnd, "reviewed_hashes": reviewed}, None


def _canonical_candidates(path: str, sync: dict) -> Iterator[str]:
    if path.startswith(".agents/skills/"):
        mirrored = ".claude/skills/" + path[len(".agents/skills/") :]
        yield mirrored
        yield from _canonical_candidates(mirrored, sync)
    elif path.startswith(".claude/"):
        component, _, rest = path[len(".claude/") :].partition("/")
        if component == "scripts":
            plugins = sync["scripts_mirrors"]
        else:
            plugins = sync["plugin_mirrors"] if component in MIRROR_COMPONENTS else []
        if rest:
            for plugin in plugins:
                yield f"plugins/{plugin}/{component}/{rest}"


def _mirror_canonicals(path: str, sync: dict, read: Reader) -> list[str]:
    """Canonical files this path is a byte-for-byte copy of (empty if it is not a clean mirror)."""
    data = read(path)
    if data is None or path in sync["exceptions"]:
        return []
    return [c for c in _canonical_candidates(path, sync) if read(c) == data]


def _config_reason(
    path: str,
    config: dict,
    globs: list[tuple[str, re.Pattern[str]]],
    picks: Sequence[str],
) -> tuple[str, str] | None:
    local = config["local_entries"]

    def label(kind: str, entry: str) -> str:
        return entry + (" (local)" if (kind, entry) in local else "")

    for folder in picks:
        if path.startswith(folder):
            return ("run-pick", folder)
    for folder in config["dirs"]:
        if path.startswith(folder):
            return ("config-dir", label("dirs", folder))
    suffix = PurePosixPath(path).suffix.lower()
    if suffix and suffix in config["extensions"]:
        return ("config-extension", label("extensions", suffix))
    for pattern, regex in globs:
        if regex.match(path):
            return ("config-glob", label("globs", pattern))
    return None


def classify(path: str, executable: bool = False) -> str:
    p = PurePosixPath(path)
    suffix = p.suffix.lower()
    if any(rx.search(path) for rx in NEVER_EXCLUDE):
        return "protected"
    in_hooks = "/hooks/" in f"/{path}" and suffix in _HOOK_EXTENSIONS
    if _GRANT_RE.search(path) or in_hooks:
        return "grants"
    if p.name in _EXECUTED_TEST_FILES:
        return "scripts"
    if path.startswith("tests/") or "/tests/" in path or p.name.startswith("test_"):
        return "tests"
    if suffix in _SCRIPT_EXTENSIONS or executable:
        return "scripts"
    return "prose" if suffix in _PROSE_EXTENSIONS else "other"


def _slices(files: list[dict], max_slice_bytes: int) -> list[dict]:
    slices: list[dict] = []
    for cls in CLASS_ORDER:
        current: dict | None = None
        count = 0
        for entry in sorted((f for f in files if f["class"] == cls), key=lambda f: f["path"]):
            if current is None or current["bytes"] + entry["bytes"] > max_slice_bytes:
                count += 1
                current = {
                    "name": cls if count == 1 else f"{cls}-{count}",
                    "index": count,
                    "class": cls,
                    "files": [],
                    "bytes": 0,
                }
                slices.append(current)
            current["files"].append(entry["path"])
            current["bytes"] += entry["bytes"]
    return slices


def _select(kept: list[dict], config: dict) -> tuple[list[dict], list[dict]]:
    """Slice `kept` and apply the budget; protected slices are always chosen and never counted."""
    order = {c: i for i, c in enumerate(CLASS_ORDER)}
    chosen: list[dict] = []
    dropped: list[dict] = []
    used = 0
    slices = _slices(kept, config["max_slice_bytes"])
    for s in sorted(slices, key=lambda s: (order[s["class"]], s["index"])):
        if s["class"] == "protected":
            chosen.append(s)
        # `not chosen` is deliberate: the "keep the first slice even if it alone is over budget"
        # exception only applies when nothing, protected slices included, would be reviewed
        # otherwise. With a protected slice chosen, an oversized slice must fit the budget, so a
        # padding file cannot be kept free of it. A dropped slice is disclosed and must be read.
        elif not chosen or used + s["bytes"] <= config["budget_bytes"]:
            chosen.append(s)
            used += s["bytes"]
        else:
            dropped.append(s)
    return chosen, dropped


def _listed(paths: Sequence[str]) -> str:
    shown = ", ".join(paths[:_MAX_LISTED_PATHS])
    extra = len(paths) - _MAX_LISTED_PATHS
    return shown + (f" (+{extra} more)" if extra > 0 else "")


def _default_fingerprint(read: Reader) -> Callable[[str], str]:
    def fingerprint(path: str) -> str:
        data = read(path)
        return "deleted" if data is None else "file:-:" + hashlib.sha256(data).hexdigest()

    return fingerprint


def _is_executable(fingerprint: str) -> bool:
    return fingerprint.startswith("file:x:")


def plan_scope(
    changed: Sequence[str],
    config: dict,
    sync: dict,
    *,
    read: Reader,
    diff_size: Callable[[str], int],
    base_read: Reader = lambda _path: None,
    fingerprint: Callable[[str], str] | None = None,
    picks: Sequence[str] = (),
    recheck: Sequence[str] = (),
    prior: dict | None = None,
    fallback: str | None = None,
    base: str = "",
    scope: str = "",
) -> dict:
    fingerprint = fingerprint or _default_fingerprint(read)
    changed_set = set(changed)
    prints = {p: fingerprint(p) for p in changed}
    prior_reviewed = prior["reviewed_hashes"] if prior else {}
    globs = [(g, glob_to_regex(g)) for g in config["globs"]]
    excluded: list[dict] = []
    refused: list[str] = []
    carried: list[str] = []
    solid: list[str] = []  # reviewed unless the budget drops them
    # Mirrors and lockfiles are excused only while their anchor is reviewed: path -> (reason,
    # detail, anchors, identical-on-base).
    conditional: dict[str, tuple[str, str, list[str], bool]] = {}
    for path in changed:
        hit = _config_reason(path, config, globs, picks)
        if hit and any(rx.search(path) for rx in NEVER_EXCLUDE):
            refused.append(path)
            hit = None
        if hit is None and prior and path not in recheck and prints[path] not in _NEVER_SKIP:
            if prior_reviewed.get(path) == prints[path]:
                hit = ("unchanged-since-prior-round", f"round {prior['round']}")
                carried.append(path)
        if hit:
            excluded.append({"path": path, "reason": hit[0], "detail": hit[1]})
            continue
        # Equal bytes are not enough: an executable-bit change on a mirror is a change to review.
        canonicals = [
            c
            for c in _mirror_canonicals(path, sync, read)
            if _is_executable(prints[path]) == _is_executable(fingerprint(c))
        ]
        manifest = LOCK_MANIFESTS.get(PurePosixPath(path).name)
        sibling = str(PurePosixPath(path).with_name(manifest)) if manifest else ""
        if canonicals:
            base_ok = any(base_read(c) == read(path) for c in canonicals)
            conditional[path] = ("mirror-identical", canonicals[0], canonicals, base_ok)
        elif sibling in changed_set:
            detail = f"{PurePosixPath(path).name} with {manifest}"
            conditional[path] = ("lockfile", detail, [sibling], False)
        else:
            solid.append(path)

    sizes: dict[str, int] = {}

    def entry(path: str) -> dict:
        if path not in sizes:
            sizes[path] = diff_size(path)
        return {
            "path": path,
            "class": classify(path, prints[path].startswith("file:x:")),
            "bytes": max(sizes[path], 0),
        }

    collapsed = set(conditional)
    while True:
        kept = [entry(p) for p in solid + sorted(set(conditional) - collapsed)]
        chosen, dropped = _select(kept, config)
        reviewed_now = {p for s in chosen for p in s["files"]}
        still = set()
        for path in collapsed:
            reason, _detail, anchors, base_ok = conditional[path]
            if reason == "lockfile":
                ok = anchors[0] in reviewed_now
            else:
                ok = base_ok or any(a in reviewed_now or a in carried for a in anchors)
            if ok:
                still.add(path)
        if still == collapsed:
            break
        collapsed = still

    for path in sorted(collapsed):
        reason, detail = conditional[path][:2]
        excluded.append({"path": path, "reason": reason, "detail": detail})
    slice_of = {p: s["name"] for s in chosen for p in s["files"]}
    files = [dict(f, slice=slice_of[f["path"]]) for f in kept if f["path"] in slice_of]
    planned = {f["path"]: prints[f["path"]] for f in files}
    carried_hashes = {p: prints[p] for p in carried}

    limits = list(config["notes"]) + list(sync.get("notes", []))
    if fallback:
        limits.append(f"full scope reviewed: {fallback}")
    if scope:
        limits.append(
            f"scope limited to pathspec '{scope}': changes outside it were not considered"
        )
    groups: dict[tuple[str, str], list[str]] = {}
    for e in excluded:
        groups.setdefault((e["reason"], e["detail"]), []).append(e["path"])
    for (reason, detail), paths in groups.items():
        suffix = f" ({detail})" if detail else ""
        limits.append(f"excluded {len(paths)} file(s) by {reason}{suffix}: {_listed(paths)}")
    if refused:
        limits.append(
            f"exclusion refused for protected path(s), still reviewed: {_listed(refused)}"
        )
    lock_kept = [f["path"] for f in files if PurePosixPath(f["path"]).name in LOCK_MANIFESTS]
    if lock_kept:
        limits.append(
            f"lockfile(s) kept for review, no reviewed manifest beside them: {_listed(lock_kept)}"
        )
    if any(_GITATTRIBUTES_RE.search(p) for p in changed):
        limits.append(
            ".gitattributes changed: it can alter how git renders diffs; review it and the files "
            "it matches directly"
        )
    if any(_GITMODULES_RE.search(p) for p in changed):
        limits.append(
            ".gitmodules changed: submodule URLs and pointers changed with it; review it and the "
            "pointer bumps directly"
        )
    unsized = sorted(p for p, n in sizes.items() if n < 0)
    if unsized:
        limits.append(f"diff size unknown (git failed), counted as 0 bytes: {_listed(unsized)}")
    for s in dropped:
        limits.append(
            f"reduced scope: dropped slice '{s['name']}' ({len(s['files'])} file(s), "
            f"{s['bytes']} bytes) over the {config['budget_bytes']}-byte budget: "
            f"{_listed(s['files'])}"
        )

    folders: dict[str, list[int]] = {}
    for f in files:
        top, sep, _ = f["path"].partition("/")
        if sep:
            stats = folders.setdefault(top + "/", [0, 0])
            stats[0] += 1
            stats[1] += f["bytes"]
    candidates = [
        {"dir": d, "files": n, "bytes": b}
        for d, (n, b) in sorted(folders.items(), key=lambda kv: -kv[1][1])
    ]
    return {
        "version": MANIFEST_VERSION,
        "round": prior["round"] + 1 if prior else 1,
        "base": base,
        "scope": scope,
        "fallback": fallback,
        "budget_bytes": config["budget_bytes"],
        "max_slice_bytes": config["max_slice_bytes"],
        "files": files,
        "slices": chosen,
        "dropped_slices": dropped,
        "excluded": excluded,
        "inspection_limits": limits,
        "planned_hashes": planned,
        "carried_hashes": carried_hashes,
        "candidate_dirs": candidates,
    }


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, timeout=_GIT_TIMEOUT_SECONDS, check=False
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["git", *args], 124, b"", b"git timed out")


def _git_show_bytes(repo: Path, sha: str, path: str) -> bytes | None:
    result = _git(repo, "show", f"{sha}:{path}")
    return result.stdout if result.returncode == 0 else None


def _has_symlink(repo: Path, parts: Sequence[str]) -> bool:
    current = repo
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _plain_file(repo: Path, path: str) -> Path | None:
    """The file at `path`, only if no component of the path is a symlink."""
    parts = PurePosixPath(path).parts
    if not parts or any(part in ("..", "/") for part in parts) or _has_symlink(repo, parts):
        return None
    target = repo.joinpath(*parts)
    return target if target.is_file() else None


def _make_reader(repo: Path) -> Reader:
    def read(path: str) -> bytes | None:
        target = _plain_file(repo, path)
        try:
            if target is None or target.stat().st_size > MAX_FILE_BYTES:
                return None
            return target.read_bytes()
        except OSError:
            return None

    return read


def _make_fingerprint(repo: Path) -> Callable[[str], str]:
    """Content, executable bit and symlink target, so none of them can change unnoticed."""

    def fingerprint(path: str) -> str:
        parts = PurePosixPath(path).parts
        if _has_symlink(repo, parts[:-1]):
            return "unreadable"
        target = repo / path
        try:
            st = target.lstat()
            if stat.S_ISLNK(st.st_mode):
                return "symlink:" + os.readlink(target)
            if not stat.S_ISREG(st.st_mode):
                return "other"
            digest = hashlib.sha256()
            with open(target, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except FileNotFoundError:
            return "deleted"
        except OSError:
            return "unreadable"
        return f"file:{'x' if st.st_mode & 0o111 else '-'}:{digest.hexdigest()}"

    return fingerprint


def _local_config(repo: Path, merge_base: str, changed: Sequence[str]) -> tuple[str | None, bool]:
    """(text, untrusted): the local config's text and whether it must be ignored.

    Trusted only when it is a real file (no symlink component), no path that differs from it only
    by case is listed by the index, the base tree, HEAD or this diff, and git could answer at all.
    """
    if not os.path.lexists(repo / LOCAL_PATH):
        return None, False
    target = _plain_file(repo, LOCAL_PATH)
    if target is None:
        return "", True
    try:
        with open(target, "rb") as handle:
            text = handle.read(1_000_000).decode("utf-8", "replace")
    except OSError:
        return "", True
    names: list[str] = list(changed)
    for args in (
        ("ls-files", "-z"),
        ("ls-tree", "-r", "--name-only", "-z", merge_base),
        ("ls-tree", "-r", "--name-only", "-z", "HEAD"),
    ):
        result = _git(repo, *args)
        if result.returncode != 0:
            return text, True
        names += result.stdout.decode("utf-8", "surrogateescape").split("\0")
    return text, any(n.lower() == LOCAL_PATH.lower() for n in names)


def _prior_manifest_problem(repo: Path, path: Path) -> str | None:
    """Why a prior manifest path may not be trusted, or None."""
    try:
        if path.is_symlink() or not path.is_file():
            return "prior manifest is not a regular file"
        resolved = path.resolve()
        if resolved == repo or repo in resolved.parents:
            return "prior manifest lies inside the repository (a PR could have committed it)"
        if hasattr(os, "getuid") and path.stat().st_uid != os.getuid():
            return "prior manifest is not owned by the current user"
    except OSError:
        return "prior manifest is missing or unreadable"
    return None


def _write_fresh(output: Path, text: str) -> None:
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


_CODEX_PATH_RE = re.compile(r"[A-Za-z0-9._/-]+\Z")


def _codex_eligible(repo: Path, path: str) -> bool:
    """Whether the Codex dispatch scripts accept this path: their charset, a regular file that
    still exists, and no symlink anywhere along it."""
    if not _CODEX_PATH_RE.match(path) or path.startswith("/") or ".." in path.split("/"):
        return False
    target = repo / path
    return target.is_file() and not _has_symlink(repo, PurePosixPath(path).parts)


def _write_diffs(diff_dir: Path, manifest: dict, file_diff: Callable[[str], bytes | None]) -> None:
    """One diff file per slice, plus a variant of it limited to Codex-eligible files. Slice names
    come from a fixed set, so no file name is built from diff content."""
    eligible = {f["path"] for f in manifest["files"] if f["codex_eligible"]}
    os.mkdir(diff_dir, 0o700)
    for s in manifest["slices"]:
        for suffix, keep in (
            (".diff", s["files"]),
            (".codex.diff", [p for p in s["files"] if p in eligible]),
        ):
            body = b"".join(file_diff(p) or b"" for p in keep)
            fd = os.open(
                diff_dir / (s["name"] + suffix), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--base-ref", default="main", help="trusted ref for settings and mirror map"
    )
    parser.add_argument("--merge-base", required=True, help="full commit SHA")
    parser.add_argument("--scope", default="")
    parser.add_argument("--exclude-dir", action="append", default=[], help="per-run folder pick")
    parser.add_argument("--recheck", action="append", default=[], help="force-include a file")
    parser.add_argument("--prior-manifest", default="")
    parser.add_argument(
        "--completed-slice",
        action="append",
        default=[],
        help="a prior-round slice whose reviewer finished (repeatable)",
    )
    parser.add_argument("--output", required=True, help="fresh path; never overwritten")
    parser.add_argument(
        "--diff-dir",
        default="",
        help="fresh directory outside the repository; receives <slice>.diff and <slice>.codex.diff",
    )
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    output = Path(args.output)
    if os.path.lexists(output):
        return _fail(f"--output {output} already exists; use a fresh file name")
    if output.parent.resolve().is_relative_to(repo):
        return _fail("--output must be outside the repository")
    diff_dir: Path | None = None
    if args.diff_dir:
        diff_dir = Path(args.diff_dir)
        if os.path.lexists(diff_dir):
            return _fail(f"--diff-dir {diff_dir} already exists; use a fresh directory name")
        if diff_dir.resolve().is_relative_to(repo):
            return _fail("--diff-dir must be outside the repository")
    if not _SHA_RE.match(args.merge_base):
        return _fail("invalid --merge-base: pass the full lowercase commit SHA")
    if args.scope.startswith(":"):
        return _fail("invalid --scope: pathspec magic (a leading ':') is not accepted")

    picks_notes: list[str] = []
    picks = _clean_entries(args.exclude_dir, "dirs", "--exclude-dir", picks_notes)
    if picks_notes:
        return _fail("; ".join(picks_notes))
    diff_args = ["diff", "--no-renames", "--ignore-submodules=none", "--name-only", "-z"]
    diff_args.append(args.merge_base)
    if args.scope:
        diff_args += ["--", args.scope]
    listing = _git(repo, *diff_args)
    if listing.returncode != 0:
        return _fail(f"git diff failed: {listing.stderr.decode('utf-8', 'replace')}")
    changed = sorted(p for p in listing.stdout.decode("utf-8", "surrogateescape").split("\0") if p)

    resolved = _git(
        repo, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{args.base_ref}^{{commit}}"
    )
    base_sha = resolved.stdout.decode().strip() if resolved.returncode == 0 else ""

    def base_text(path: str) -> str | None:
        data = _git_show_bytes(repo, base_sha, path) if _SHA_RE.match(base_sha) else None
        return None if data is None else data.decode("utf-8", "replace")

    local_text, local_untrusted = _local_config(repo, args.merge_base, changed)
    config = load_config(base_text(SETTINGS_PATH), local_text, local_untrusted)
    sync = parse_sync(base_text(SYNC_PATH))

    prior, fallback = None, None
    if args.prior_manifest:
        prior_path = Path(args.prior_manifest)
        fallback = _prior_manifest_problem(repo, prior_path)
        if fallback is None:
            try:
                with open(prior_path, "rb") as handle:
                    raw = handle.read(MAX_MANIFEST_BYTES + 1)
                if len(raw) > MAX_MANIFEST_BYTES:
                    fallback = "prior manifest is too large"
                else:
                    prior, fallback = load_prior(
                        raw.decode("utf-8"), args.merge_base, args.completed_slice
                    )
            except (OSError, UnicodeDecodeError):
                fallback = "prior manifest is missing or unreadable"
        if prior is not None and not args.completed_slice:
            config["notes"].append(
                "no --completed-slice given: files planned last round are reviewed again"
            )

    diff_cache: dict[str, bytes | None] = {}

    def file_diff(path: str) -> bytes | None:
        if path not in diff_cache:
            # A changed file's name is data: with literal pathspecs a name such as ":(glob)x" or
            # "*" selects exactly that file, not pathspec magic that matches nothing or more.
            result = _git(
                repo,
                "--literal-pathspecs",
                "diff",
                "--no-color",
                "--no-renames",
                "--ignore-submodules=none",
                "--text",
                "--no-ext-diff",
                "--no-textconv",
                args.merge_base,
                "--",
                path,
            )
            diff_cache[path] = result.stdout if result.returncode == 0 else None
        return diff_cache[path]

    def diff_size(path: str) -> int:
        data = file_diff(path)
        return -1 if data is None else len(data)

    manifest = plan_scope(
        changed,
        config,
        sync,
        read=_make_reader(repo),
        diff_size=diff_size,
        base_read=lambda path: _git_show_bytes(repo, args.merge_base, path),
        fingerprint=_make_fingerprint(repo),
        picks=picks,
        recheck=args.recheck,
        prior=prior,
        fallback=fallback,
        base=args.merge_base,
        scope=args.scope,
    )
    for entry in manifest["files"]:
        entry["codex_eligible"] = _codex_eligible(repo, entry["path"])
    try:
        if diff_dir is not None:
            _write_diffs(diff_dir, manifest, file_diff)
        _write_fresh(output, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    except OSError as err:
        return _fail(f"cannot write --output or --diff-dir: {err}")
    print(
        f"round {manifest['round']}: {len(manifest['files'])} file(s) in "
        f"{len(manifest['slices'])} slice(s), {len(manifest['excluded'])} excluded, "
        f"{len(manifest['dropped_slices'])} slice(s) dropped -> {output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
