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
import sys
import tempfile
import time

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


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
    """A minimal, repository-local exclusive lock via an OS-level advisory
    lock (`fcntl.flock` on POSIX, `msvcrt.locking` on Windows) held on a
    sibling lockfile for the full duration of ownership. Not a distributed
    lock -- this system's actual requirement is "one writer at a time on
    one machine, reject a concurrent/stale apply rather than merge it,"
    which this satisfies without an external dependency.

    Unlike a bare `O_CREAT | O_EXCL` lockfile (this class's earlier
    design), an advisory lock is released by the kernel the instant the
    holding process's file descriptor closes -- on a clean `__exit__`, but
    just as reliably on a crash or `kill -9`, with no age heuristic and no
    check-then-act window for a second waiter to race against. This is
    exactly the "real PID-liveness check" a prior version of this
    docstring said had no portable, dependency-free implementation --
    `fcntl`/`msvcrt` are both stdlib and provide it directly.

    The lockfile itself is never removed (deliberately -- see `__exit__`):
    removing it while another process might already hold an open file
    descriptor on the same inode reintroduces the classic flock-plus-unlink
    race, where a fresh `open()` after removal creates a new inode and two
    processes end up holding locks on two different files. Leaving the
    lockfile in place means every acquirer always locks the same, stable
    inode.
    """

    def __init__(self, path, timeout_seconds=30, poll_interval=0.2):
        self.lock_path = path + ".lock"
        self.timeout_seconds = timeout_seconds
        self.poll_interval = poll_interval
        self._fd = None

    def _try_lock(self, fd):
        if sys.platform == "win32":
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                return False
            return True
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def __enter__(self):
        deadline = time.monotonic() + self.timeout_seconds
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        while True:
            if self._try_lock(fd):
                os.ftruncate(fd, 0)
                os.write(fd, str(os.getpid()).encode("utf-8"))
                self._fd = fd
                return self
            if time.monotonic() >= deadline:
                os.close(fd)
                raise TimeoutError(
                    f"could not acquire inventory lock at {self.lock_path} "
                    f"within {self.timeout_seconds}s"
                )
            time.sleep(self.poll_interval)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            if sys.platform == "win32":
                os.lseek(self._fd, 0, os.SEEK_SET)
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None
        return False
