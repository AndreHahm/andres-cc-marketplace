#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Canonical SHA-256 of a batch submission file, for plugin-integration-intake's
hash-bound batch approval (see skills/plugin-integration-intake/references/
wmgt-intake-batch-contract.md).

Subcommands:
    hash    <file>                         print {"ok": true, "sha256": ..., "record_count": N}
    verify  <file> <sha256>                same, but a typed failure on a hash mismatch
    show    <file> <sha256>                verify, then print the submission header only
                                           (everything except "records"), plus record_count
    preview <file> <sha256> <start> <end>  verify, then print one compact table row per record
                                           in [start, end) (at most 100 rows, at most 20000
                                           bytes) and, for the first three records of the batch
                                           when in range, their full description plus a backtick
                                           "fence" to render it in; cell text is made safe for a
                                           markdown table, chunk output is never altered
    chunk   <file> <sha256> <start> <end>  verify, then print operation, environment, team_id,
                                           linear_target, source_plugin, source_skill and the
                                           records [start, end) exactly as hashed (at most 25
                                           records and 20000 bytes), so a write is built from
                                           verified output and not from a second read
    purge   <scratch-root> <file>          delete a submission or progress file, only when it is
                                           directly inside <scratch-root>/wmgt-intake and has an
                                           intake-generated name (the only mutating command)

The preview and chunk outputs carry "bytes" (the size of what was printed) so a truncated
tool result can be recognised.

The file must be a regular (non-symlink) UTF-8 JSON object with: "operation" (create or
update), "environment" (production or test), a non-empty string "team_id", a normalized
"linear_target" slug, "source_plugin" and "source_skill" names, a "batch_id"
nonce (intake generates a fresh one for every submission, including a resume, so the same
records never hash the same twice), and a non-empty "records" array. Records are checked
against a per-operation field allowlist and typed (strings; labels as a bounded array of
strings; title, status, priority, owner and id are length-capped, labels bounded), and a create
record must carry a non-blank title, description and status.
Duplicate JSON keys and non-finite numbers (NaN, Infinity) anywhere are refused, and the
source_plugin, source_skill and linear_target fields are pattern-checked. Every record must also
fit a one-record chunk and a one-row preview, so none can be hashed yet never written or shown. The
hash covers the whole object, serialized canonically (sorted keys, no whitespace, ASCII
escapes).

What this does and does not do: it binds an approval to the bytes of one file, and lets a
write be built from those bytes. It cannot bind the model's own connector-call arguments to
the file; that gap is inherent to a model-executed gate and is disclosed in the contract.
Symlink and hard-link refusal is best effort on Windows.

Except for --help (argparse's own help text, exit 0), always prints one JSON object on stdout.
Exit 0 on success, 1 on a typed failure (never a traceback; an unexpected error is reported by
its type name only).
"""

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata

MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 1000
MAX_CHUNK = 25
MAX_PREVIEW_ROWS = 100
MAX_OUTPUT_BYTES = 20000
EXCERPT_CHARS = 120
FULL_DESCRIPTION_COUNT = 3
SCRATCH_DIR_NAME = "wmgt-intake"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BATCH_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_TEAM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_KEBAB_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}/[a-z0-9][a-z0-9._-]{0,99}$")
_CREATE_REQUIRED = ("title", "description", "status")
_PURGE_NAME_RE = re.compile(
    r"^(?:[A-Za-z0-9._-]{8,64}\.json|[0-9a-f]{64}-[A-Za-z0-9._-]{8,64}\.progress\.json)$"
)
_OPERATIONS = {"create", "update"}
_ENVIRONMENTS = {"production", "test"}
_CREATE_FIELDS = {"title", "description", "status", "priority", "labels"}
_UPDATE_SET_FIELDS = {"title", "status", "labels", "priority", "owner"}
_UPDATE_RECORD_KEYS = {"id", "set", "before"}
_TOP_LEVEL_KEYS = {
    "operation",
    "environment",
    "team_id",
    "batch_id",
    "linear_target",
    "source_plugin",
    "source_skill",
    "records",
}
_STRING_FIELDS = {"title", "description", "status", "priority", "owner"}
MAX_LABELS = 20
MAX_LABEL_CHARS = 100
_FIELD_CAPS = {"title": 256, "status": 100, "priority": 32, "owner": 100}
MAX_ID_CHARS = 100
BS = chr(92)
_MD_PUNCT = "[]()!*_~#"


class HashError(Exception):
    pass


def _reject_constant(name):
    """Reject NaN and Infinity at parse time so no output can be non-standard JSON."""
    raise HashError(f"non-finite number {name} is not allowed")


def _no_duplicate_keys(pairs):
    """Build a JSON object, refusing any duplicate key."""
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise HashError(f"duplicate JSON key: {key[:64]!r}")
        seen[key] = value
    return seen


def _check_value(where: str, field: str, value, allow_none: bool = False) -> None:
    """Check one record field's type; ``allow_none`` lets an unset ``before`` field be null."""
    if value is None and allow_none:
        return
    if field in _STRING_FIELDS:
        if not isinstance(value, str):
            raise HashError(f"{where}: {field!r} must be a string")
        if len(value) > _FIELD_CAPS.get(field, len(value)):
            raise HashError(f"{where}: {field!r} is longer than {_FIELD_CAPS[field]} characters")
    elif field == "labels":
        if (
            not isinstance(value, list)
            or len(value) > MAX_LABELS
            or not all(isinstance(v, str) and 0 < len(v) <= MAX_LABEL_CHARS for v in value)
        ):
            raise HashError(
                f"{where}: 'labels' must be an array of at most {MAX_LABELS} non-empty strings"
                f" of at most {MAX_LABEL_CHARS} characters"
            )


def _check_records(operation: str, records: list) -> None:
    """Check every record against the per-operation field allowlist and value types."""
    for index, record in enumerate(records):
        where = f"record {index}"
        if not isinstance(record, dict) or not record:
            raise HashError(f"{where} must be a non-empty object")
        if operation == "create":
            extra = set(record) - _CREATE_FIELDS
            if extra:
                shown = sorted(k[:64] for k in extra)[:10]
                raise HashError(f"{where} has fields not allowed on create: {shown}")
            for field in _CREATE_REQUIRED:
                value = record.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise HashError(
                        f"{where}: {field!r} is required and must be a non-blank string"
                    )
            for field, value in record.items():
                _check_value(where, field, value)
        else:
            extra = set(record) - _UPDATE_RECORD_KEYS
            if extra or "id" not in record or "set" not in record:
                raise HashError(f'{where} must hold "id" and "set" (and "before") only')
            if not isinstance(record["id"], str) or not record["id"].strip():
                raise HashError(f"{where} needs a non-empty string id")
            if len(record["id"]) > MAX_ID_CHARS:
                raise HashError(f"{where}: id is longer than {MAX_ID_CHARS} characters")
            changes = record["set"]
            if not isinstance(changes, dict) or not changes or set(changes) - _UPDATE_SET_FIELDS:
                allowed = sorted(_UPDATE_SET_FIELDS)
                raise HashError(f'{where} "set" must be a non-empty object limited to {allowed}')
            for field, value in changes.items():
                _check_value(where + " set", field, value)
            before = record.get("before")
            if (
                not isinstance(before, dict)
                or set(before) - _UPDATE_SET_FIELDS
                or "title" not in before
                or not set(changes) <= set(before)
            ):
                raise HashError(
                    f'{where} "before" must hold the current "title" and every field named in "set"'
                )
            if not isinstance(before["title"], str) or not before["title"].strip():
                raise HashError(f'{where} "before" needs a non-blank string title')
            for field, value in before.items():
                _check_value(where + " before", field, value, allow_none=True)


def _check_records_fit_a_chunk(data: dict) -> None:
    """Refuse a submission holding a record that could never be written in a one-record chunk."""
    head = {
        key: data[key]
        for key in (
            "operation",
            "environment",
            "team_id",
            "linear_target",
            "source_plugin",
            "source_skill",
        )
    }
    for index, record in enumerate(data["records"]):
        probe = {
            "ok": True,
            "sha256": "0" * 64,
            "record_count": len(data["records"]),
            **head,
            "start": index,
            "records": [record],
        }
        if _sized(probe) > MAX_OUTPUT_BYTES:
            raise HashError(
                f"record {index} is too large to write or preview: its one-record chunk would "
                f"exceed {MAX_OUTPUT_BYTES} bytes"
            )
        shown = _preview_result(data, "0" * 64, index, index + 1)
        if _sized(shown) > MAX_OUTPUT_BYTES:
            raise HashError(
                f"record {index} is too large to write or preview: its one-row preview would "
                f"exceed {MAX_OUTPUT_BYTES} bytes"
            )


def load_submission(path_str: str) -> dict:
    """Read and validate a submission file; return the parsed object or raise HashError."""
    if os.path.islink(path_str):
        raise HashError("symlinks are refused")
    try:
        fd = os.open(
            path_str,
            os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise HashError(f"cannot open file: {exc.strerror}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise HashError("not a regular file")
        if info.st_nlink > 1:
            raise HashError("hard-linked files are refused")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(MAX_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_BYTES:
        raise HashError(f"file exceeds {MAX_BYTES} bytes")
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except HashError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError, MemoryError) as exc:
        raise HashError(f"invalid or too deeply nested UTF-8 JSON: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise HashError("top level must be a JSON object")
    unexpected = set(data) - _TOP_LEVEL_KEYS
    if unexpected:
        raise HashError(f"unexpected top-level keys: {sorted(k[:64] for k in unexpected)[:10]}")
    for key in ("source_plugin", "source_skill"):
        if not (isinstance(data.get(key), str) and _KEBAB_RE.fullmatch(data[key])):
            raise HashError(
                f"{key!r} is required and must be a lowercase kebab-case name (max 64 characters)"
            )
    if not (
        isinstance(data.get("linear_target"), str) and _SLUG_RE.fullmatch(data["linear_target"])
    ):
        raise HashError('"linear_target" is required and must be a lowercase owner/repo slug')
    if not (isinstance(data.get("operation"), str) and data["operation"] in _OPERATIONS):
        raise HashError('"operation" must be "create" or "update"')
    if not (isinstance(data.get("environment"), str) and data["environment"] in _ENVIRONMENTS):
        raise HashError('"environment" must be "production" or "test"')
    team_id = data.get("team_id")
    if not isinstance(team_id, str) or not _TEAM_ID_RE.fullmatch(team_id):
        raise HashError('"team_id" must match ^[A-Za-z0-9_-]{1,64}$')
    batch_id = data.get("batch_id")
    if not isinstance(batch_id, str) or not _BATCH_ID_RE.fullmatch(batch_id):
        raise HashError('"batch_id" must match ^[A-Za-z0-9._-]{8,64}$')
    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise HashError('"records" must be a non-empty array')
    if len(records) > MAX_RECORDS:
        raise HashError(f'"records" exceeds {MAX_RECORDS} entries')
    _check_records(data["operation"], records)
    _check_records_fit_a_chunk(data)
    return data


def digest_of(data: dict) -> str:
    """Return the SHA-256 of the canonical (sorted, compact, ASCII) JSON form of ``data``."""
    canonical = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _require_hash(expected: str) -> None:
    """Refuse an expected hash that is not 64 lowercase hex characters."""
    if not _SHA256_RE.fullmatch(expected):
        raise HashError("expected hash is not 64 lowercase hex characters")


def _range(args, total: int, limit: int, label: str) -> None:
    """Check that ``[start, end)`` is inside the records and no longer than ``limit``."""
    if not (0 <= args.start < args.end <= total):
        raise HashError(f"{label} range is outside the records array")
    if args.end - args.start > limit:
        raise HashError(f"{label} exceeds {limit} records")


def _excerpt(value) -> str:
    """Return ``value`` as text, cut to EXCERPT_CHARS characters with an ellipsis if longer."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)
    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS] + "..."


def _visible_controls(text: str, keep: str = "") -> str:
    """Show control and format characters (bidi, zero-width, ESC...) as visible backslash-u text."""
    out = []
    for ch in text:
        if ch not in keep and unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp"):
            code = ord(ch)
            out.append(f"{BS}u{code:04x}" if code <= 0xFFFF else f"{BS}U{code:08x}")
        else:
            out.append(ch)
    return "".join(out)


def _safe(value):
    """Make preview text inert in a markdown table cell.

    Line breaks become spaces, a backslash is escaped first so a trailing one cannot cancel
    later escapes, then markdown punctuation, '&' (so an entity cannot rebuild a character),
    '<', backtick and the pipe are neutralised, and control or format characters are made visible.
    """
    if isinstance(value, str):
        text = re.sub("[\r\n\v\f\x85\u2028\u2029]", " ", value).replace(BS, BS + BS)
        for ch in _MD_PUNCT:
            text = text.replace(ch, BS + ch)
        text = (
            text.replace("&", "&amp;").replace("<", "&lt;").replace("`", "'").replace("|", BS + "|")
        )
        return _visible_controls(text)
    if isinstance(value, list):
        return [_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    return value


def _row(index: int, record: dict, operation: str) -> dict:
    """Build one compact preview row for a record; text is made safe for a markdown table."""
    if operation == "create":
        return {
            "index": index,
            "title": _safe(record.get("title")),
            "status": _safe(record.get("status")),
            "labels": _safe(record.get("labels")),
            "priority": _safe(record.get("priority")),
            "description_excerpt": _safe(_excerpt(record.get("description", ""))),
        }
    before = record.get("before", {})
    return {
        "index": index,
        "id": _safe(record["id"]),
        "title": _safe(before.get("title")),
        "set": _safe(record["set"]),
        "before": _safe({k: v for k, v in before.items() if k != "title"}),
    }


def _preview_result(data: dict, digest: str, start: int, end: int) -> dict:
    """Build the preview output for records [start, end); shared by ``run`` and the fit probe."""
    records = data["records"]
    result = {"ok": True, "sha256": digest, "record_count": len(records), "start": start}
    result["rows"] = [_row(i, records[i], data["operation"]) for i in range(start, end)]
    result["full_descriptions"] = [
        {
            "index": i,
            "description": _safe_block(records[i].get("description")),
            "fence": _fence_for(_safe_block(records[i].get("description"))),
        }
        for i in range(start, min(end, FULL_DESCRIPTION_COUNT))
        if data["operation"] == "create"
    ]
    return result


def _safe_block(value):
    """Show control and format characters in a full description as visible text; keep newlines."""
    return _visible_controls(value, keep="\n\t") if isinstance(value, str) else value


def _fence_for(text) -> str:
    """Return a backtick fence longer than any backtick run in ``text`` (at least three)."""
    longest = max((len(run) for run in re.findall("`+", text or "")), default=0)
    return "`" * max(3, longest + 1)


def _sized(result: dict) -> int:
    """Add a ``bytes`` field holding the final size of the printed JSON, itself included.

    Returns that size. It is found by fixed-point iteration so the figure the model sees is
    the figure it received.
    """
    size = 0
    for _ in range(5):
        result["bytes"] = size
        new_size = len(json.dumps(result).encode("utf-8"))
        if new_size == size:
            break
        size = new_size
    return size


def run(args) -> dict:
    """Run hash, verify, show, preview or chunk and return the result object."""
    data = load_submission(args.file)
    digest = digest_of(data)
    records = data["records"]
    result = {"ok": True, "sha256": digest, "record_count": len(records)}
    if args.command in ("verify", "show", "preview", "chunk"):
        _require_hash(args.sha256)
        if digest != args.sha256:
            raise HashError(f"hash mismatch (file hashes to {digest})")
    if args.command == "show":
        result["submission"] = {k: v for k, v in data.items() if k != "records"}
    if args.command == "preview":
        _range(args, len(records), MAX_PREVIEW_ROWS, "preview")
        result = _preview_result(data, digest, args.start, args.end)
    if args.command == "chunk":
        _range(args, len(records), MAX_CHUNK, "chunk")
        result["operation"] = data["operation"]
        result["environment"] = data["environment"]
        result["team_id"] = data["team_id"]
        result["linear_target"] = data["linear_target"]
        result["source_plugin"] = data["source_plugin"]
        result["source_skill"] = data["source_skill"]
        result["start"] = args.start
        result["records"] = records[args.start : args.end]
    if args.command in ("preview", "chunk"):
        # Size first, then enforce the cap on the final output, "bytes" field included.
        if _sized(result) > MAX_OUTPUT_BYTES:
            raise HashError(f"output exceeds {MAX_OUTPUT_BYTES} bytes; request a smaller range")
    return result


def _unlink_in_dir(directory: str, name: str) -> None:
    """Delete <directory>/<name> without re-resolving the path where the platform allows.

    On POSIX the directory is opened once, the entry is checked with lstat semantics relative
    to that descriptor, and unlinked relative to it, so swapping a path component between the
    check and the delete cannot redirect the delete. Where dir_fd is unsupported (Windows) this
    falls back to a pathname check followed by os.remove, which leaves a small race.
    """
    if (
        os.unlink in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and hasattr(os, "O_DIRECTORY")
    ):
        dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                raise HashError("refused: not a regular file")
            os.unlink(name, dir_fd=dir_fd)
        finally:
            os.close(dir_fd)
        return
    path = os.path.join(directory, name)
    if os.path.islink(path) or not os.path.isfile(path):
        raise HashError("refused: not a regular file")
    os.remove(path)


def purge(scratch_root: str, path_str: str) -> dict:
    """Delete one intake-generated scratch file, only inside ``<scratch_root>/wmgt-intake``."""
    expected_dir = os.path.realpath(os.path.join(scratch_root, SCRATCH_DIR_NAME))
    path = os.path.abspath(path_str)
    if os.path.realpath(os.path.dirname(path)) != expected_dir:
        raise HashError(f"refused: file is not directly inside <scratch-root>/{SCRATCH_DIR_NAME}")
    name = os.path.basename(path)
    if not _PURGE_NAME_RE.fullmatch(name):
        raise HashError("refused: not an intake-generated file name")
    try:
        _unlink_in_dir(expected_dir, name)
    except OSError as exc:
        raise HashError(f"cannot delete: {exc.strerror or exc}") from exc
    return {"ok": True, "purged": True}


def main(argv=None) -> int:
    """Parse arguments, run the command and print exactly one JSON object; return the exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or "wmgt_batch_hash").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hash").add_argument("file")
    p_purge = sub.add_parser("purge")
    p_purge.add_argument("scratch_root")
    p_purge.add_argument("file")
    for name in ("verify", "show"):
        p_named = sub.add_parser(name)
        p_named.add_argument("file")
        p_named.add_argument("sha256")
    for name in ("preview", "chunk"):
        p_ranged = sub.add_parser(name)
        p_ranged.add_argument("file")
        p_ranged.add_argument("sha256")
        p_ranged.add_argument("start", type=int)
        p_ranged.add_argument("end", type=int)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            return 0  # --help: argparse already printed its help text
        # argparse exits 2 on its own; keep the typed-failure contract instead.
        print(json.dumps({"ok": False, "error": "invalid arguments"}))
        return 1
    try:
        result = purge(args.scratch_root, args.file) if args.command == "purge" else run(args)
    except HashError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    except (RecursionError, MemoryError, ValueError):
        print(json.dumps({"ok": False, "error": "input too deeply nested or too large"}))
        return 1
    except Exception as exc:  # last resort: keep the one-JSON-object contract
        print(json.dumps({"ok": False, "error": f"unexpected failure: {type(exc).__name__}"}))
        return 1
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
