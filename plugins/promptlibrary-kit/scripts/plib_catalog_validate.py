#!/usr/bin/env python3
"""Validate and maintain a promptlibrary-kit prompt catalog.

Single home of the security-relevant logic the promptlibrary-kit skills rely on: catalog-root
resolution
with a path trust boundary, record validation, text hashing, secret screening, and lifecycle moves.
Every subcommand prints one JSON object on stdout and exits 0 (ok) or 1 (not ok). Standard
library only.

Usage: plib_catalog_validate.py [--root PATH] <subcommand> [args]
Subcommands: validate, show, review-bundle, hash, screen, init, new-id, draft, update-draft,
             register, discard-orphan, discard-draft, record-verification, activate,
             deactivate, finalize, retire, upgrade
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404 - git runs with fixed argument lists, no shell
import sys
import tempfile
import unicodedata
from collections.abc import Callable
from pathlib import Path

SETTINGS_NAME = "promptlibrary-kit.settings.json"
LOCAL_OVERRIDE = Path(".claude") / "promptlibrary-kit.local.json"
DEFAULT_ROOT = ".claude/prompts"
MAX_NONBLANK_LINES = 50

SUPPORTED_CATALOG_VERSIONS = {1, 2, 3}
# Version 3 binds origin and attached files into the approval fingerprint (SEC-4, CAT-2).
CURRENT_CATALOG_VERSION = 3
SUPPORTED_SCOPES = {"repo"}
ATTACHMENT_LIMITS_KB = (16, 32, 64)
DEFAULT_ATTACHMENT_KB = 32
FINGERPRINT_TAG = "promptlibrary-kit fingerprint 3"
STATUSES = ("draft", "active", "inactive", "historical")
ORIGINS = ("user", "claude", "codex", "session", "web")

# Field lists are selected by catalog_version so an additive change can bump the version (see
# references/prompt-record-format.md, "Extension seams").
# Version 2 only adds reserved_slugs to catalog.yaml: slugs whose first draft was discarded.
CATALOG_FIELDS = {
    1: {"catalog_version", "scope", "snapshot_id", "records"},
    2: {"catalog_version", "scope", "snapshot_id", "records", "reserved_slugs"},
}
CATALOG_FIELDS[3] = CATALOG_FIELDS[2]
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
RECORD_REQUIRED[2], RECORD_OPTIONAL[2] = RECORD_REQUIRED[1], RECORD_OPTIONAL[1]
RECORD_REQUIRED[3], RECORD_OPTIONAL[3] = RECORD_REQUIRED[1], RECORD_OPTIONAL[1]
# Version 3 adds verification.core: the hash of text and origin alone, so a blocked prompt can tell
# a changed attachment (revisable, CAT-6) from a changed text or origin (restore or retire only).
VERIFICATION_KEYS = {1: ("quality", "import"), 2: ("quality", "import")}
VERIFICATION_KEYS[3] = ("quality", "import", "core")
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
# imports; claude and codex text is built from session context, which can hold secrets. Only user
# text is warn-only, because a person's own prompt may legitimately contain a path or example.
SCREENED_ORIGINS = ("session", "web", "claude", "codex")
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


def _load_token_shapes(path: Path | None = None) -> list[tuple[str, re.Pattern]]:
    """Prefix-based token shapes, shared with the other redactors through one canonical file.

    plib-token-shapes.json is a byte-identical copy of scripts/marketplace_ci/token_shapes.json;
    edit that file and run `python -m scripts.marketplace_ci sync-token-shapes`, never this copy.
    Compiled with re.ASCII so a word boundary behaves like the JavaScript redactor's (the default
    Unicode boundary missed a token next to an accented or CJK character). A missing or malformed
    file raises at import: a screen that silently matches nothing would let a secret through.
    """
    document = json.loads(
        (path or Path(__file__).with_name("plib-token-shapes.json")).read_text("utf-8")
    )
    valid = (
        isinstance(document, dict)
        and document.get("version") == 1
        and isinstance(document.get("shapes"), list)
        and bool(document["shapes"])
        and all(
            isinstance(shape, dict)
            and isinstance(shape.get("name"), str)
            and isinstance(shape.get("pattern"), str)
            and shape["pattern"]
            for shape in document["shapes"]
        )
    )
    if not valid:
        raise ValueError(
            "plib-token-shapes.json: expected version 1 and a non-empty list of name/pattern shapes"
        )
    return [(shape["name"], re.compile(shape["pattern"], re.ASCII)) for shape in document["shapes"]]


_TOKEN_SHAPES = _load_token_shapes()

# The token shapes above are shared; the other rules were seeded from
# plugins/analysis-kit/scripts/anls_redact_secrets.py. That script replaces matches and never
# blocks, and a plugin installed alone cannot call another plugin's script, so the remaining
# rules are a deliberate duplicate: when either list changes, sweep the other (R20).
SECRET_PATTERNS = (
    ("authorization_header", re.compile(r"(?im)\bauthorization\s*[:=]\s*\S+")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    (
        # A bare PASSWORD=..., TOKEN=... or export KEY=... line counts, not only a longer
        # identifier, and the identifier may be any length. The lookahead finds the credential word
        # inside the identifier run, then one pass consumes the run: two linear scans per line, no
        # nested repetition around the word, so a long line of repeated keywords stays fast. The
        # padding is any whitespace except a newline ([^\S\r\n], so a no-break space or form feed
        # still counts), never \s, so a run of blank lines cannot make the match quadratic.
        "dotenv_secret_line",
        re.compile(
            r"(?im)^[^\S\r\n]*(?:export[^\S\r\n]+)?(?=[A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|API))"
            r"[A-Za-z0-9_]+[^\S\r\n]*=[^\S\r\n]*\S+"
        ),
    ),
    *_TOKEN_SHAPES,
    ("pem_private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")),
    # Shapes beyond the analysis-kit list: this list diverges on purpose, see the R20 note above.
    ("url_embedded_credentials", re.compile(r"(?i)\b[a-z][a-z0-9+.-]{0,30}://[^/\s:@]*:[^/\s@]+@")),
    (
        "key_value_secret",
        re.compile(
            r"(?i)[\"']?\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)[\"']?\s*[:=]\s*[\"']?[^\s\"',]{6,}"
        ),
    ),
    (
        # A credential name anywhere in a line, in either = or : form: DB_PASSWORD, client_secret,
        # AWS_SECRET_ACCESS_KEY. A bare "token:" or "primary_key:" is ordinary prose and stays out.
        # The lookbehind starts one attempt per identifier run, so a long run stays linear.
        "prefixed_credential",
        re.compile(
            r"(?i)(?<![a-z0-9_-])(?:[a-z0-9_-]*[_-](?:password|passwd|pwd|secret|token)"
            r"|(?:[a-z0-9_-]*[_-])?(?:api|access|account|auth|encryption|private|secret|signing)"
            r"[_-]key)[\"']?[^\S\r\n]*(?::=|[:=])[^\S\r\n]*[\"']?[^\s\"',]{6,}"
        ),
    ),
    (
        "query_string_secret",
        re.compile(
            r"(?i)[?&](?:access_token|auth_token|token|api_key|apikey|password|secret)=[^&\s]{6,}"
        ),
    ),
    # re.ASCII for the same reason as the shared shapes: a Unicode \b misses a token next to an
    # accented or CJK character. No trailing \b: a token followed by `_` must still match.
    ("stripe_key", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}", re.ASCII)),
    ("gitlab_token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}", re.ASCII)),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}", re.ASCII)),
    (
        "home_directory_path",
        re.compile(r"(?:[A-Za-z]:[\\/]{1,4}Users[\\/]{1,4}[^\\/\s]+|/home/[^/\s]+|/Users/[^/\s]+)"),
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
                if m.group(1) in data[key]:
                    raise CatalogError(f"duplicate key: {key}.{m.group(1)}")
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


MAX_HIDDEN_REPORTED = 50
# Format (zero-width, bidi, tags), control, private-use, unassigned, line/paragraph separators.
HIDDEN_CATEGORIES = frozenset({"Cf", "Cc", "Co", "Cn", "Zl", "Zp"})
# Letters and marks that render blank or not at all: Hangul fillers, the braille blank, and the
# default-ignorable combining marks (grapheme joiner, Khmer inherent vowels, Mongolian free
# variation selectors), which are category Mn like a visible accent.
HIDDEN_EXTRA = frozenset(
    {0x034F, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180B, 0x180C, 0x180D, 0x180F, 0x2800, 0x3164, 0xFFA0}
)


def _is_hidden(ch: str) -> bool:
    cp = ord(ch)
    if ch == "\t":
        return False
    if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:  # variation selectors
        return True
    category = unicodedata.category(ch)
    if category == "Zs":  # a space that is not the ASCII one renders like it but is not it
        return ch != " "
    return cp in HIDDEN_EXTRA or category in HIDDEN_CATEGORIES


def hidden_characters(text: str) -> tuple[list[dict], bool]:
    """Characters a rendered preview does not show or shows as something else (format and control
    characters, variation selectors, private-use or unassigned code points, separators, non-ASCII
    spaces, blank-looking letters, invisible combining marks), by 1-based line, 1-based column and
    code point, plus whether the list was cut at MAX_HIDDEN_REPORTED. The user
    may otherwise approve text that reads differently from what runs. Reported, not rejected: an
    emoji joiner or variation selector is legitimate."""
    found = []
    for lineno, line in enumerate(normalize_text(text).split("\n"), start=1):
        for column, ch in enumerate(line, start=1):
            if _is_hidden(ch):
                if len(found) >= MAX_HIDDEN_REPORTED:
                    return found, True
                found.append(
                    {
                        "line": lineno,
                        "column": column,
                        "codepoint": f"U+{ord(ch):04X}",
                        "name": unicodedata.name(ch, "UNNAMED CHARACTER"),
                    }
                )
    return found, False


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _tagged_hash(payload: dict) -> str:
    data = json.dumps({"tag": FINGERPRINT_TAG, **payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def core_hash(meta: dict) -> str:
    """Hash of the prompt text and its origin (version 3)."""
    return _tagged_hash({"text": text_hash(meta["_body"]), "origin": meta.get("origin")})


def fingerprint_of(meta: dict, attachments: list[dict]) -> str:
    """The approval fingerprint: text only before version 3; text, origin and every attached
    file's path and content from version 3 on (SEC-4, CAT-2). Attachment order is part of it."""
    if meta.get("_version", 1) < 3:
        return text_hash(meta["_body"])
    files = [[a["path"], a["sha256"]] for a in attachments]
    return _tagged_hash({"core": core_hash(meta), "attachments": files})


def current_fingerprint(meta: dict) -> str | None:
    """The fingerprint load_catalog computed, or None when an attachment could not be read."""
    if "_fingerprint" in meta:
        return meta["_fingerprint"]
    return fingerprint_of(meta, [])


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
    meta, body = split_record(path.read_text(encoding="utf-8-sig"))
    if any(str(key).startswith("_") for key in meta):
        raise CatalogError("a field name starts with an underscore (reserved for this script)")
    meta["_body"] = normalize_text(body)
    return meta


def _target_mode(path: Path) -> int:
    """Permission bits for a rewritten file: the regular file's own, else the umask default."""
    try:
        st = os.lstat(path)
    except OSError:
        st = None
    if st is not None and stat.S_ISREG(st.st_mode):
        return stat.S_IMODE(st.st_mode) & 0o777
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def _write_atomic(path: Path, text: str) -> None:
    """Write text to a temp file beside path, then replace path, so a failed write (an unencodable
    character, a full disk) never truncates the file that was already there. The temp file has a
    random name and is created exclusively (mkstemp), so a symlink a repository planted at a
    predictable name can never redirect the write outside the catalog."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        mode = _target_mode(path)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            # mkstemp creates the file as 0600; give it the target's own permission bits (read from
            # the file itself, never through a link, and without setuid/setgid/sticky), or the
            # umask default for a new file, so rewriting a record does not change who can read it.
            # Set on the open descriptor where the platform allows, so a swapped-in link at the
            # temp name is never followed. A filesystem that rejects chmod keeps the temp file's
            # own mode rather than failing the write.
            with contextlib.suppress(OSError):
                if hasattr(os, "fchmod"):
                    handle.flush()
                    os.fchmod(handle.fileno(), mode)
                else:
                    os.chmod(tmp, mode)
            # Flush to disk before the rename, so a crash right after it cannot leave the target
            # name pointing at an empty or partly written file.
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            with contextlib.suppress(OSError):
                os.chmod(tmp, 0o600)  # a read-only temp file cannot be unlinked on Windows
            tmp.unlink(missing_ok=True)
        except OSError:
            pass  # the original error is the one worth reporting
        raise


def write_record(path: Path, meta: dict) -> None:
    clean = {k: v for k, v in meta.items() if not k.startswith("_")}
    text = "---\n" + dump_yaml(clean, FIELD_ORDER) + "---\n\n" + meta["_body"] + "\n"
    _write_atomic(path, text)


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
    version = meta.get("_version", 1)
    current = current_fingerprint(meta)
    what = "prompt, origin or attachments" if version >= 3 else "prompt text"
    if current is None:
        problems.extend(meta.get("_attachment_problems", []))
    required = ["quality"] + (["import"] if meta.get("origin") in ("session", "web") else [])
    expected = {kind: current for kind in required}
    if version >= 3:
        expected["core"] = core_hash(meta)
    for kind, value in expected.items():
        stored = ver.get(kind)
        if not stored:
            problems.append(f"verification.{kind} is missing")
        elif not isinstance(stored, str) or not HASH_RE.fullmatch(stored):
            problems.append(f"verification.{kind} is not a SHA-256 hex digest")
        elif kind == "core" and stored != value:
            problems.append("verification.core: the prompt text or origin changed")
        elif value is not None and stored != value:
            problems.append(f"verification.{kind} does not match the current {what}")
    for kind in ver:
        if kind not in VERIFICATION_KEYS[version]:
            problems.append(f"unknown verification field: {kind}")
    return problems


def attachment_only_change(meta: dict) -> bool:
    """True when a blocked version 3 prompt's text and origin still match its approval, so only an
    attached file changed (CAT-6, attachments amendment: it can be revised to take the new file)."""
    ver = meta.get("verification")
    return (
        meta.get("_version", 1) >= 3
        and isinstance(ver, dict)
        and ver.get("core") == core_hash(meta)
    )


def missing_verification(meta: dict) -> list[str]:
    """Required verification kinds that are absent or do not bind the current fingerprint, in step
    order (quality, then import), so a resumed draft knows whether to restart at the review or the
    import check."""
    ver = meta.get("verification")
    ver = ver if isinstance(ver, dict) else {}
    current = current_fingerprint(meta)
    required = ["quality"] + (["import"] if meta.get("origin") in ("session", "web") else [])
    return [kind for kind in required if current is None or ver.get(kind) != current]


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
    # A malformed verification of an approved record blocks only that prompt
    # (approval_problems), and one kept by retire must not fail the catalog.
    maps = MAP_FIELDS if meta["status"] == "draft" else MAP_FIELDS - {"verification"}
    for f in maps & set(meta):
        if meta[f] is not None and not isinstance(meta[f], dict):
            errs.append(f"{f} must be a map")
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
    if meta["status"] == "historical":
        pass  # never runs again, so an edited text (kept by retire) must not fail the catalog
    elif nonblank_lines(meta["_body"]) == 0:
        errs.append("prompt_text is empty")
    elif nonblank_lines(meta["_body"]) > MAX_NONBLANK_LINES:
        errs.append(f"prompt_text exceeds {MAX_NONBLANK_LINES} nonblank lines")
    return errs


def approval_problems(meta: dict) -> tuple[list[str], list[str]]:
    """For an approved (active or inactive) record: (problems that make the whole catalog invalid,
    reasons this one prompt counts as changed since its approval). A fingerprint that is missing,
    malformed or no longer matches the text blocks only the prompt itself (CAT-5)."""
    if meta.get("status") not in ("active", "inactive"):
        return [], []
    found = hash_problems(meta)
    unknown = [p for p in found if p.startswith("unknown verification field")]
    return unknown, [p for p in found if p not in unknown]


# ------------------------------------------------------------- catalog root


def _find_git(cwd: Path) -> str | None:
    """Absolute path of git, never one that lives inside the working directory.

    On Windows a bare "git" can resolve to a git.exe sitting in the current directory (for
    example one
    shipped by a cloned repository), so the lookup result is checked against the working directory.
    """
    found = shutil.which("git")
    if found and _within(Path(found), cwd):
        trusted = os.pathsep.join(
            p
            for p in os.environ.get("PATH", "").split(os.pathsep)
            if p and p != os.curdir and not _within(Path(p), cwd)
        )
        found = shutil.which("git", path=trusted)
        if found and _within(Path(found), cwd):
            found = None
    return found


def _norm_plain(path: Path) -> str:
    return os.path.normcase(os.path.realpath(str(path)))


def _within(path: Path, folder: Path) -> bool:
    """True when path is folder itself or lies below it.

    A plain string prefix would also match a sibling such as /work/repo-tools for the folder
    /work/repo, so the folder ends in a separator.
    """
    p, f = _norm_plain(path), _norm_plain(folder)
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def _git_toplevel(cwd: Path) -> Path | None:
    git = _find_git(cwd)
    if not git:
        return None
    try:
        out = subprocess.run(  # nosec B603 # nosemgrep
            [git, "rev-parse", "--show-toplevel"],  # nosemgrep
            cwd=str(cwd),
            env=_git_env(),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = out.stdout.strip()
    return Path(top) if out.returncode == 0 and top else None


_GIT_ENV_DROPPED = (
    "GIT_LITERAL_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
    "GIT_INDEX_FILE",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
)


def _git_env() -> dict[str, str]:
    """The environment git runs in: inherited switches that redirect which repository or index it
    reads, or how it reads a pathspec, would change its answer about the project."""
    return {k: v for k, v in os.environ.items() if k not in _GIT_ENV_DROPPED}


def _is_tracked(project_root: Path, rel: Path) -> bool:
    """True when git tracks rel. Fails closed: any doubt counts as tracked, so the override is
    ignored. Only git's exit code 1 (the path is not known to git) counts as untracked; any other
    failure, such as a corrupt index or an ownership error, is doubt."""
    git = _find_git(project_root)
    if not git:
        return True
    try:
        out = subprocess.run(  # nosec B603 # nosemgrep
            # icase: on a case-insensitive filesystem the override file is found under any casing,
            # so a tracked copy committed under another casing must still count as tracked.
            # nosemgrep
            [git, "ls-files", "--error-unmatch", "--", ":(icase,literal)" + rel.as_posix()],
            cwd=str(project_root),
            # An inherited GIT_LITERAL_PATHSPECS would make git read the icase magic as part of the
            # file name and report "untracked".
            env=_git_env(),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
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


def _norm_lexical(path: Path, fold: bool) -> str:
    """Like _norm but without following symlinks."""
    text = os.path.normcase(os.path.abspath(str(path)))
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


_JUNCTION_TAG = 0xA0000003  # stat.IO_REPARSE_TAG_MOUNT_POINT, which only Windows defines


def _is_link(path) -> bool:
    """True for a symlink or a Windows junction. Reads the entry itself and never follows it."""
    try:
        info = os.lstat(path)
    except (OSError, ValueError):
        return False
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) == _JUNCTION_TAG


def _parts_below(path: Path, base: Path) -> list[str] | None:
    """The parts of path below base, compared as written (no link is followed), or None. The
    parts keep their own spelling: folding can produce a name that is not the one on disk."""
    fold = _case_insensitive(base)
    below, top = _norm_lexical(path, fold), _norm_lexical(base, fold)
    prefix = top.rstrip(os.sep) + os.sep
    if not below.startswith(prefix):
        return None
    count = len(below[len(prefix) :].split(os.sep))
    return os.path.abspath(str(path)).split(os.sep)[-count:]


def _linked_below(path: Path, base: Path) -> bool:
    """True when path is not below base as written, or a part of it below base is a link. Resolving
    a link can open a network connection on Windows, so this runs before any other look at path."""
    parts = _parts_below(path, base)
    if parts is None:
        return True
    current = str(base)
    for part in parts:
        current = os.path.join(current, part)
        if _is_link(current):
            return True
    return False


def _is_unc(text: str) -> bool:
    """True for a UNC or device path in any separator mix. Check it before any filesystem call:
    resolving such a path on Windows can open a network connection."""
    return text.strip().replace("/", "\\").startswith(("\\\\", "\\??\\"))


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
    if _is_unc(text):
        return None, "UNC paths are not allowed"
    # Windows drops a trailing dot or space from a folder name and reads ':' as a stream marker, so
    # ".claude./rules" can create the real .claude folder while escaping the name match below.
    for segment in re.split(r"[\\/]", os.path.splitdrive(text)[1]):
        if segment not in ("", ".", "..") and _bad_segment(segment):
            return None, "a path part ends in a dot or space, or contains a colon"
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    reason = _placement_problem(candidate, project_root)
    if reason:
        return None, reason
    return Path(os.path.realpath(str(candidate))), None


def _bad_segment(segment: str) -> bool:
    return segment != segment.rstrip(". ") or ":" in segment


def _placement_problem(candidate: Path, project_root: Path) -> str | None:
    """The placement rules a catalog root and an attached file share (m2): strictly inside the
    project root, and never at, under or containing a folder that holds configuration or
    instructions."""
    if not contained(candidate, project_root):
        return "resolves outside the project root"
    fold = _case_insensitive(project_root)
    for forbidden in FORBIDDEN_ROOTS:
        target = project_root / forbidden
        if _norm(candidate, fold) == _norm(target, fold) or contained(candidate, target):
            return f"resolves inside {forbidden}, which holds configuration or instructions"
    # The same folders nested deeper (sub/.claude/rules) can be loaded as instructions too. Match
    # the resolved path and the path as written: a symlink named .claude/rules is read under that
    # name, whatever it points at.
    # Each form is measured against the project root in the same form, never a mix. Names are
    # folded here whatever the filesystem does: a ".CLAUDE" folder is refused even where it would
    # be a different folder, so the rule never depends on the case behavior of one machine.
    for norm in (_norm, _norm_lexical):
        try:
            rel = os.path.relpath(norm(candidate, True), norm(project_root, True))
        except ValueError:  # different drives: cannot be placed under the root, so refuse
            return "cannot be compared with the project root"
        parts = rel.replace("\\", "/").split("/")
        for forbidden in FORBIDDEN_ROOTS:
            seq = forbidden.split("/")
            if any(parts[i : i + len(seq)] == seq for i in range(len(parts) - len(seq) + 1)):
                return f"contains {forbidden} below the project root, which holds instructions"
    return None


# A part of an attachment path: no separator, control character or character Windows refuses.
_DEVICE_NAMES = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    f"{kind}{n}" for kind in ("com", "lpt") for n in range(10)
}
_ATTACH_PART = re.compile(r'^[^\x00-\x1f\x7f/\\:*?"<>|]+$')


def attachment_text_problem(value) -> str | None:
    """Why an attachment entry is not a canonical project-relative path, or None. One spelling
    per file keeps the fingerprint stable: forward slashes, no ".", ".." or empty parts."""
    if not isinstance(value, str) or not value.strip():
        return "is empty or not text"
    if value != value.strip():
        return "has leading or trailing space"
    if value.startswith("/") or "\\" in value or re.match(r"^[A-Za-z]:", value):
        return "must be a path relative to the project root, written with /"
    parts = value.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            return 'must not contain an empty, "." or ".." part'
        if not _ATTACH_PART.fullmatch(part) or _bad_segment(part):
            return "contains a character or part ending that Windows does not allow"
        if part.split(".")[0].casefold() in _DEVICE_NAMES:
            return "names a Windows device"
    name = parts[-1].casefold()
    if name == ".env" or name.startswith(".env."):
        return "is a .env file, which holds secrets"
    return None


def attachment_path(
    value, project_root: Path, catalog_root: Path
) -> tuple[Path | None, str | None]:
    """Return (path to open, None) or (None, reason) for one attachment entry. The returned path is
    the one checked, spelled as written below the project root; open exactly that path."""
    reason = attachment_text_problem(value)
    if reason:
        return None, reason
    path = Path(project_root, *value.split("/"))
    if _linked_below(path, project_root):  # before any look that could follow a link
        return None, "goes through a link"
    reason = _placement_problem(path, project_root)
    if reason:
        return None, reason
    fold = _case_insensitive(project_root)
    if _norm(path, fold) == _norm(catalog_root, fold) or contained(path, catalog_root):
        return None, "is inside the prompt catalog"
    return path, None


class AttachContext:
    """Where attachments are resolved and how much one prompt may attach (CFG-6)."""

    def __init__(self, project_root: Path, catalog_root: Path, limit_kb: int):
        self.project_root, self.catalog_root, self.limit_kb = project_root, catalog_root, limit_kb


def _opened_path(fd: int) -> str | None:
    """The path the operating system holds for an open file, or None when it cannot say. Asked of
    the handle itself, so no swap of a name after the open can change the answer."""
    try:
        if sys.platform == "win32":
            import ctypes
            import msvcrt
            from ctypes import wintypes

            final = ctypes.windll.kernel32.GetFinalPathNameByHandleW
            final.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
            final.restype = wintypes.DWORD
            handle, size = msvcrt.get_osfhandle(fd), 1024
            while True:
                buf = ctypes.create_unicode_buffer(size)
                got = final(handle, buf, size, 0)
                if got == 0:
                    return None
                if got < size:
                    break
                size = got + 1
            text = buf.value
            if text.startswith("\\\\?\\UNC\\"):
                return None  # a network file is never inside the project
            return text[4:] if text.startswith("\\\\?\\") else text
        if sys.platform == "darwin":
            import fcntl

            raw = fcntl.fcntl(fd, 50, b"\0" * 1024)  # F_GETPATH
            return os.fsdecode(raw.split(b"\0", 1)[0])
        target = os.readlink(f"/proc/self/fd/{fd}")
        return target if target.startswith("/") else None
    except (OSError, AttributeError, ValueError, ImportError):
        return None


def _read_once(path: Path, project_root: Path, budget: int) -> bytes:
    """Read a checked attachment exactly once (REV-6, EXE-2), and refuse it unless the opened file
    is the one checked: the handle's own path must be the project root's real path plus the parts as
    written (no link, junction, short name or swapped folder on the way), and the file must have one
    name only (a hard link can name a file outside the project). Returns at most budget + 1 bytes,
    so the caller can tell the file is over the limit."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)  # a FIFO must not block the open
    if not stat.S_ISREG(os.lstat(path).st_mode):  # a folder cannot even be opened on Windows
        raise CatalogError("is not a regular file")
    parts = _parts_below(path, project_root)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise CatalogError("is not a regular file")
        if opened.st_nlink != 1:
            raise CatalogError("has more than one name (a hard link)")
        actual = _opened_path(fd)
        if actual is None or parts is None:
            raise CatalogError("its location cannot be confirmed")
        # normcase only, no casefold: casefold is looser than any filesystem's own case rules.
        expected = os.path.join(os.path.realpath(str(project_root)), *parts)
        if _norm_lexical(Path(actual), False) != _norm_lexical(Path(expected), False):
            raise CatalogError("goes through a link or a different name, or was replaced")
        chunks, size = [], 0
        while size <= budget:
            chunk = os.read(fd, min(65536, budget + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
    finally:
        os.close(fd)
    return b"".join(chunks)


def read_attachments(meta: dict, ctx: AttachContext | None) -> tuple[list[dict], list[str]]:
    """Read every attached file of a version 3 record once: [{path, content, sha256, bytes}] and the
    problems that make the set unusable. The content returned is the content fingerprinted."""
    paths = meta.get("attachments") or []
    if meta.get("_version", 1) < 3 or not paths:
        return [], []  # before version 3 the field is stored but never loaded
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        return [], ["attachments must be a list of text"]
    if ctx is None:
        return [], ["attachments cannot be checked here"]
    limit = ctx.limit_kb * 1024
    found: list[dict] = []
    problems: list[str] = []
    used = 0
    for value in paths:
        if any(a["path"] == value for a in found):
            problems.append(f"attachment {value}: listed twice")
            continue
        path, reason = attachment_path(value, ctx.project_root, ctx.catalog_root)
        if reason or path is None:
            problems.append(f"attachment {value}: {reason}")
            continue
        try:
            raw = _read_once(path, ctx.project_root, max(limit - used, 0))
        except FileNotFoundError:
            problems.append(f"attachment {value}: missing")
            continue
        except CatalogError as exc:
            problems.append(f"attachment {value}: {exc}")
            continue
        except OSError as exc:
            problems.append(f"attachment {value}: cannot be read ({exc.strerror or exc})")
            continue
        if used + len(raw) > limit:
            size = None
            with contextlib.suppress(OSError):
                size = os.lstat(path).st_size
            problems.append(
                f"attachment {value}: {size if size is not None else 'too many'} bytes, with "
                f"{used} bytes attached before it: over the {ctx.limit_kb} KB limit "
                f"({limit} bytes for all attachments together)"
            )
            continue
        used += len(raw)
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            problems.append(f"attachment {value}: is not UTF-8 text")
            continue
        if "\x00" in content:
            problems.append(f"attachment {value}: is not a text file")
            continue
        found.append(
            {"path": value, "content": content, "sha256": text_hash(content), "bytes": len(raw)}
        )
    return found, problems


def _with_attachments(meta: dict, ctx: AttachContext | None) -> dict:
    """Read meta's attachments and set _attachments, _attachment_problems and _fingerprint (None
    while an attachment cannot be used)."""
    found, problems = read_attachments(meta, ctx)
    meta["_attachments"], meta["_attachment_problems"] = found, problems
    meta["_fingerprint"] = None if problems else fingerprint_of(meta, found)
    return meta


def _via_link(project_root: Path, local: Path) -> bool:
    """True when the override file is reached through a link. git does not look through a tracked
    folder symlink, so its "not tracked" answer cannot be trusted for such a path."""
    expected = os.path.join(os.path.realpath(str(project_root)), *LOCAL_OVERRIDE.parts)
    return os.path.normcase(os.path.realpath(str(local))) != os.path.normcase(expected)


def _settings_dir() -> Path:
    # <dir>/scripts/this_file.py with <dir>/promptlibrary-kit.settings.json beside scripts/ — true
    # for the
    # plugin root and for the hand-copied twin under .claude/ (see README).
    return Path(__file__).resolve().parent.parent


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _limit_value(value) -> bool:
    return type(value) is int and value in ATTACHMENT_LIMITS_KB


def _attachment_limit(defaults, local, trusted: bool, warnings: list[str]) -> dict:
    """attachment_max_kb (CFG-6): the plugin default, then the local override. A local file that
    git tracks, that is reached through a link or that git cannot check may only lower it."""
    kb, source = DEFAULT_ATTACHMENT_KB, "built-in default"
    allowed = "/".join(str(n) for n in ATTACHMENT_LIMITS_KB)
    if isinstance(defaults, dict) and "attachment_max_kb" in defaults:
        if _limit_value(defaults["attachment_max_kb"]):
            kb, source = defaults["attachment_max_kb"], "plugin default"
        else:
            warnings.append(f"plugin default attachment_max_kb is not {allowed}; using {kb}")
    if isinstance(local, dict) and "attachment_max_kb" in local:
        value = local["attachment_max_kb"]
        name = LOCAL_OVERRIDE.as_posix()
        if not _limit_value(value):
            warnings.append(f"{name} attachment_max_kb is not {allowed}; using {kb}")
        elif trusted or value <= kb:
            kb, source = value, "local override"
        else:
            warnings.append(
                f"{name} may only lower attachment_max_kb here (tracked, linked or outside git); "
                f"using {kb}"
            )
    return {"attachment_max_kb": kb, "attachment_limit_source": source}


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
    data = None
    trusted = False
    if local.is_file():
        linked = _via_link(project_root, local)
        data = None if linked else _read_json(local)  # a linked file is never read
        if not top:
            info["warnings"].append(
                f"{LOCAL_OVERRIDE.as_posix()} cannot be checked against git here; its path value "
                "is ignored"
            )
        elif linked or _is_tracked(project_root, LOCAL_OVERRIDE):
            info["warnings"].append(
                f"{LOCAL_OVERRIDE.as_posix()} is tracked by git or reached through a link; "
                "its path value is ignored"
            )
        else:
            trusted = True
            if isinstance(data, dict) and "catalog_root" in data:
                candidates.append(("local override", data["catalog_root"]))
            elif not (isinstance(data, dict) and "attachment_max_kb" in data):
                info["warnings"].append(
                    f"{LOCAL_OVERRIDE.as_posix()} is unreadable or has no catalog_root"
                )
    info.update(_attachment_limit(defaults, data, trusted, info["warnings"]))
    candidates.append(("default", default_value))
    for source, value in candidates:
        resolved, reason = check_catalog_path(value, project_root)
        if resolved is not None:
            info.update(catalog_root=str(resolved), root_source=source)
            return info
        info["warnings"].append(f"{source} catalog path rejected ({reason}); falling back")
    raise CatalogError("no usable catalog root: " + "; ".join(info["warnings"]))


# ------------------------------------------------------------ catalog loading


def load_catalog(root: Path, ctx: AttachContext | None = None) -> tuple[dict, dict, list[str]]:
    """Return (catalog meta, {relpath: record}, errors). Never raises for content problems. An
    attachment problem is never structural: it blocks only its own prompt (CAT-5)."""
    errs: list[str] = []
    cat_path = root / "catalog.yaml"
    if _linked_below(cat_path, root):
        return {}, {}, ["catalog.yaml is reached through a link"]
    if not cat_path.is_file():
        return {}, {}, ["catalog.yaml is missing"]
    try:
        cat = parse_yaml(cat_path.read_text(encoding="utf-8-sig"))
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
    reserved = cat.get("reserved_slugs")
    if reserved is not None and (
        not isinstance(reserved, list)
        or not all(isinstance(x, str) and SLUG_RE.fullmatch(x) for x in reserved)
    ):
        errs.append("catalog.yaml: reserved_slugs must be a list of slugs")
    elif version == 2 and not reserved:
        # a catalog only moves to version 2 to reserve a slug, so an empty list was lost
        errs.append("catalog.yaml: version 2 needs at least one slug in reserved_slugs")
    listed = cat.get("records")
    if listed is None:
        listed = []
    if not isinstance(listed, list) or not all(isinstance(x, str) for x in listed):
        return cat, {}, errs + ["catalog.yaml: records must be a list of paths"]
    records: dict = {}
    for rel in listed:
        # One spelling only, the one the validator writes: <slug>/<file>.md with "/". A "." part or
        # a backslash would otherwise be read as another file, and reported as missing.
        parts = rel.split("/")
        if (
            "\\" in rel
            or len(parts) != 2
            or any(p in ("", ".", "..") for p in parts)
            or not parts[1].endswith(".md")
        ):
            errs.append(f"invalid record path: {rel} (expected <slug>/<file>.md, written with /)")
            continue
        if rel in records:
            errs.append(f"record listed twice: {rel}")
            continue
        path = root / parts[0] / parts[1]
        if _linked_below(path, root):
            errs.append(f"record path goes through a link or leaves the catalog root: {rel}")
            continue
        if not path.is_file():
            errs.append(f"listed record is missing: {rel}")
            continue
        try:
            meta = read_record(path)
        except (CatalogError, OSError, ValueError) as exc:
            errs.append(f"{rel}: {exc}")
            continue
        meta["_path"], meta["_version"] = rel, version
        problems = validate_record(meta, version)
        _with_attachments(meta, ctx)
        structural, changed = approval_problems(meta)
        if changed:
            # An edited text can also break the text limits. That belongs to the same prompt.
            changed += [p for p in problems if p.startswith("prompt_text ")]
            problems = [p for p in problems if not p.startswith("prompt_text ")]
            meta["_blocked"] = changed
            meta["_attachment_change"] = attachment_only_change(meta)
        errs.extend(f"{rel}: {p}" for p in [*problems, *structural])
        records[rel] = meta
    errs.extend(check_lineages(root, records))
    _mark_retired(records)
    return cat, records, errs


def _mark_retired(records: dict) -> None:
    """Flag the historical records of a retired lineage: one whose last approved version is
    historical. A finished revision always leaves a newer active or inactive version, so only
    retire does this. A draft left behind is not flagged: it can still be found and discarded."""
    groups: dict = {}
    for meta in records.values():
        if isinstance(meta.get("slug"), str) and isinstance(meta.get("version"), int):
            groups.setdefault(meta["slug"], []).append(meta)
    for group in groups.values():
        approved = [m for m in group if m.get("status") in ("active", "inactive")]
        ran = [m for m in group if m.get("status") == "historical"]
        if ran and not approved:
            for meta in ran:
                meta["_retired"] = True


def _refuse_blocked(records: dict, slug, allow_attachment: bool = False) -> None:
    """Refuse a change to a prompt that changed since its approval: it can only be restored from
    git or retired (CAT-6). When only an attached file changed, allow_attachment lets the revise
    steps through (a successor with the same text and origin). Other prompts are not affected."""
    for meta in records.values():
        if meta.get("slug") != slug or not meta.get("_blocked"):
            continue
        reasons = "; ".join(meta["_blocked"])
        if not meta.get("_attachment_change"):
            raise CatalogError(
                f"{slug} changed since its approval ({reasons}): restore {meta['_path']} from git "
                "or retire it"
            )
        if not allow_attachment:
            raise CatalogError(
                f"{slug}: an attachment changed since its approval ({reasons}): revise it to "
                "review the new content, restore the file, or retire the prompt"
            )


def _same_core_as_blocked(meta: dict, records: dict) -> list[str]:
    """A successor of a prompt whose attachment changed keeps the approved text and origin: only
    the attached content is reviewed again (CAT-6, attachments amendment)."""
    for other in records.values():
        if (
            other.get("slug") == meta.get("slug")
            and other.get("_attachment_change")
            and core_hash(other) != core_hash(meta)
        ):
            return [
                "the prompt's attachment changed since its approval: a revision keeps the "
                "approved text and origin and only takes the new attachment content"
            ]
    return []


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
                if not isinstance(prev, str):
                    errs.append(f"{m['_path']}: previous_id must be text")
                    continue
                target = by_id.get(prev)
                if target is None or target.get("slug") != slug:
                    errs.append(f"{m['_path']}: previous_id {prev} not found in the same lineage")
                elif isinstance(m.get("version"), int) and target.get("version") != (
                    m["version"] - 1
                ):
                    errs.append(
                        f"{m['_path']}: previous_id is not the immediately preceding version"
                    )
    listed = set(records)
    for entry in sorted(root.iterdir()) if root.is_dir() else []:
        if _is_link(entry):
            # Whether a link points at a folder cannot be told without following it. A name ending
            # in .tmp is never a catalog folder, so a link under one stays unused and unread.
            if not entry.name.endswith(".tmp"):
                errs.append(f"folder is a link: {entry.name}")
        elif entry.is_dir():
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
        "missing_verification": missing_verification(meta),
        "blocked": meta.get("_blocked", []),
        "attachment_change": meta.get("_attachment_change", False),
        "retired": meta.get("_retired", False),
        "fingerprint": current_fingerprint(meta),
        "attachments": [a["path"] for a in meta.get("_attachments", [])],
        "attachment_problems": meta.get("_attachment_problems", []),
    }


def _attachment_view(meta: dict) -> list[dict]:
    """Each attached file's full checked content, as read once by load_catalog."""
    out = []
    for a in meta.get("_attachments", []):
        hidden, truncated = hidden_characters(a["content"])
        out.append(
            {
                "path": a["path"],
                "bytes": a["bytes"],
                "sha256": a["sha256"],
                "content": a["content"],
                "hidden_characters": hidden,
                "hidden_characters_truncated": truncated,
            }
        )
    return out


# ------------------------------------------------------------------ commands


def _context(info: dict) -> AttachContext:
    return AttachContext(
        Path(info["project_root"]), Path(info["catalog_root"]), info["attachment_max_kb"]
    )


def _load(args) -> tuple[dict, Path, dict, dict]:
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    cat, records, errs = load_catalog(root, _context(info))
    info["errors"] = errs
    return info, root, cat, records


def _need_ok(info: dict) -> None:
    if info["errors"]:
        raise CatalogError("catalog is not valid: " + "; ".join(info["errors"][:3]))


def _stray_temp_files(root: Path) -> list[str]:
    """Temp files a killed write left behind (not records, so validation never lists them)."""
    if not root.is_dir():
        return []
    # The shapes _write_atomic creates. A linked folder is never listed: check_lineages reports it,
    # except one whose name ends in .tmp, which is never a catalog folder and stays unread.
    found = set(root.glob("catalog.yaml.*.tmp"))
    for entry in root.iterdir():
        if not _is_link(entry) and entry.is_dir():
            found.update(entry.glob("*.md.*.tmp"))
    return sorted(p.relative_to(root).as_posix() for p in found if _is_link(p) or p.is_file())


def search_words(text: str) -> str:
    """Letters (with their combining marks) and digits only, case-folded and single-spaced, so a
    search ignores punctuation, line breaks and case."""
    out = ""
    for ch in unicodedata.normalize("NFC", text).casefold():
        mark = unicodedata.category(ch).startswith("M") and out[-1:] not in ("", " ")
        out += ch if ch.isalnum() or mark else " "
    return " ".join(out.split())


def search_matches(meta: dict, query: str) -> list[str]:
    """Where a search_words() query occurs as whole words in a record: label names, or "text" for
    the prompt."""
    fields = {f: meta[f] for f in ("slug", "name", "area", "short_description")}
    fields["text"] = meta["_body"]
    return [name for name, value in fields.items() if f" {query} " in f" {search_words(value)} "]


def cmd_validate(args) -> dict:
    info, root, cat, records = _load(args)
    for rel in _stray_temp_files(root):
        info["warnings"].append(
            f"stray temp file {rel} (appears left by an interrupted write; check, then delete)"
        )
    info["ok"] = not info["errors"]
    info["catalog_version"] = cat.get("catalog_version")
    info["blocked"] = [
        {
            "slug": m.get("slug"),
            "internal_id": m.get("internal_id"),
            "version": m.get("version"),
            "path": m["_path"],
            "text_hash": text_hash(m["_body"]),
            "reasons": m["_blocked"],
            "attachment_change": m.get("_attachment_change", False),
        }
        for m in records.values()
        if m.get("_blocked")
    ]
    if args.search is None:
        info["records"] = [summarize(m) for m in records.values()]
        return info
    _need_ok(info)  # a search lists nothing from a catalog that fails its check
    query = search_words(args.search)
    if not query:
        raise CatalogError("the search needs at least one letter or digit")
    hits = ((m, search_matches(m, query)) for m in records.values())
    info["records"] = [{**summarize(m), "matched_in": found} for m, found in hits if found]
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
        _refuse_blocked(records, args.slug)
    info["ok"] = True
    info["records"] = [
        {
            **summarize(m),
            "path": m["_path"],
            "previous_id": m.get("previous_id"),
            "prerequisites": m.get("prerequisites"),
            "boundaries": m.get("boundaries"),
            "references": m.get("references"),
            "source_ref": m.get("source_ref"),
            "prompt_text": m["_body"],
            "text_hash": text_hash(m["_body"]),
            "attachment_content": _attachment_view(m),
        }
        for m in shown
    ]
    for entry, m in zip(info["records"], shown, strict=True):
        entry["hidden_characters"], entry["hidden_characters_truncated"] = hidden_characters(
            m["_body"]
        )
    return info


def cmd_review_bundle(args) -> dict:
    """Everything prompt-reviewer may see for one draft, from one read of the record and each of
    its attachments (REV-6): the caller passes this inline, so the reviewer opens no path."""
    info, _, _, records = _load(args)
    _need_ok(info)
    meta = _record_by_id(records, args.internal_id)
    if meta["status"] != "draft":
        raise CatalogError("only a draft is reviewed; revise an active or inactive record first")
    _refuse_blocked(records, meta["slug"], allow_attachment=True)
    if meta["_attachment_problems"]:
        raise CatalogError("; ".join(meta["_attachment_problems"][:4]))
    hidden, truncated = hidden_characters(meta["_body"])
    fields = ("slug", "internal_id", "version", "name", "area", "short_description", "origin")
    info.update(
        ok=True,
        record={f: meta.get(f) for f in fields}
        | {
            f: meta.get(f)
            for f in ("source_ref", "prerequisites", "boundaries", "references", "previous_id")
        },
        prompt_text=meta["_body"],
        hidden_characters=hidden,
        hidden_characters_truncated=truncated,
        attachment_content=_attachment_view(meta),
        fingerprint=meta["_fingerprint"],
        text_hash=text_hash(meta["_body"]),
    )
    return info


MAX_INPUT_BYTES = 262144


def _inside(root: Path, path: Path) -> Path:
    """Re-check containment right before a write: a directory can be swapped for a link after load
    time."""
    if _linked_below(path, root) or not contained(path, root):
        raise CatalogError(f"path escapes the catalog root: {path.name}")
    return path


def _readable_candidate(path_text: str, root: Path) -> Path:
    """A file the hash/screen/draft commands may read: inside the catalog root or the system temp
    directory."""
    if "\x00" in path_text or _is_unc(path_text):
        raise CatalogError("the path is a UNC path or contains a NUL byte")
    # Remove ".." as written and use only that form from here on: the system would resolve a ".."
    # behind a link to the parent of the link's target, which is not the path checked below.
    path = Path(os.path.abspath(path_text))
    temp = Path(tempfile.gettempdir())
    # The temp directory counts in both spellings: as configured and with its own links resolved.
    allowed = [a for a in (root, temp, Path(os.path.realpath(str(temp)))) if a.exists()]
    below = [(a, parts) for a in allowed if (parts := _parts_below(path, a)) is not None]
    if not below:
        raise CatalogError("the file must be inside the catalog root or the system temp directory")
    # Checked below the innermost match, so a catalog reached through the temp directory's own
    # location is not refused for a part above it.
    base, parts = max(below, key=lambda b: len(str(b[0])))
    path = Path(base, *parts)  # a look-alike of base compares equal when folded: never open that
    if _linked_below(path, base):
        raise CatalogError("the file is reached through a link")
    if not any(contained(path, a) for a in allowed):
        raise CatalogError("the file must be inside the catalog root or the system temp directory")
    if not path.is_file():
        raise CatalogError(f"not a file: {path_text}")
    resolved = Path(os.path.realpath(str(path)))
    if resolved.stat().st_size > MAX_INPUT_BYTES:
        raise CatalogError("the file is too large")
    return resolved


def cmd_hash(args) -> dict:
    info = resolve_root(getattr(args, "root", None))
    path = _readable_candidate(args.file, Path(info["catalog_root"]))
    try:
        raw = path.read_text(encoding="utf-8-sig")
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
    # A lone CR ends a line too, or a line-anchored pattern (dotenv_secret_line) would miss an
    # assignment that follows one.
    for lineno, line in enumerate(re.split(r"\r\n|\r|\n", text), start=1):
        if not line.strip():
            continue  # no pattern matches a blank line; many of them must stay cheap
        # Other line separators are shown as breaks too, so their parts are screened as lines of
        # their own, next to the whole line (a match may also span one).
        parts = re.split(r"[\v\f\x1c-\x1e\x85\u2028\u2029]", line)
        views = [line] if len(parts) == 1 else [line, *parts]
        for name, pattern in SECRET_PATTERNS:
            if any(pattern.search(view) for view in views):
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
    """Enforce detect-and-block for session, web, claude and codex text (SCREENED_ORIGINS), not
    just in the skill's step order."""
    if meta.get("origin") in SCREENED_ORIGINS:
        hits = screen_text(screen_blob(meta))
        if hits:
            names = ", ".join(sorted({h["pattern"] for h in hits}))
            raise CatalogError(
                f"possible secret or personal data found ({names}); remove it and try again"
            )
        found = attachment_screen(meta)
        if found:
            names = ", ".join(sorted({h["path"] for h in found}))
            raise CatalogError(
                f"possible secret or personal data found in an attachment ({names}); remove it "
                "and try again"
            )


def attachment_screen(meta: dict) -> list[dict]:
    """{path, line, pattern} for each secret-screen match in an attached file. For user text these
    are warnings to show (SCR-2); for the other origins _assert_clean refuses them."""
    return [
        {"path": a["path"], **hit}
        for a in meta.get("_attachments", [])
        for hit in screen_text(a["content"])
    ]


def _check_expected(meta: dict, expected: str, text_only: bool = False) -> None:
    """Bind a change to what the user was shown: the approval fingerprint for an approval step, or
    the text hash for discard and retire, which also apply when an attachment cannot be read."""
    shown = (expected or "").strip().lower()
    if text_only:
        if text_hash(meta["_body"]) != shown:
            raise CatalogError(
                "the prompt text changed since it was approved (--expect-sha256 does not match)"
            )
        return
    if meta.get("_attachment_problems"):
        raise CatalogError("; ".join(meta["_attachment_problems"][:4]))
    if current_fingerprint(meta) != shown:
        raise CatalogError(
            "the prompt changed since it was approved (--expect-sha256 does not match its "
            "fingerprint)"
        )


def cmd_screen(args) -> dict:
    try:
        if args.file == "-":
            # read() counts characters; the cap is in UTF-8 bytes, so measure the encoded size too.
            text = sys.stdin.read(MAX_INPUT_BYTES + 1)
            if len(text.encode("utf-8", "surrogatepass")) > MAX_INPUT_BYTES:
                raise CatalogError("the input is too large")
            text = text.removeprefix(chr(0xFEFF))
        else:
            info = resolve_root(getattr(args, "root", None))
            path = _readable_candidate(args.file, Path(info["catalog_root"]))
            text = path.read_text(encoding="utf-8-sig")
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
    order = ["catalog_version", "scope", "snapshot_id", "records"]
    if cat.get("reserved_slugs"):
        out["reserved_slugs"] = sorted(set(cat["reserved_slugs"]))
        order.append("reserved_slugs")
    target = _inside(root, root / "catalog.yaml")
    _write_atomic(target, dump_yaml(out, order))


def cmd_init(args) -> dict:
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    if _is_link(root / "catalog.yaml"):
        raise CatalogError("catalog.yaml is reached through a link")
    if (root / "catalog.yaml").exists():
        raise CatalogError("catalog.yaml already exists")
    root.mkdir(parents=True, exist_ok=True)
    write_catalog(root, {"catalog_version": CURRENT_CATALOG_VERSION}, [])
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


def _check_new_draft(meta: dict, records: dict, cat: dict) -> list[str]:
    errs = []
    if any(m["internal_id"] == meta["internal_id"] for m in records.values()):
        errs.append("duplicate internal_id")
    group = [m for m in records.values() if m["slug"] == meta["slug"]]
    if any(m.get("_blocked") and not m.get("_attachment_change") for m in group):
        errs.append("the prompt changed since its approval: restore it from git or retire it")
    errs.extend(_same_core_as_blocked(meta, records))
    if meta["version"] == 1:
        if group:
            errs.append("the slug is already used by another lineage")
        elif meta["slug"] in (cat.get("reserved_slugs") or []):
            errs.append("the slug belonged to a discarded draft and is never reused")
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


def _valid_catalog(root: Path, ctx: AttachContext):
    cat, records, errs = load_catalog(root, ctx)
    if errs:
        raise CatalogError("catalog is not valid: " + "; ".join(errs[:3]))
    return cat, records


def _catalog_committed(root: Path, before: dict) -> bool:
    """True if catalog.yaml lost the snapshot_id read before a write, or cannot be read.
    write_catalog always writes a new snapshot_id, and an interrupt can land after it replaced the
    file but before it returned: cleanup must then keep what the catalog lists."""
    try:
        now = parse_yaml((root / "catalog.yaml").read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, CatalogError):
        return True
    return now.get("snapshot_id") != before.get("snapshot_id")


def _scratch_record(path_text: str, ctx: AttachContext, version: int) -> dict:
    """Read and check a scratch draft against the field list of the catalog's own version, with
    its attachments read and checked (CAT-2, CFG-6: refused before review)."""
    root = ctx.catalog_root
    path = _readable_candidate(path_text, root)
    try:
        meta = read_record(path)
    except (CatalogError, OSError, UnicodeDecodeError) as exc:
        raise CatalogError(f"cannot read the draft file: {exc}") from exc
    errs = validate_record(meta, version)
    if meta.get("status") != "draft":
        errs.append("only a draft record can be added or updated here")
    if errs:
        raise CatalogError("; ".join(errs[:4]))
    meta.pop("verification", None)  # a new or changed draft starts unverified
    meta["_version"] = version
    _with_attachments(meta, ctx)
    if meta["_attachment_problems"]:
        raise CatalogError("; ".join(meta["_attachment_problems"][:4]))
    _assert_clean(meta)
    return meta


def _draft_result(meta: dict) -> dict:
    return {
        "internal_id": meta["internal_id"],
        "text_hash": text_hash(meta["_body"]),
        "fingerprint": meta["_fingerprint"],
        "attachments": [a["path"] for a in meta["_attachments"]],
        "attachment_screen": attachment_screen(meta),
    }


def cmd_draft(args) -> dict:
    """Add a new draft from a scratch file: validate, screen, write the record, then list it in
    catalog.yaml."""
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    ctx = _context(info)
    cat, records = _valid_catalog(root, ctx)
    meta = _scratch_record(args.file, ctx, cat["catalog_version"])
    errs = _check_new_draft(meta, records, cat)
    if errs:
        raise CatalogError("; ".join(errs))
    rel = f"{meta['slug']}/{meta['internal_id']}.md"
    target = _inside(root, root / meta["slug"] / f"{meta['internal_id']}.md")
    if target.exists():
        raise CatalogError(f"{rel} already exists")
    new_dir = not target.parent.exists()
    target.parent.mkdir(exist_ok=True)
    try:
        write_record(target, meta)
        write_catalog(root, cat, [m["_path"] for m in records.values()] + [rel])
    except BaseException:
        if _catalog_committed(root, cat):
            raise  # catalog.yaml already lists the draft: keep it
        # No orphan record file, and no empty slug folder this call created, is left behind.
        with contextlib.suppress(OSError):
            target.unlink(missing_ok=True)
            if new_dir:
                target.parent.rmdir()
        raise
    info.update(ok=True, path=rel, **_draft_result(meta))
    return info


def cmd_update_draft(args) -> dict:
    """Replace an existing draft's content from a scratch file (an approved rewrite or an in-place
    edit)."""
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    ctx = _context(info)
    cat, records = _valid_catalog(root, ctx)
    current = _record_by_id(records, args.internal_id)
    if current["status"] != "draft":
        raise CatalogError(
            "only a draft can be updated in place; revise an active or inactive record instead"
        )
    _refuse_blocked(records, current["slug"], allow_attachment=True)
    meta = _scratch_record(args.file, ctx, cat["catalog_version"])
    for field in ("internal_id", "slug", "version", "previous_id", "origin", "source_ref"):
        if meta.get(field) != current.get(field):
            raise CatalogError(f"{field} cannot change when updating a draft")
    problems = _same_core_as_blocked(meta, records)
    if problems:
        raise CatalogError(problems[0])
    # Keep the verification only for the exact content it bound: text, origin and attachments.
    if meta["_fingerprint"] == current["_fingerprint"] and current.get("verification"):
        meta["verification"] = current["verification"]
    write_record(_inside(root, root / current["_path"]), meta)
    info.update(ok=True, **_draft_result(meta))
    return info


def cmd_register(args) -> dict:
    """List an existing, unlisted draft file (path relative to the catalog root) in catalog.yaml."""
    info = resolve_root(getattr(args, "root", None))
    root = Path(info["catalog_root"])
    ctx = _context(info)
    cat, records, errs = load_catalog(root, ctx)
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
    if problems:  # a malformed draft may lack the fields the checks below read
        raise CatalogError("; ".join(problems[:4]))
    if meta.get("status") != "draft":
        problems.append("only a draft record can be registered")
    elif parts[1] != f"{meta['internal_id']}.md" or parts[0] != meta["slug"]:
        problems.append(f"a draft must be stored as {meta['slug']}/{meta['internal_id']}.md")
    problems.extend(_check_new_draft(meta, records, cat))
    if problems:
        raise CatalogError("; ".join(problems[:4]))
    meta["_version"] = cat.get("catalog_version", 1)
    _with_attachments(meta, ctx)  # a broken attachment is refused later, at verification
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
    _, _, errs = load_catalog(root, _context(info))
    rel = args.path.replace("\\", "/")
    if f"unlisted record file on disk: {rel}" not in errs:
        raise CatalogError(f"{rel} is not an unlisted record file")
    parts = rel.split("/")
    path = _inside(root, root / parts[0] / parts[1])
    try:
        meta = read_record(path)
    except (CatalogError, OSError, ValueError):
        meta = {}
    if meta.get("status") != "draft":
        raise CatalogError(
            "only an unlisted draft can be discarded; this file is not a readable draft"
        )
    path.unlink()
    with contextlib.suppress(OSError):
        path.parent.rmdir()  # only succeeds when the slug folder is now empty
    info["ok"] = True
    info["removed"] = rel
    info["slug"] = meta.get("slug")
    info["internal_id"] = meta.get("internal_id")
    return info


def cmd_discard_draft(args) -> dict:
    """Delete one listed draft. A first draft's slug stays reserved (never reused)."""
    info, root, cat, records = _load(args)
    _need_ok(info)
    meta = _record_by_id(records, args.internal_id)
    if meta["status"] != "draft":
        raise CatalogError("only a draft can be discarded; a version that has run stays")
    if any(m.get("previous_id") == meta["internal_id"] for m in records.values()):
        raise CatalogError("a later version follows this draft, so it cannot be discarded")
    _refuse_blocked(records, meta["slug"], allow_attachment=True)
    _check_expected(meta, args.expect_sha256, text_only=True)
    path = _inside(root, root / meta["_path"])
    paths = [m["_path"] for m in records.values()]
    new_cat = dict(cat)
    if meta["version"] == 1:
        new_cat["catalog_version"] = max(2, cat["catalog_version"])
        new_cat["reserved_slugs"] = [*(cat.get("reserved_slugs") or []), meta["slug"]]
    # catalog.yaml first: an interrupt then leaves an unlisted draft, which discard-orphan removes,
    # instead of a listed record that is missing.
    write_catalog(root, new_cat, [p for p in paths if p != meta["_path"]])
    try:
        path.unlink(missing_ok=True)  # already gone: relisting it would break the catalog
    except OSError:
        write_catalog(root, cat, paths)  # nothing was deleted: list it again
        raise
    with contextlib.suppress(OSError):
        path.parent.rmdir()  # only succeeds when the slug folder is now empty
    info.update(
        ok=True,
        removed=meta["_path"],
        slug=meta["slug"],
        internal_id=meta["internal_id"],
        slug_reserved=meta["version"] == 1,
    )
    return info


def cmd_record_verification(args) -> dict:
    info, root, cat, records = _load(args)
    _need_ok(info)
    meta = _record_by_id(records, args.internal_id)
    if meta["status"] != "draft":
        raise CatalogError("verification is recorded only on a draft (editing a draft clears it)")
    if args.kind == "import" and meta["origin"] not in ("session", "web"):
        raise CatalogError("an import hash is only recorded for session or web origin")
    _refuse_blocked(records, meta["slug"], allow_attachment=True)
    _check_expected(meta, args.expect_sha256)
    _assert_clean(meta)
    ver = dict(meta.get("verification") or {})
    ver[args.kind] = meta["_fingerprint"]
    if meta["_version"] >= 3:
        ver["core"] = core_hash(meta)  # tells a later attachment change from a text change
    meta["verification"] = ver
    write_record(_inside(root, root / meta["_path"]), meta)
    info["ok"] = True
    info["recorded"] = {args.kind: ver[args.kind]}
    return info


def cmd_upgrade(args) -> dict:
    """Move a version 1 or 2 catalog to version 3 (SEC-4). Without --expect-listing it only lists
    the approved prompts whose fingerprint would then also bind their origin; with it, it rebinds
    each one whose text still matches, then writes catalog.yaml last. Refused while any record lists
    attachments (they were never loaded or reviewed) or any prompt is blocked."""
    info, root, cat, records = _load(args)
    _need_ok(info)
    if cat["catalog_version"] >= CURRENT_CATALOG_VERSION:
        raise CatalogError(f"the catalog is already at version {cat['catalog_version']}")
    listing = [m["_path"] for m in records.values() if m.get("attachments")]
    if listing:
        raise CatalogError(
            "records list attachments, which were never loaded or reviewed before version 3: "
            + ", ".join(sorted(listing)[:5])
        )
    blocked = [m["slug"] for m in records.values() if m.get("_blocked")]
    if blocked:
        raise CatalogError(
            "restore or retire the prompts that changed since their approval first: "
            + ", ".join(sorted(set(blocked)))
        )
    approved = [m for m in records.values() if m["status"] in ("active", "inactive")]
    info["records"] = [
        {
            "slug": m["slug"],
            "internal_id": m["internal_id"],
            "version": m["version"],
            "status": m["status"],
            "origin": m["origin"],
            "text_hash": text_hash(m["_body"]),
        }
        for m in approved
    ]
    # The listing id binds the apply step to exactly what the user saw, origins included: a record
    # edit leaves catalog.yaml's snapshot_id unchanged, and before version 3 a relabelled origin
    # does not block its prompt.
    info["listing_id"] = _tagged_hash(
        {"upgrade": cat.get("snapshot_id"), "records": info["records"]}
    )
    if args.expect_listing is None:
        info.update(ok=True, applied=False)
        return info
    if args.expect_listing != info["listing_id"]:
        raise CatalogError("the catalog changed since the upgrade was shown (listing differs)")
    undo: list[tuple[Path, str]] = []
    try:
        for meta in approved:
            path = _inside(root, root / meta["_path"])
            undo.append((path, path.read_bytes().decode("utf-8")))
            meta["_version"] = CURRENT_CATALOG_VERSION
            fingerprint = fingerprint_of(meta, [])
            meta["verification"] = {k: fingerprint for k in meta["verification"]}
            meta["verification"]["core"] = core_hash(meta)
            write_record(path, meta)
        write_catalog(root, {**cat, "catalog_version": CURRENT_CATALOG_VERSION}, list(records))
    except BaseException:
        if _catalog_committed(root, cat):
            raise
        for path, text in reversed(undo):
            try:
                _write_atomic(path, text)
            except (OSError, ValueError):
                break  # validate shows what is left; restore the rest from git
        raise
    info.update(ok=True, applied=True, catalog_version=CURRENT_CATALOG_VERSION)
    return info


def _move(root: Path, meta: dict, new_status: str, paths: list[str]) -> Callable[[], None]:
    """Move a record to new_status. Returns a step that undoes the move, so the caller can roll back
    earlier moves when a later move or the catalog.yaml write fails."""
    old_rel = meta["_path"]
    new_name = "active.md" if new_status == "active" else f"{meta['internal_id']}.md"
    new_rel = f"{meta['slug']}/{new_name}"
    old_path, new_path = _inside(root, root / old_rel), _inside(root, root / new_rel)
    old_status = meta["status"]
    meta["status"] = new_status

    def undo() -> None:
        meta["status"] = old_status
        if new_rel != old_rel:
            new_path.replace(old_path)
        write_record(old_path, meta)

    if new_rel == old_rel:
        try:
            write_record(old_path, meta)
        except BaseException:
            meta["status"] = old_status
            raise
        return undo
    # Rename first, then write the new status into the moved file, so a failure at any point leaves
    # a record whose status still matches its file name (the rename is undone if the write fails).
    try:
        old_path.replace(new_path)
    except BaseException:
        meta["status"] = old_status
        raise
    try:
        write_record(new_path, meta)
    except BaseException:
        meta["status"] = old_status
        try:
            new_path.replace(old_path)
        except OSError:
            pass  # the original error is the one worth reporting; validate will show the mismatch
        raise
    paths[paths.index(old_rel)] = new_rel
    meta["_path"] = new_rel
    return undo


def _lifecycle(args, op: str) -> dict:
    info, root, cat, records = _load(args)
    _need_ok(info)
    paths = [m["_path"] for m in records.values()]
    meta = _record_by_id(records, args.internal_id)
    group = [m for m in records.values() if m["slug"] == meta["slug"]]
    active = next((m for m in group if m["status"] == "active"), None)
    undo_steps: list[Callable[[], None]] = []
    if op != "retire":
        _refuse_blocked(records, meta["slug"], allow_attachment=op == "finalize")
    try:
        if op == "retire":
            if not meta.get("_blocked"):
                raise CatalogError("only a prompt that changed since its approval can be retired")
            _check_expected(meta, args.expect_sha256, text_only=True)
            undo_steps.append(_move(root, meta, "historical", paths))
        elif op == "deactivate":
            if meta["status"] != "active":
                raise CatalogError("only an active record can be deactivated")
            undo_steps.append(_move(root, meta, "inactive", paths))
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
            undo_steps.append(_move(root, meta, "active", paths))
        else:  # finalize
            if meta["status"] != "draft" or not meta.get("previous_id"):
                raise CatalogError("finalize applies to a draft successor (one with previous_id)")
            _check_expected(meta, args.expect_sha256)
            _assert_clean(meta)
            problems = hash_problems(meta)
            if problems:
                raise CatalogError("not verified: " + "; ".join(problems))
            pred = _record_by_id(records, meta["previous_id"])
            if pred.get("_attachment_change") and core_hash(pred) != core_hash(meta):
                raise CatalogError(_same_core_as_blocked(meta, records)[0])
            if pred["status"] not in ("active", "inactive"):
                raise CatalogError("the predecessor is neither active nor inactive")
            if pred["status"] == "inactive" and not args.active and not args.inactive:
                raise CatalogError("predecessor is inactive: pass --active or --inactive to choose")
            goes_active = args.active or (pred["status"] == "active" and not args.inactive)
            undo_steps.append(_move(root, pred, "historical", paths))
            undo_steps.append(_move(root, meta, "active" if goes_active else "inactive", paths))
        write_catalog(root, cat, paths)  # catalog.yaml last, after every record move succeeded
    except BaseException:
        if _catalog_committed(root, cat):
            raise  # catalog.yaml already lists the moved records: undoing would break it
        # A move or the catalog write failed: put every record that already moved back, newest
        # first, so catalog.yaml (still listing the old paths) and the files on disk agree again.
        # If an undo itself fails, stop: undoing an earlier move on top of a half-restored state
        # could overwrite a file (both records can share active.md). The error worth reporting is
        # still the original one, and validate shows what is left.
        for undo in reversed(undo_steps):
            try:
                undo()
            except (OSError, ValueError):
                break
        raise
    info["ok"] = True
    info["status"] = meta["status"]
    return info


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--root", help="catalog root override (validated by the same path trust boundary)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--search", help="list only records whose labels or prompt text contain this")
    s = sub.add_parser("show")
    s.add_argument("slug")
    s.add_argument("--history", action="store_true")
    sub.add_parser("review-bundle").add_argument("internal_id")
    up = sub.add_parser("upgrade")
    up.add_argument("--expect-listing", help="the listing_id shown with the upgrade listing")
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
    dd = sub.add_parser("discard-draft")
    dd.add_argument("internal_id")
    dd.add_argument("--expect-sha256", required=True, help="the hash shown to the user")
    rv = sub.add_parser("record-verification")
    rv.add_argument("internal_id")
    rv.add_argument("--kind", choices=("quality", "import"), required=True)
    rv.add_argument(
        "--expect-sha256", required=True, help="the hash shown to the user when they approved"
    )
    sub.add_parser("deactivate").add_argument("internal_id")
    rt = sub.add_parser("retire")
    rt.add_argument("internal_id")
    rt.add_argument("--expect-sha256", required=True, help="the hash shown to the user")
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
    "review-bundle": cmd_review_bundle,
    "upgrade": cmd_upgrade,
    "hash": cmd_hash,
    "screen": cmd_screen,
    "init": cmd_init,
    "new-id": cmd_new_id,
    "draft": cmd_draft,
    "update-draft": cmd_update_draft,
    "register": cmd_register,
    "discard-orphan": cmd_discard_orphan,
    "discard-draft": cmd_discard_draft,
    "record-verification": cmd_record_verification,
    "activate": lambda a: _lifecycle(a, "activate"),
    "deactivate": lambda a: _lifecycle(a, "deactivate"),
    "finalize": lambda a: _lifecycle(a, "finalize"),
    "retire": lambda a: _lifecycle(a, "retire"),
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = COMMANDS[args.cmd](args)
    except CatalogError as exc:
        result = {"ok": False, "error": str(exc)}
    except OSError as exc:
        result = {"ok": False, "error": f"filesystem error: {exc}"}
    except (ValueError, TypeError, KeyError) as exc:
        # ValueError includes UnicodeError (a value that cannot be encoded as UTF-8). TypeError and
        # KeyError come from a hand-edited record with a wrongly typed or missing field that the
        # checks did not guard: still a JSON error, never a traceback.
        result = {"ok": False, "error": f"invalid content: {type(exc).__name__}: {exc}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


def _use_utf8_streams() -> None:
    """Read stdin and write stdout as UTF-8 whatever the console code page is, and never let an
    unencodable character crash the final print."""
    for stream, errors in ((sys.stdin, "strict"), (sys.stdout, "backslashreplace")):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors=errors)


if __name__ == "__main__":
    _use_utf8_streams()
    sys.exit(main())
