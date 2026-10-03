#!/usr/bin/env python3
"""Validate and maintain a promptlibrary-kit prompt catalog.

Single home of the security-relevant logic the promptlibrary-kit skills rely on: catalog-root
resolution
with a path trust boundary, record validation, text hashing, secret screening, and lifecycle moves.
Every subcommand prints one JSON object on stdout and exits 0 (ok) or 1 (not ok). Standard
library only.

Usage: plib_catalog_validate.py [--root PATH] <subcommand> [args]
Subcommands: validate, show, hash, screen, init, new-id, draft, update-draft, register, discard-
orphan,
             record-verification, activate, deactivate, finalize
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SETTINGS_NAME = "promptlibrary-kit.settings.json"
LOCAL_OVERRIDE = Path(".claude") / "promptlibrary-kit.local.json"
DEFAULT_ROOT = ".claude/prompts"
MAX_NONBLANK_LINES = 50

SUPPORTED_CATALOG_VERSIONS = {1}
SUPPORTED_SCOPES = {"repo"}
STATUSES = ("draft", "active", "inactive", "historical")
ORIGINS = ("user", "claude", "codex", "session", "web")

# Field lists are selected by catalog_version so an additive change can bump the version (see
# references/prompt-record-format.md, "Extension seams").
CATALOG_FIELDS = {1: {"catalog_version", "scope", "snapshot_id", "records"}}
RECORD_REQUIRED = {
    1: ("name", "area", "slug", "internal_id", "version", "short_description", "status", "origin")
}
RECORD_OPTIONAL = {
    1: (
        "previous_id",
        "source_ref",
        "prerequisites",
        "boundaries",
        "references",
        "attachments",
        "verification",
    )
}
FIELD_ORDER = (
    "name",
    "area",
    "slug",
    "internal_id",
    "version",
    "short_description",
    "status",
    "previous_id",
    "origin",
    "source_ref",
    "prerequisites",
    "boundaries",
    "references",
    "attachments",
    "verification",
)
LIST_FIELDS = {"references", "attachments"}
MAP_FIELDS = {"source_ref", "verification"}

SLUG_PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SLUG_RE = re.compile(rf"^{SLUG_PART}__{SLUG_PART}$")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
# internal_id values that would collide with a file name the layout already uses, or that name a
# file Claude, Codex or Gemini load as instructions (the record file is <internal_id>.md, and
# CLAUDE.md is the same file as claude.md on a case-insensitive filesystem), or a Windows device.
RESERVED_IDS = {
    "active",
    "catalog",
    "claude",
    "agents",
    "gemini",
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{n}" for n in range(10)),
    *(f"lpt{n}" for n in range(10)),
}
# Origins whose text must pass the secret screen before it is filed or approved. session and web are
# imports; claude text is built from session context, which can hold secrets.
SCREENED_ORIGINS = ("session", "web", "claude")
# Folders Claude Code or git treat as configuration or instructions: a catalog root must never sit
# at or
# under one, or filed prompt text would be loaded with project-instruction authority.
FORBIDDEN_ROOTS = (
    ".git",
    ".github",
    ".claude/rules",
    ".claude/commands",
    ".claude/agents",
    ".claude/skills",
    ".claude/hooks",
    ".claude/plugins",
    ".claude/output-styles",
    ".codex",
    ".agents",
)

# Pattern shapes seeded from plugins/analysis-kit/scripts/anls_redact_secrets.py. That script
# replaces
# matches and never blocks, and a plugin installed alone cannot call another plugin's script, so
# this list
# is a deliberate duplicate: when either list changes, sweep the other (R20).
SECRET_PATTERNS = (
    ("authorization_header", re.compile(r"(?im)\bauthorization\s*[:=]\s*\S+")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    (
        "dotenv_secret_line",
        re.compile(
            r"(?im)^\s*[A-Za-z_][A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|API)[A-Za-z0-9_]*\s*=\s*\S+"
        ),
    ),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+\b")),
    ("generic_sk_token", re.compile(r"\bsk-[A-Za-z0-9-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("jwt_token", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\b")),
    ("pem_private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    # Shapes beyond the analysis-kit list: this list diverges on purpose, see the R20 note above.
    ("url_embedded_credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@")),
    (
        "key_value_secret",
        re.compile(
            r"(?i)[\"']?\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)[\"']?\s*:\s*[\"']?[^\s\"',]{6,}"
        ),
    ),
    (
        "query_string_secret",
        re.compile(
            r"(?i)[?&](?:access_token|auth_token|token|api_key|apikey|password|secret)=[^&\s]{6,}"
        ),
    ),
    ("stripe_key", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("gitlab_token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}\b")),
    (
        "home_directory_path",
        re.compile(r"(?:[A-Za-z]:[\\/]Users[\\/][^\\/\s]+|/home/[^/\s]+|/Users/[^/\s]+)"),
    ),
)


class CatalogError(Exception):
    """A condition that makes the catalog unavailable or an operation refuse."""


# ---------------------------------------------------------------- YAML subset


def _parse_scalar(raw: str):
    raw = raw.strip()
    if raw == "":
        return ""
    if raw[0] == '"':
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise CatalogError("malformed quoted value") from exc
    if raw[0] == "'" and raw[-1] == "'" and len(raw) >= 2:
        return raw[1:-1].replace("''", "'")
    if raw == "[]":
        return []
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if raw in ("true", "false"):
        return raw == "true"
    if raw in ("null", "~"):
        return None
    return raw


def parse_yaml(text: str) -> dict:
    """Parse the YAML subset this plugin writes: scalars, one-level maps, lists of scalars."""
    data: dict = {}
    key = None
    for line in text.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if indent == 0:
            m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*):\s*(.*)", body)
            if not m:
                raise CatalogError("unparseable line in frontmatter or catalog")
            key, rest = m.group(1), m.group(2)
            if key in data:
                raise CatalogError(f"duplicate key: {key}")
            data[key] = _parse_scalar(rest) if rest != "" else None
        else:
            if key is None:
                raise CatalogError("indented line before any key")
            if body.startswith("- ") or body == "-":
                if data[key] is None:
                    data[key] = []
                if not isinstance(data[key], list):
                    raise CatalogError(f"mixed list and value under {key}")
                data[key].append(_parse_scalar(body[2:]))
            else:
                m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*):\s*(.*)", body)
                if not m:
                    raise CatalogError(f"unparseable nested line under {key}")
                if data[key] is None:
                    data[key] = {}
                if not isinstance(data[key], dict):
                    raise CatalogError(f"mixed map and value under {key}")
                data[key][m.group(1)] = _parse_scalar(m.group(2))
    return data


_SAFE_PLAIN = re.compile(r"^[A-Za-z0-9_./@-][A-Za-z0-9_ ./@-]*$")


def _dump_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if (
        _SAFE_PLAIN.fullmatch(text)
        and text not in ("true", "false", "null", "~")
        and not re.fullmatch(r"-?\d+", text)
        and not text.endswith(" ")
    ):
        return text
    return json.dumps(text, ensure_ascii=False)


def dump_yaml(data: dict, order=None) -> str:
    out = []
    keys = [k for k in (order or data) if k in data] + [k for k in data if order and k not in order]
    for key in keys:
        value = data[key]
        if isinstance(value, dict):
            out.append(f"{key}:")
            out.extend(f"  {k}: {_dump_scalar(v)}" for k, v in value.items())
        elif isinstance(value, list):
            if not value:
                out.append(f"{key}: []")
            else:
                out.append(f"{key}:")
                out.extend(f"  - {_dump_scalar(v)}" for v in value)
        else:
            out.append(f"{key}: {_dump_scalar(value)}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------- records, hashes


def normalize_text(text: str) -> str:
    """LF-normalize and drop leading/trailing blank lines, so editors that differ on the final
    newline agree."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def split_record(raw: str) -> tuple[dict, str]:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    if not raw.startswith("---\n"):
        raise CatalogError("record has no frontmatter")
    end = raw.find("\n---\n", 3)
    if end == -1:
        if raw.endswith("\n---"):
            end = len(raw) - 4
        else:
            raise CatalogError("frontmatter is not closed")
    return parse_yaml(raw[4 : end + 1]), raw[end + 5 :]


def read_record(path: Path) -> dict:
    meta, body = split_record(path.read_text(encoding="utf-8"))
    meta["_body"] = normalize_text(body)
    return meta


def write_record(path: Path, meta: dict) -> None:
    clean = {k: v for k, v in meta.items() if not k.startswith("_")}
    text = "---\n" + dump_yaml(clean, FIELD_ORDER) + "---\n\n" + meta["_body"] + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def nonblank_lines(text: str) -> int:
    return sum(1 for ln in text.split("\n") if ln.strip())


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"[.!?]+(?:\s|$)", text.strip()) if s.strip()])


def hash_problems(meta: dict) -> list[str]:
    """Verification problems for a record that needs a bound approval (active/inactive, or about to
    be)."""
    problems = []
    ver = meta.get("verification")
    if not isinstance(ver, dict):
        return ["verification is missing"]
    current = text_hash(meta["_body"])
    required = ["quality"] + (["import"] if meta.get("origin") in ("session", "web") else [])
    for kind in required:
        stored = ver.get(kind)
        if not stored:
            problems.append(f"verification.{kind} is missing")
        elif not isinstance(stored, str) or not HASH_RE.fullmatch(stored):
            problems.append(f"verification.{kind} is not a SHA-256 hex digest")
        elif stored != current:
            problems.append(f"verification.{kind} does not match the current prompt text")
    for kind in ver:
        if kind not in ("quality", "import"):
            problems.append(f"unknown verification field: {kind}")
    return problems


def validate_record(meta: dict, version: int) -> list[str]:
    errs = []
    required, optional = RECORD_REQUIRED[version], RECORD_OPTIONAL[version]
    for f in required:
        if meta.get(f) in (None, ""):
            errs.append(f"missing required field: {f}")
    for f in meta:
        if not f.startswith("_") and f not in required and f not in optional:
            errs.append(f"unknown field: {f}")
    if errs:
        return errs
    for f in ("name", "area", "slug", "internal_id", "short_description"):
        if not isinstance(meta[f], str):
            errs.append(f"{f} must be text")
    if (
        not isinstance(meta["version"], int)
        or isinstance(meta["version"], bool)
        or meta["version"] < 1
    ):
        errs.append("version must be a positive integer")
    if isinstance(meta["slug"], str) and not SLUG_RE.fullmatch(meta["slug"]):
        errs.append("slug must match <kebab-area>__<kebab-name>")
    if isinstance(meta["internal_id"], str):
        if not ID_RE.fullmatch(meta["internal_id"]) or len(meta["internal_id"]) > 64:
            errs.append("internal_id must be lowercase kebab text of at most 64 characters")
        elif meta["internal_id"] in RESERVED_IDS:
            errs.append("internal_id is reserved: " + meta["internal_id"])
    if meta["status"] not in STATUSES:
        errs.append(f"status must be one of {', '.join(STATUSES)}")
    if meta["origin"] not in ORIGINS:
        errs.append(f"origin must be one of {', '.join(ORIGINS)}")
    if isinstance(meta["short_description"], str) and sentence_count(meta["short_description"]) > 3:
        errs.append("short_description must be at most three sentences")
    for f in LIST_FIELDS & set(meta):
        if not isinstance(meta[f], list) or not all(isinstance(x, str) for x in meta[f]):
            errs.append(f"{f} must be a list of text")
    for f in ("prerequisites", "boundaries"):
        if f in meta and not isinstance(meta[f], str):
            errs.append(f"{f} must be text")
    if isinstance(meta.get("version"), int) and meta["version"] > 1 and not meta.get("previous_id"):
        errs.append("a successor (version > 1) requires previous_id")
    if meta.get("previous_id") and meta.get("version") == 1:
        errs.append("version 1 must not have previous_id")
    needs_ref = meta["origin"] in ("session", "web")
    ref = meta.get("source_ref")
    if needs_ref:
        keys = ("session_id", "turns") if meta["origin"] == "session" else ("url", "retrieved_on")
        if not isinstance(ref, dict) or any(not ref.get(k) for k in keys):
            errs.append(f"source_ref requires {' and '.join(keys)} for origin {meta['origin']}")
        elif set(ref) - set(keys):
            errs.append("source_ref has unknown keys: " + ", ".join(sorted(set(ref) - set(keys))))
    elif ref is not None:
        errs.append("source_ref is only allowed for origin session or web")
    if nonblank_lines(meta["_body"]) == 0:
        errs.append("prompt_text is empty")
    elif nonblank_lines(meta["_body"]) > MAX_NONBLANK_LINES:
        errs.append(f"prompt_text exceeds {MAX_NONBLANK_LINES} nonblank lines")
    if meta["status"] in ("active", "inactive"):
        errs.extend(hash_problems(meta))
    return errs


# ------------------------------------------------------------- catalog root


def _find_git(cwd: Path) -> str | None:
    """Absolute path of git, never one that lives inside the working directory.

    On Windows a bare "git" can resolve to a git.exe sitting in the current directory (for
    example one
    shipped by a cloned repository), so the lookup result is checked against the working directory.
    """
    found = shutil.which("git")
    if found and _norm_plain(Path(found)).startswith(_norm_plain(cwd) + os.sep):
        trusted = os.pathsep.join(
            p
            for p in os.environ.get("PATH", "").split(os.pathsep)
            if p and p != os.curdir and not _norm_plain(Path(p)).startswith(_norm_plain(cwd))
        )
        found = shutil.which("git", path=trusted)
        if found and _norm_plain(Path(found)).startswith(_norm_plain(cwd) + os.sep):
            found = None
    return found


def _norm_plain(path: Path) -> str:
    return os.path.normcase(os.path.realpath(str(path)))


def _git_toplevel(cwd: Path) -> Path | None:
    git = _find_git(cwd)
    if not git:
        return None
    try:
        out = subprocess.run(
            [git, "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = out.stdout.strip()
    return Path(top) if out.returncode == 0 and top else None


def _is_tracked(project_root: Path, rel: Path) -> bool:
    """True when git tracks rel. Fails closed: any doubt counts as tracked, so the override is
    ignored. Only git's exit code 1 (the path is not known to git) counts as untracked; any other
    failure, such as a corrupt index or an ownership error, is doubt."""
    git = _find_git(project_root)
    if not git:
        return True
    try:
        out = subprocess.run(
            [git, "ls-files", "--error-unmatch", "--", rel.as_posix()],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return True
    return out.returncode != 1


def _case_insensitive(directory: Path) -> bool:
    # Compare strings: Path.__eq__ is itself case-insensitive on Windows and would hide the
    # difference.
    swapped = str(directory).swapcase()
    try:
        return (
            swapped != str(directory)
            and os.path.exists(swapped)
            and os.path.samefile(swapped, str(directory))
        )
    except OSError:
        return False


def _norm(path: Path, fold: bool) -> str:
    text = os.path.normcase(os.path.realpath(str(path)))
    return text.casefold() if fold else text


def contained(child: Path, parent: Path) -> bool:
    """True when child resolves strictly inside parent (resolved paths, never string prefixes)."""
    fold = _case_insensitive(parent)
    c, p = _norm(child, fold), _norm(parent, fold)
    if c == p:
        return False
    try:
        return os.path.commonpath([c, p]) == p
    except ValueError:  # different drives
        return False


def check_catalog_path(value, project_root: Path) -> tuple[Path | None, str | None]:
    """Return (resolved catalog root, None) or (None, reason) for a candidate path value."""
    if not isinstance(value, str) or not value.strip():
        return None, "path is empty or not text"
    if "\x00" in value:
        return None, "path contains a NUL byte"
    text = value.strip()
    # Normalize separators first: "/\srv\x" and "\/srv\x" are UNC on Windows even though they do
    # not start
    # with a doubled backslash, and resolving them can open a network connection before
    # containment fails.
    if text.replace("/", "\\").startswith("\\\\"):
        return None, "UNC paths are not allowed"
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    if not contained(candidate, project_root):
        return None, "resolves outside the project root"
    fold = _case_insensitive(project_root)
    for forbidden in FORBIDDEN_ROOTS:
        target = project_root / forbidden
        if _norm(candidate, fold) == _norm(target, fold) or contained(candidate, target):
            return None, f"resolves inside {forbidden}, which holds configuration or instructions"
    return Path(os.path.realpath(str(candidate))), None


def _settings_dir() -> Path:
    # <dir>/scripts/this_file.py with <dir>/promptlibrary-kit.settings.json beside scripts/ — true
    # for the
    # plugin root and for the hand-copied twin under .claude/ (see README).
    return Path(__file__).resolve().parent.parent


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def resolve_root(cli_root: str | None, cwd: Path | None = None) -> dict:
    cwd = cwd or Path.cwd()
    top = _git_toplevel(cwd)
    project_root = top if top else cwd
    info = {
        "project_root": str(project_root),
        "project_root_source": "git" if top else "cwd",
        "warnings": [],
    }
    if not top:
        info["warnings"].append(
            "not inside a git repository; using the working directory as the project root"
        )
    default_value = DEFAULT_ROOT
    defaults = _read_json(_settings_dir() / SETTINGS_NAME)
    if isinstance(defaults, dict) and isinstance(defaults.get("catalog_root"), str):
        default_value = defaults["catalog_root"]
    candidates = []
    if cli_root:
        candidates.append(("--root", cli_root))
    local = project_root / LOCAL_OVERRIDE
    if local.is_file():
        if not top:
            info["warnings"].append(
                f"{LOCAL_OVERRIDE.as_posix()} cannot be checked against git here; its path value "
                "is ignored"
            )
        elif _is_tracked(project_root, LOCAL_OVERRIDE):
            info["warnings"].append(
                f"{LOCAL_OVERRIDE.as_posix()} is tracked by git; its path value is ignored"
            )
        else:
            data = _read_json(local)
            if isinstance(data, dict) and "catalog_root" in data:
                candidates.append(("local override", data["catalog_root"]))
            else:
                info["warnings"].append(
                    f"{LOCAL_OVERRIDE.as_posix()} is unreadable or has no catalog_root"
                )
    candidates.append(("default", default_value))
    for source, value in candidates:
        resolved, reason = check_catalog_path(value, project_root)
        if resolved is not None:
            info.update(catalog_root=str(resolved), root_source=source)
            return info
        info["warnings"].append(f"{source} catalog path rejected ({reason}); falling back")
    raise CatalogError("no usable catalog root: " + "; ".join(info["warnings"]))


# ------------------------------------------------------------ catalog loading


def load_catalog(root: Path) -> tuple[dict, dict, list[str]]:
    """Return (catalog meta, {relpath: record}, errors). Never raises for content problems."""
    errs: list[str] = []
    cat_path = root / "catalog.yaml"
    if not cat_path.is_file():
        return {}, {}, ["catalog.yaml is missing"]
    try:
        cat = parse_yaml(cat_path.read_text(encoding="utf-8"))
    except CatalogError as exc:
        return {}, {}, [f"catalog.yaml: {exc}"]
    version = cat.get("catalog_version")
    if version not in SUPPORTED_CATALOG_VERSIONS:
        return cat, {}, [f"unsupported catalog_version: {version!r}"]
    if cat.get("scope") not in SUPPORTED_SCOPES:
        errs.append(f"unsupported scope: {cat.get('scope')!r}")
    for f in cat:
        if f not in CATALOG_FIELDS[version]:
            errs.append(f"catalog.yaml: unknown field: {f}")
    if not isinstance(cat.get("snapshot_id"), str) or not cat.get("snapshot_id"):
        errs.append("catalog.yaml: snapshot_id is missing")
    listed = cat.get("records")
    if listed is None:
        listed = []
    if not isinstance(listed, list) or not all(isinstance(x, str) for x in listed):
        return cat, {}, errs + ["catalog.yaml: records must be a list of paths"]
    records: dict = {}
    for rel in listed:
        parts = rel.replace("\\", "/").split("/")
        if rel.startswith("/") or ".." in parts or len(parts) != 2 or not parts[1].endswith(".md"):
            errs.append(f"invalid record path: {rel}")
            continue
        if rel in records:
            errs.append(f"record listed twice: {rel}")
            continue
        path = root / parts[0] / parts[1]
        if not contained(path, root):
            errs.append(f"record path escapes the catalog root: {rel}")
            continue
        if not path.is_file():
            errs.append(f"listed record is missing: {rel}")
            continue
        try:
            meta = read_record(path)
        except (CatalogError, OSError, UnicodeDecodeError) as exc:
            errs.append(f"{rel}: {exc}")
            continue
        meta["_path"] = rel
        problems = validate_record(meta, version)
        errs.extend(f"{rel}: {p}" for p in problems)
        records[rel] = meta
    errs.extend(check_lineages(root, records))
    return cat, records, errs


def check_lineages(root: Path, records: dict) -> list[str]:
    errs = []
    by_id: dict = {}
    by_slug: dict = {}
    for rel, meta in records.items():
        if not isinstance(meta.get("internal_id"), str) or not isinstance(meta.get("slug"), str):
            continue
        rel_dir, _, fname = rel.partition("/")
        if meta["slug"] != rel_dir:
            errs.append(f"{rel}: slug does not match its directory")
        expected = "active.md" if meta.get("status") == "active" else f"{meta['internal_id']}.md"
        if fname != expected:
            errs.append(
                f"{rel}: expected path {rel_dir}/{expected} for status {meta.get('status')}"
            )
        if meta["internal_id"] in by_id:
            errs.append(f"{rel}: duplicate internal_id {meta['internal_id']}")
        by_id[meta["internal_id"]] = meta
        by_slug.setdefault(meta["slug"], []).append(meta)
    for slug, group in by_slug.items():
        if sum(1 for m in group if m.get("status") == "active") > 1:
            errs.append(f"{slug}: more than one active record")
        versions = sorted(m["version"] for m in group if isinstance(m.get("version"), int))
        if versions != list(range(1, len(versions) + 1)):
            errs.append(f"{slug}: version numbers are not contiguous from 1")
        for m in group:
            prev = m.get("previous_id")
            if prev:
                target = by_id.get(prev)
                if target is None or target.get("slug") != slug:
                    errs.append(f"{m['_path']}: previous_id {prev} not found in the same lineage")
                elif target.get("version") != m.get("version", 0) - 1:
                    errs.append(
                        f"{m['_path']}: previous_id is not the immediately preceding version"
                    )
    listed = set(records)
    for entry in sorted(root.iterdir()) if root.is_dir() else []:
        if entry.is_dir():
            for f in sorted(entry.glob("*.md")):
                rel = f"{entry.name}/{f.name}"
                if rel not in listed:
                    errs.append(f"unlisted record file on disk: {rel}")
    return errs


def summarize(meta: dict) -> dict:
    return {
        "slug": meta.get("slug"),
        "internal_id": meta.get("internal_id"),
        "version": meta.get("version"),
        "status": meta.get("status"),
        "origin": meta.get("origin"),
        "name": meta.get("name"),
        "area": meta.get("area"),
        "short_description": meta.get("short_description"),
        "verified": not hash_problems(meta),
    }


# ------------------------------------------------------------------ commands


def _load(args) -> tuple[dict, Path, dict, dict]:
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    cat, records, errs = load_catalog(root)
    info["errors"] = errs
    return info, root, cat, records


def _need_ok(info: dict) -> None:
    if info["errors"]:
        raise CatalogError("catalog is not valid: " + "; ".join(info["errors"][:3]))


def cmd_validate(args) -> dict:
    info, _, cat, records = _load(args)
    info["ok"] = not info["errors"]
    info["catalog_version"] = cat.get("catalog_version")
    info["records"] = [summarize(m) for m in records.values()]
    return info


def cmd_show(args) -> dict:
    info, _, _, records = _load(args)
    _need_ok(info)
    group = sorted(
        (m for m in records.values() if m["slug"] == args.slug), key=lambda m: m["version"]
    )
    if not group:
        raise CatalogError(f"no such slug: {args.slug}")
    if args.history:
        shown = group
    else:
        shown = [m for m in group if m["status"] == "active"]
        if not shown:
            raise CatalogError(
                f"{args.slug} has no active record (use --history to list its lineage)"
            )
    info["ok"] = True
    info["records"] = [
        {
            **summarize(m),
            "previous_id": m.get("previous_id"),
            "prerequisites": m.get("prerequisites"),
            "boundaries": m.get("boundaries"),
            "references": m.get("references"),
            "source_ref": m.get("source_ref"),
            "prompt_text": m["_body"],
            "text_hash": text_hash(m["_body"]),
        }
        for m in shown
    ]
    return info


MAX_INPUT_BYTES = 262144


def _inside(root: Path, path: Path) -> Path:
    """Re-check containment right before a write: a directory can be swapped for a link after load
    time."""
    if not contained(path, root):
        raise CatalogError(f"path escapes the catalog root: {path.name}")
    return path


def _readable_candidate(path_text: str, root: Path) -> Path:
    """A file the hash/screen/draft commands may read: inside the catalog root or the system temp
    directory."""
    path = Path(path_text)
    if not path.is_file():
        raise CatalogError(f"not a file: {path_text}")
    allowed = [a for a in (root, Path(tempfile.gettempdir())) if a.exists()]
    if not any(contained(path, a) for a in allowed):
        raise CatalogError("the file must be inside the catalog root or the system temp directory")
    resolved = Path(os.path.realpath(str(path)))
    if resolved.stat().st_size > MAX_INPUT_BYTES:
        raise CatalogError("the file is too large")
    return resolved


def cmd_hash(args) -> dict:
    info = resolve_root(getattr(args, "root", None))
    path = _readable_candidate(args.file, Path(info["catalog_root"]))
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CatalogError(f"cannot read {args.file}: {exc}") from exc
    body = split_record(raw)[1] if raw.replace("\r\n", "\n").startswith("---\n") else raw
    return {
        "ok": True,
        "sha256": text_hash(body),
        "nonblank_lines": nonblank_lines(normalize_text(body)),
    }


def screen_text(text: str) -> list[dict]:
    """Return {line, pattern} for each match. The matched text is never echoed."""
    found = []
    for lineno, line in enumerate(text.replace("\r\n", "\n").split("\n"), start=1):
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                found.append({"line": lineno, "pattern": name})
    return found


def screen_blob(meta: dict) -> str:
    """Body plus every text-valued metadata field.

    A secret cannot hide outside the prompt text.
    """
    parts = [meta.get("_body", "")]
    for key in ("name", "area", "short_description", "prerequisites", "boundaries"):
        if isinstance(meta.get(key), str):
            parts.append(meta[key])
    for key in ("references", "attachments"):
        if isinstance(meta.get(key), list):
            parts.extend(x for x in meta[key] if isinstance(x, str))
    if isinstance(meta.get("source_ref"), dict):
        parts.extend(str(v) for v in meta["source_ref"].values())
    return "\n".join(parts)


def _assert_clean(meta: dict) -> None:
    """Enforce detect-and-block for imported text (session, web), not just in the skill's step
    order."""
    if meta.get("origin") in SCREENED_ORIGINS:
        hits = screen_text(screen_blob(meta))
        if hits:
            names = ", ".join(sorted({h["pattern"] for h in hits}))
            raise CatalogError(
                f"possible secret or personal data found ({names}); remove it and try again"
            )


def _check_expected(meta: dict, expected: str) -> None:
    if text_hash(meta["_body"]) != (expected or "").strip().lower():
        raise CatalogError(
            "the prompt text changed since it was approved (--expect-sha256 does not match)"
        )


def cmd_screen(args) -> dict:
    try:
        if args.file == "-":
            text = sys.stdin.read(MAX_INPUT_BYTES + 1)
            if len(text) > MAX_INPUT_BYTES:
                raise CatalogError("the input is too large")
        else:
            info = resolve_root(getattr(args, "root", None))
            path = _readable_candidate(args.file, Path(info["catalog_root"]))
            text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CatalogError(f"cannot read {args.file}: {exc}") from exc
    matches = screen_text(text)
    return {
        "ok": not matches,
        "matches": matches,
        "note": "detect-and-block only: nothing was rewritten and no matched text is shown; "
        "the user removes each match"
        if matches
        else "",
    }


def new_snapshot_id() -> str:
    return hashlib.sha256(os.urandom(16)).hexdigest()[:12]


def write_catalog(root: Path, cat: dict, record_paths: list[str]) -> None:
    out = {
        "catalog_version": cat.get("catalog_version", 1),
        "scope": cat.get("scope", "repo"),
        "snapshot_id": new_snapshot_id(),
        "records": sorted(record_paths),
    }
    target = _inside(root, root / "catalog.yaml")
    target.write_text(
        dump_yaml(out, ("catalog_version", "scope", "snapshot_id", "records")),
        encoding="utf-8",
        newline="\n",
    )


def cmd_init(args) -> dict:
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    if (root / "catalog.yaml").exists():
        raise CatalogError("catalog.yaml already exists")
    root.mkdir(parents=True, exist_ok=True)
    write_catalog(root, {}, [])
    info["ok"] = True
    return info


def cmd_new_id(args) -> dict:
    info, _, _, records = _load(args)
    taken = {m["internal_id"] for m in records.values() if isinstance(m.get("internal_id"), str)}
    while True:
        candidate = "p" + hashlib.sha256(os.urandom(16)).hexdigest()[:12]
        if candidate not in taken:
            return {"ok": True, "internal_id": candidate}


def _record_by_id(records: dict, ident: str) -> dict:
    for m in records.values():
        if m["internal_id"] == ident:
            return m
    raise CatalogError(f"no record with internal_id {ident}")


def _check_new_draft(meta: dict, records: dict) -> list[str]:
    errs = []
    if any(m["internal_id"] == meta["internal_id"] for m in records.values()):
        errs.append("duplicate internal_id")
    group = [m for m in records.values() if m["slug"] == meta["slug"]]
    if meta["version"] == 1:
        if group:
            errs.append("the slug is already used by another lineage")
    else:
        pred = next((m for m in group if m["internal_id"] == meta.get("previous_id")), None)
        if pred is None:
            errs.append("previous_id is not in this slug's lineage")
        else:
            if pred["status"] not in ("active", "inactive"):
                errs.append("the predecessor must be active or inactive")
            if meta["version"] != pred["version"] + 1:
                errs.append("version must follow the predecessor's version")
        if any(m["version"] >= meta["version"] for m in group):
            errs.append("a record with this version or a later one already exists")
    return errs


def _valid_catalog(root: Path):
    cat, records, errs = load_catalog(root)
    if errs:
        raise CatalogError("catalog is not valid: " + "; ".join(errs[:3]))
    return cat, records


def _scratch_record(path_text: str, root: Path) -> dict:
    path = _readable_candidate(path_text, root)
    try:
        meta = read_record(path)
    except (CatalogError, OSError, UnicodeDecodeError) as exc:
        raise CatalogError(f"cannot read the draft file: {exc}") from exc
    errs = validate_record(meta, 1)
    if meta.get("status") != "draft":
        errs.append("only a draft record can be added or updated here")
    if errs:
        raise CatalogError("; ".join(errs[:4]))
    meta.pop("verification", None)  # a new or changed draft starts unverified
    _assert_clean(meta)
    return meta


def cmd_draft(args) -> dict:
    """Add a new draft from a scratch file: validate, screen, write the record, then list it in
    catalog.yaml."""
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    cat, records = _valid_catalog(root)
    meta = _scratch_record(args.file, root)
    errs = _check_new_draft(meta, records)
    if errs:
        raise CatalogError("; ".join(errs))
    rel = f"{meta['slug']}/{meta['internal_id']}.md"
    target = _inside(root, root / meta["slug"] / f"{meta['internal_id']}.md")
    if target.exists():
        raise CatalogError(f"{rel} already exists")
    target.parent.mkdir(exist_ok=True)
    write_record(target, meta)
    try:
        write_catalog(root, cat, [m["_path"] for m in records.values()] + [rel])
    except (OSError, CatalogError):
        target.unlink(missing_ok=True)  # no orphan record file is left behind
        raise
    info.update(
        ok=True, internal_id=meta["internal_id"], path=rel, text_hash=text_hash(meta["_body"])
    )
    return info


def cmd_update_draft(args) -> dict:
    """Replace an existing draft's content from a scratch file (an approved rewrite or an in-place
    edit)."""
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    _, records = _valid_catalog(root)
    current = _record_by_id(records, args.internal_id)
    if current["status"] != "draft":
        raise CatalogError(
            "only a draft can be updated in place; revise an active or inactive record instead"
        )
    meta = _scratch_record(args.file, root)
    for field in ("internal_id", "slug", "version", "previous_id", "origin", "source_ref"):
        if meta.get(field) != current.get(field):
            raise CatalogError(f"{field} cannot change when updating a draft")
    if text_hash(meta["_body"]) == text_hash(current["_body"]) and current.get("verification"):
        meta["verification"] = current["verification"]
    write_record(_inside(root, root / current["_path"]), meta)
    info.update(ok=True, internal_id=meta["internal_id"], text_hash=text_hash(meta["_body"]))
    return info


def cmd_register(args) -> dict:
    """List an existing, unlisted draft file (path relative to the catalog root) in catalog.yaml."""
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    cat, records, errs = load_catalog(root)
    rel = args.path.replace("\\", "/")
    unlisted = f"unlisted record file on disk: {rel}"
    other = [e for e in errs if e != unlisted]
    if other:
        raise CatalogError("catalog is not valid: " + "; ".join(other[:3]))
    if unlisted not in errs:
        raise CatalogError(f"{rel} is not an unlisted record file")
    parts = rel.split("/")
    path = _inside(root, root / parts[0] / parts[1])
    meta = read_record(path)
    problems = validate_record(meta, cat.get("catalog_version", 1))
    if meta.get("status") != "draft":
        problems.append("only a draft record can be registered")
    elif parts[1] != f"{meta['internal_id']}.md" or parts[0] != meta["slug"]:
        problems.append(f"a draft must be stored as {meta['slug']}/{meta['internal_id']}.md")
    problems.extend(_check_new_draft(meta, records))
    if problems:
        raise CatalogError("; ".join(problems[:4]))
    _assert_clean(meta)
    if (
        meta.pop("verification", None) is not None
    ):  # verification is recorded by record-verification only
        write_record(path, meta)
    write_catalog(root, cat, [m["_path"] for m in records.values()] + [rel])
    info["ok"] = True
    return info


def cmd_discard_orphan(args) -> dict:
    """Delete one unlisted record file.

    An interrupted draft then does not block the catalog for good.
    """
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    _, _, errs = load_catalog(root)
    rel = args.path.replace("\\", "/")
    if f"unlisted record file on disk: {rel}" not in errs:
        raise CatalogError(f"{rel} is not an unlisted record file")
    parts = rel.split("/")
    path = _inside(root, root / parts[0] / parts[1])
    try:
        meta = read_record(path)
    except (CatalogError, OSError, UnicodeDecodeError):
        meta = {}
    if meta.get("status") != "draft":
        raise CatalogError(
            "only an unlisted draft can be discarded; this file is not a readable draft"
        )
    path.unlink()
    info["ok"] = True
    info["removed"] = rel
    info["slug"] = meta.get("slug")
    info["internal_id"] = meta.get("internal_id")
    return info


def cmd_record_verification(args) -> dict:
    info, root, cat, records = _load(args)
    _need_ok(info)
    meta = _record_by_id(records, args.internal_id)
    if meta["status"] != "draft":
        raise CatalogError("verification is recorded only on a draft (editing a draft clears it)")
    if args.kind == "import" and meta["origin"] not in ("session", "web"):
        raise CatalogError("an import hash is only recorded for session or web origin")
    _check_expected(meta, args.expect_sha256)
    _assert_clean(meta)
    ver = dict(meta.get("verification") or {})
    ver[args.kind] = text_hash(meta["_body"])
    meta["verification"] = ver
    write_record(_inside(root, root / meta["_path"]), meta)
    info["ok"] = True
    info["recorded"] = {args.kind: ver[args.kind]}
    return info


def _move(root: Path, meta: dict, new_status: str, paths: list[str]) -> None:
    old_rel = meta["_path"]
    new_name = "active.md" if new_status == "active" else f"{meta['internal_id']}.md"
    new_rel = f"{meta['slug']}/{new_name}"
    old_path, new_path = _inside(root, root / old_rel), _inside(root, root / new_rel)
    meta["status"] = new_status
    write_record(old_path, meta)
    if new_rel != old_rel:
        old_path.replace(new_path)
        paths[paths.index(old_rel)] = new_rel
        meta["_path"] = new_rel


def _lifecycle(args, op: str) -> dict:
    info, root, cat, records = _load(args)
    _need_ok(info)
    paths = [m["_path"] for m in records.values()]
    meta = _record_by_id(records, args.internal_id)
    group = [m for m in records.values() if m["slug"] == meta["slug"]]
    active = next((m for m in group if m["status"] == "active"), None)
    if op == "deactivate":
        if meta["status"] != "active":
            raise CatalogError("only an active record can be deactivated")
        _move(root, meta, "inactive", paths)
    elif op == "activate":
        if meta["status"] not in ("draft", "inactive"):
            raise CatalogError("only a draft or inactive record can be activated")
        if meta.get("previous_id") and meta["status"] == "draft":
            raise CatalogError("a successor is activated with finalize, not activate")
        if active is not None:
            raise CatalogError(f"{meta['slug']} already has an active record")
        _check_expected(meta, args.expect_sha256)
        _assert_clean(meta)
        problems = hash_problems(meta)
        if problems:
            raise CatalogError("not verified: " + "; ".join(problems))
        _move(root, meta, "active", paths)
    else:  # finalize
        if meta["status"] != "draft" or not meta.get("previous_id"):
            raise CatalogError("finalize applies to a draft successor (one with previous_id)")
        _check_expected(meta, args.expect_sha256)
        _assert_clean(meta)
        problems = hash_problems(meta)
        if problems:
            raise CatalogError("not verified: " + "; ".join(problems))
        pred = _record_by_id(records, meta["previous_id"])
        if pred["status"] not in ("active", "inactive"):
            raise CatalogError("the predecessor is neither active nor inactive")
        if pred["status"] == "inactive" and not args.active and not args.inactive:
            raise CatalogError("predecessor is inactive: pass --active or --inactive to choose")
        goes_active = args.active or (pred["status"] == "active" and not args.inactive)
        _move(root, pred, "historical", paths)
        _move(root, meta, "active" if goes_active else "inactive", paths)
    write_catalog(root, cat, paths)  # catalog.yaml last, after every record move succeeded
    info["ok"] = True
    info["status"] = meta["status"]
    return info


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--root", help="catalog root override (validated by the same path trust boundary)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    s = sub.add_parser("show")
    s.add_argument("slug")
    s.add_argument("--history", action="store_true")
    h = sub.add_parser("hash")
    h.add_argument("file", help="a file inside the catalog root or the system temp directory")
    sc = sub.add_parser("screen")
    sc.add_argument(
        "file", help="a file inside the catalog root or the system temp directory, or - for stdin"
    )
    sub.add_parser("init")
    sub.add_parser("new-id")
    d = sub.add_parser("draft")
    d.add_argument("file", help="scratch file holding the full draft record (frontmatter and body)")
    ud = sub.add_parser("update-draft")
    ud.add_argument("internal_id")
    ud.add_argument("file", help="scratch file holding the full replacement record")
    r = sub.add_parser("register")
    r.add_argument(
        "path", help="record path relative to the catalog root, e.g. <slug>/<internal_id>.md"
    )
    o = sub.add_parser("discard-orphan")
    o.add_argument("path", help="unlisted record path relative to the catalog root")
    rv = sub.add_parser("record-verification")
    rv.add_argument("internal_id")
    rv.add_argument("--kind", choices=("quality", "import"), required=True)
    rv.add_argument(
        "--expect-sha256", required=True, help="the hash shown to the user when they approved"
    )
    sub.add_parser("deactivate").add_argument("internal_id")
    a = sub.add_parser("activate")
    a.add_argument("internal_id")
    a.add_argument("--expect-sha256", required=True)
    f = sub.add_parser("finalize")
    f.add_argument("internal_id")
    f.add_argument("--expect-sha256", required=True)
    choice = f.add_mutually_exclusive_group()
    choice.add_argument("--active", action="store_true")
    choice.add_argument("--inactive", action="store_true")
    return p


COMMANDS = {
    "validate": cmd_validate,
    "show": cmd_show,
    "hash": cmd_hash,
    "screen": cmd_screen,
    "init": cmd_init,
    "new-id": cmd_new_id,
    "draft": cmd_draft,
    "update-draft": cmd_update_draft,
    "register": cmd_register,
    "discard-orphan": cmd_discard_orphan,
    "record-verification": cmd_record_verification,
    "activate": lambda a: _lifecycle(a, "activate"),
    "deactivate": lambda a: _lifecycle(a, "deactivate"),
    "finalize": lambda a: _lifecycle(a, "finalize"),
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = COMMANDS[args.cmd](args)
    except CatalogError as exc:
        result = {"ok": False, "error": str(exc)}
    except OSError as exc:
        result = {"ok": False, "error": f"filesystem error: {exc}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
