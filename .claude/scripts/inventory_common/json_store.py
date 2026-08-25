"""Deterministic serialization, hashing, locking, and atomic replacement for
the two canonical inventory JSON files.

**Canonical serialization/hashing algorithm** (the one definition every
inventory hash in this system is computed from): UTF-8 encoding, object keys
sorted lexicographically at every nesting level, no insignificant whitespace,
array elements keep their existing semantic order (never re-sorted -- e.g.
history periods keep chronological array order, not key order), LF line
endings only. Every document-level hash defined elsewhere in this system is
SHA-256 over this canonical byte sequence unless stated otherwise at its own
definition site.
"""

import hashlib
import json
import os
import tempfile
import time


def canonical_bytes(obj):
    """Serialize `obj` to the canonical byte form this system hashes."""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")


def compute_hash(obj_or_bytes):
    """SHA-256 hex digest of an object's canonical bytes, or of raw bytes directly."""
    data = (
        obj_or_bytes
        if isinstance(obj_or_bytes, (bytes, bytearray))
        else canonical_bytes(obj_or_bytes)
    )
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def atomic_write_json(path, obj, validator=None):
    """Write `obj` to `path` atomically: a temporary sibling file, optional
    validation of the round-tripped content, then `os.replace`. Never leaves
    a partially-written canonical file, and never touches `path` itself
    until the replace succeeds.
    """
    if validator is not None:
        validator(obj)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-inventory-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False))
            f.write("\n")
        if validator is not None:
            validator(read_json(tmp_path))
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


class InventoryLock:
    """A minimal, repository-local exclusive lock via an atomically-created
    lockfile (`O_CREAT | O_EXCL`). Not a distributed lock -- this system's
    actual requirement is "one writer at a time on one machine, reject a
    concurrent/stale apply rather than merge it," which this satisfies
    without an external dependency.

    A lock older than `stale_after_seconds` is treated as abandoned (its
    writer was killed, crashed, or lost the host after creating the
    lockfile but before `__exit__` could remove it) and reclaimed before
    the next retry -- an age heuristic, not a real PID-liveness check
    (which has no portable, dependency-free implementation across POSIX
    and Windows), but enough to recover from a routine interrupted
    invocation without a human having to manually find and delete the
    stray file. The default (10 minutes) is deliberately far longer than
    any of this module's own operations should ever take, to avoid
    reclaiming a lock a slow-but-still-alive writer genuinely still holds.
    """

    def __init__(self, path, timeout_seconds=30, poll_interval=0.2, stale_after_seconds=600):
        self.lock_path = path + ".lock"
        self.timeout_seconds = timeout_seconds
        self.poll_interval = poll_interval
        self.stale_after_seconds = stale_after_seconds
        self._acquired = False

    def _reclaim_if_stale(self):
        try:
            age = time.time() - os.path.getmtime(self.lock_path)
        except FileNotFoundError:
            return  # already gone -- released by its owner, or reclaimed by another waiter
        if age > self.stale_after_seconds:
            try:
                os.remove(self.lock_path)
            except FileNotFoundError:
                pass  # a concurrent waiter already reclaimed it

    def __enter__(self):
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("utf-8"))
                os.close(fd)
                self._acquired = True
                return self
            except FileExistsError:
                self._reclaim_if_stale()
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"could not acquire inventory lock at {self.lock_path} "
                        f"within {self.timeout_seconds}s"
                    ) from None
                time.sleep(self.poll_interval)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._acquired and os.path.exists(self.lock_path):
            os.remove(self.lock_path)
        return False
