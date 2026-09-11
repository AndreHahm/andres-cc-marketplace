#!/usr/bin/env python3
"""Append-only lifecycle registry for analysis-kit's tracking-recommendation-lifecycle skill.

Stores one JSON Lines event per recommendation status change at a shared registry path
(default: .claude/output/analysis-kit-recommendations/events.jsonl -- not scoped under any
one skill's own .claude/output/<skill>/ directory, since the registry spans every
recommendation regardless of which skill originated it). Each append is one buffered
write() of a single line, guarded by a companion "<registry>.lock" file acquired via a
retry-with-timeout loop over plain os.open(O_CREAT|O_EXCL) -- portable across Windows and
POSIX with no fcntl/msvcrt branching and no new dependency, per AKR-NFR-002. A writer that
cannot acquire the lock within the timeout raises TimeoutError rather than silently
dropping the event, per AKR-019. A lock older than LOCK_STALE_SECONDS is treated as
orphaned (its writer crashed before releasing it) and broken automatically. Read-only
operations (show/list/validate) take the same lock before reading, so a reader never
observes a write in progress.

Event fields: recommendation_id, timestamp, status (required); source_report, actor,
rationale, evidence, expected_effect, observed_effect (optional -- a historical record
missing any of these is valid and simply omits the field, per AKR-NFR-005).

CLI operations: init, append, show, list, validate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REGISTRY_PATH = ".claude/output/analysis-kit-recommendations/events.jsonl"

# A lock file older than this is treated as orphaned (its writer crashed before releasing
# it) and broken automatically, rather than deadlocking every future writer forever.
LOCK_STALE_SECONDS = 300.0

REQUIRED_FIELDS = ("recommendation_id", "timestamp", "status")
OPTIONAL_FIELDS = (
    "source_report",
    "actor",
    "rationale",
    "evidence",
    "expected_effect",
    "observed_effect",
)

INITIAL_STATUS = "proposed"

# Every status a recommendation can be in. "reopened" is itself a real status (not just a
# transition label) so a reopened item's own current state is queryable before it's moved
# back into the normal pipeline.
STATUSES = frozenset(
    {
        "proposed",
        "accepted",
        "declined",
        "implemented",
        "verified",
        "measured",
        "closed",
        "reopened",
        "superseded",
    }
)

# Keyed by current status -> the set of statuses a next event may legally move to. A
# recommendation with no prior event at all is represented by the virtual predecessor
# `None`, whose only valid next status is INITIAL_STATUS -- every recommendation must
# start at "proposed".
VALID_TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset({INITIAL_STATUS}),
    "proposed": frozenset({"accepted", "declined", "superseded"}),
    "accepted": frozenset({"implemented", "declined", "superseded"}),
    "implemented": frozenset({"verified", "superseded"}),
    "verified": frozenset({"measured", "superseded"}),
    "measured": frozenset({"closed", "superseded"}),
    "declined": frozenset({"reopened", "superseded"}),
    "closed": frozenset({"reopened", "superseded"}),
    "reopened": frozenset({"accepted", "implemented", "superseded"}),
    "superseded": frozenset(),  # terminal -- nothing may follow a superseded event.
}


def validate_transition(current_status: str | None, new_status: str) -> tuple[bool, str]:
    """Returns (ok, reason). `current_status` is None for a recommendation_id with no
    prior event -- the only valid new_status in that case is INITIAL_STATUS."""
    if new_status not in STATUSES:
        return False, f"'{new_status}' is not a recognized status"
    allowed = VALID_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        current_label = current_status if current_status is not None else "(no prior event)"
        return (
            False,
            f"invalid transition: '{current_label}' -> '{new_status}' is not allowed "
            f"(allowed from '{current_label}': {sorted(allowed) or 'none'})",
        )
    return True, "ok"


def read_events(registry_path: Path) -> list[dict]:
    """Reads every event in file order. Returns [] if the registry doesn't exist yet --
    a missing registry is a valid, empty starting state, not an error. Raises ValueError
    (not silently skipping) if a line decodes to valid JSON that isn't itself an object --
    a hand-corrupted or truncated registry should be reported, not misread as an empty
    event with no recommendation_id/status."""
    if not registry_path.exists():
        return []
    events = []
    # newline="\n" pins LF-only on both read and write -- without it, Python's default
    # text-mode translation would append CRLF on Windows, corrupting the file for any
    # external LF-only JSON-Lines tool even though this module's own reader tolerates it.
    with registry_path.open(encoding="utf-8", newline="\n") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            parsed = json.loads(line)
            if not isinstance(parsed, dict):
                raise ValueError(f"{registry_path}: line {i} is not a JSON object: {line[:80]!r}")
            events.append(parsed)
    return events


def read_events_locked(registry_path: Path, *, lock_timeout: float = 10.0) -> list[dict]:
    """Read-only access under the same lock a writer takes, so a reader never observes a
    write in progress -- relevant if the underlying filesystem doesn't guarantee a
    writer's single write() call is atomic (true for typical local POSIX/NTFS appends,
    not guaranteed on every network filesystem)."""
    lock_path = registry_path.with_name(registry_path.name + ".lock")
    acquire_lock(lock_path, timeout=lock_timeout)
    try:
        return read_events(registry_path)
    finally:
        release_lock(lock_path)


def latest_status(events: list[dict], recommendation_id: str) -> str | None:
    """The most recent status for one recommendation_id, in file order -- None if no
    event exists for it yet."""
    status = None
    for event in events:
        if event.get("recommendation_id") == recommendation_id:
            status = event.get("status")
    return status


def acquire_lock(lock_path: Path, timeout: float = 10.0, poll: float = 0.05) -> None:
    """Acquires the companion lock file via exclusive create, retrying until timeout.
    Raises TimeoutError rather than returning False -- a writer that can't get the lock
    must fail loudly, per AKR-019, never silently skip the append it was asked to make.
    A lock older than LOCK_STALE_SECONDS is treated as orphaned (its writer crashed
    before reaching the release in append_event's `finally`) and broken automatically --
    without this, one crashed writer would deadlock every future writer permanently, with
    no recovery path short of a human finding and deleting the lock file by hand."""
    start = time.monotonic()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError as exc:
            try:
                if time.time() - lock_path.stat().st_mtime > LOCK_STALE_SECONDS:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass  # lock vanished between the failed open and this stat -- benign, just retry
            if time.monotonic() - start > timeout:
                raise TimeoutError(
                    f"could not acquire lock {lock_path} within {timeout}s -- another writer may "
                    f"be active, or (if older than {LOCK_STALE_SECONDS}s) should have been "
                    "auto-broken above; if this persists, confirm no writer is actually running "
                    "and delete the lock file manually"
                ) from exc
            time.sleep(poll)


def release_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


def append_event(registry_path: Path, event: dict, *, lock_timeout: float = 10.0) -> None:
    """Validates the transition against the registry's current state for this
    recommendation_id, then appends exactly one JSON Line under the companion lock.
    Raises ValueError on an invalid transition (nothing is written); raises TimeoutError
    if the lock can't be acquired in time."""
    missing = [f for f in REQUIRED_FIELDS if f not in event]
    if missing:
        raise ValueError(f"event missing required field(s): {', '.join(missing)}")

    # The parent directory must exist *before* acquire_lock -- os.open(O_CREAT|O_EXCL)
    # raises FileNotFoundError (not FileExistsError) against a nonexistent directory, which
    # the lock's own retry loop doesn't catch, so a fresh --registry path with no prior
    # `init` call would otherwise crash the very first append with an unhandled traceback.
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = registry_path.with_name(registry_path.name + ".lock")
    acquire_lock(lock_path, timeout=lock_timeout)
    try:
        existing = read_events(registry_path)
        current = latest_status(existing, event["recommendation_id"])
        ok, reason = validate_transition(current, event["status"])
        if not ok:
            raise ValueError(reason)

        line = json.dumps(event, ensure_ascii=False) + "\n"
        with registry_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line)  # single buffered write() call -- append-only, no rewrite.
    finally:
        release_lock(lock_path)


def list_recommendations(events: list[dict]) -> list[dict]:
    """One row per recommendation_id: {recommendation_id, current_status, last_updated}."""
    latest: dict[str, dict] = {}
    for event in events:
        rec_id = event.get("recommendation_id")
        if rec_id is None:
            continue
        latest[rec_id] = event
    return [
        {
            "recommendation_id": rec_id,
            "current_status": event.get("status"),
            "last_updated": event.get("timestamp"),
        }
        for rec_id, event in latest.items()
    ]


def show_recommendation(events: list[dict], recommendation_id: str) -> list[dict]:
    """Full event history for one recommendation_id, in file order."""
    return [e for e in events if e.get("recommendation_id") == recommendation_id]


def validate_registry(registry_path: Path) -> list[str]:
    """Replays every event in file order, checking each recommendation_id's transitions
    against VALID_TRANSITIONS. Returns a list of human-readable violation descriptions --
    empty means the registry is fully valid. Does not raise on JSON parse/shape errors
    here; read_events_locked already raises a clear json.JSONDecodeError or ValueError for
    a malformed line, which surfaces to the caller rather than being swallowed into a
    violation string here. Uses the locked read so a concurrent in-progress append is
    never observed mid-write."""
    events = read_events_locked(registry_path)
    current_status: dict[str, str | None] = {}
    violations = []
    for i, event in enumerate(events):
        rec_id = event.get("recommendation_id")
        status = event.get("status")
        if not isinstance(rec_id, str) or not isinstance(status, str):
            violations.append(f"line {i + 1}: missing or non-string recommendation_id/status")
            continue
        prior = current_status.get(rec_id)
        ok, reason = validate_transition(prior, status)
        if not ok:
            violations.append(f"line {i + 1} (recommendation_id={rec_id}): {reason}")
        current_status[rec_id] = status
    return violations


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")  # ty: ignore[unresolved-attribute]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        default=DEFAULT_REGISTRY_PATH,
        help=f"Path to the JSON Lines registry file (default: {DEFAULT_REGISTRY_PATH})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create the registry file (and parent dirs) if it doesn't exist")

    p_append = sub.add_parser("append", help="Append one lifecycle event")
    p_append.add_argument("--recommendation-id", required=True)
    p_append.add_argument("--status", required=True, choices=sorted(STATUSES))
    p_append.add_argument("--source-report")
    p_append.add_argument("--actor")
    p_append.add_argument("--rationale")
    p_append.add_argument("--evidence")
    p_append.add_argument("--expected-effect")
    p_append.add_argument("--observed-effect")
    p_append.add_argument("--timestamp", help="ISO-8601; defaults to now (UTC)")

    p_show = sub.add_parser("show", help="Print the full event history for one recommendation_id")
    p_show.add_argument("--recommendation-id", required=True)

    sub.add_parser("list", help="Print current status of every tracked recommendation_id")

    sub.add_parser("validate", help="Replay the registry and report any invalid transitions")

    args = parser.parse_args()
    registry_path = Path(args.registry)

    if args.command == "init":
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.touch(exist_ok=True)
        print(f"recommendation_registry: initialized {registry_path}", file=sys.stderr)
        return 0

    if args.command == "append":
        event = {
            "recommendation_id": args.recommendation_id,
            "timestamp": args.timestamp
            or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),  # noqa: UP017
            "status": args.status,
        }
        for field, value in (
            ("source_report", args.source_report),
            ("actor", args.actor),
            ("rationale", args.rationale),
            ("evidence", args.evidence),
            ("expected_effect", args.expected_effect),
            ("observed_effect", args.observed_effect),
        ):
            if value is not None:
                event[field] = value
        try:
            append_event(registry_path, event)
        except (ValueError, TimeoutError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(event, indent=2))
        return 0

    if args.command == "show":
        try:
            events = read_events_locked(registry_path)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"Error: registry contains malformed JSON: {exc}", file=sys.stderr)
            return 1
        history = show_recommendation(events, args.recommendation_id)
        json.dump(history, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.command == "list":
        try:
            events = read_events_locked(registry_path)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"Error: registry contains malformed JSON: {exc}", file=sys.stderr)
            return 1
        json.dump(list_recommendations(events), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.command == "validate":
        try:
            violations = validate_registry(registry_path)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"Error: registry contains malformed JSON: {exc}", file=sys.stderr)
            return 1
        if violations:
            for v in violations:
                print(v, file=sys.stderr)
            return 1
        print("recommendation_registry: valid, no transition violations", file=sys.stderr)
        return 0

    return 1  # unreachable -- argparse enforces `required=True` on the subparser choice


if __name__ == "__main__":
    sys.exit(main())
