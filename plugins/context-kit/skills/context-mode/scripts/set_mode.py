#!/usr/bin/env python3
"""Load, refresh, check or clear this session's context mode.

Usage: set_mode.py <admin|review|ship|refresh|status|off>
       set_mode.py replace <admin|review|ship>

A mode value is validated against a closed set before any file is read, so a forged or malformed
value can never steer a read of an arbitrary path. The active mode is kept in a small state file
under ~/.claude/context-kit/, keyed by the session id, so ctx-post-compact-restore.py can
re-inject the profile after compaction.

One mode per session: setting a different mode while one is already saved is refused (exit 3).
Switching mode means a handoff and a fresh session; `replace` exists only for the user's explicit
override and is never used on behalf of a handoff.

The session id comes from CLAUDE_CODE_SESSION_ID. Whether that id equals the `session_id` the
SessionStart hook receives has not been verified live; if they differ the post-compact restore
finds no state file and simply does nothing. Without the variable, the profile is still printed
but nothing is persisted, and the script says so.

ctx-post-compact-restore.py reads the same file with the same hash; keep the two in sync.
"""

from __future__ import annotations

import hashlib
import os
import stat
import sys
import tempfile
from pathlib import Path

MODES = ("admin", "review", "ship")
REFERENCES = Path(__file__).resolve().parent.parent / "references"
MAX_STATE_BYTES = 16


def state_file() -> Path | None:
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not session_id:
        return None
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:8]
    return Path.home() / ".claude" / "context-kit" / f"mode-{digest}"


def read_mode(path: Path | None) -> str | None:
    """Read the saved mode: a regular file, bounded read, closed-set value only.

    A symlink is rejected on POSIX only (O_NOFOLLOW does not exist on Windows).
    """
    if path is None:
        return None
    try:
        fd = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STATE_BYTES:
                return None
            value = os.read(fd, MAX_STATE_BYTES).decode("utf-8").strip()
        finally:
            os.close(fd)
    except (OSError, UnicodeDecodeError):
        return None
    return value if value in MODES else None


def profile_text(mode: str) -> str:
    generic = (REFERENCES / "generic.md").read_text(encoding="utf-8")
    profile = (REFERENCES / f"{mode}.md").read_text(encoding="utf-8")
    return f"{generic.rstrip()}\n\n---\n\n{profile.rstrip()}\n"


def announce(mode: str) -> str:
    return (
        f"[Context-Mode] {mode} active for this session. Follow the profile below until the mode "
        "is changed; CLAUDE.md and .claude/rules/ still outrank it.\n\n" + profile_text(mode)
    )


def write_state(path: Path, mode: str) -> None:
    """Atomic write through an exclusively created temp file in the target directory."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path.parent, 0o700)  # tighten a directory that already existed
    except OSError:
        pass
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(mode + "\n")
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def set_mode(mode: str, replace: bool) -> int:
    path = state_file()
    if path is None:
        print(announce(mode))
        print(
            "Note: no session id was available, so this mode is not saved and will not be "
            "re-injected after compaction."
        )
        return 0
    current = read_mode(path)
    if current is not None and current != mode and not replace:
        print(
            f"The {current} mode is already active for this session. Switching modes means "
            "writing a handoff and starting a fresh session, so nothing was changed. To override "
            f"on purpose, the user can type: /context-mode replace {mode}",
            file=sys.stderr,
        )
        return 3
    try:
        write_state(path, mode)
    except OSError as exc:
        print(announce(mode))
        print(
            f"Note: the mode could not be saved ({exc.__class__.__name__}); it will not be "
            "re-injected after compaction."
        )
        return 0
    print(announce(mode))
    return 0


def main(argv: list[str]) -> int:
    args = [a.strip() for a in argv[1:]]
    if not args or len(args) > 2:
        print(
            "usage: set_mode.py <admin|review|ship|refresh|status|off> | replace <mode>",
            file=sys.stderr,
        )
        return 2
    arg = args[0]

    if len(args) == 2:
        if arg == "replace" and args[1] in MODES:
            return set_mode(args[1], replace=True)
        print("Unknown form. Valid: <mode>, refresh, status, off, replace <mode>.", file=sys.stderr)
        return 2

    if arg in MODES:
        return set_mode(arg, replace=False)

    path = state_file()
    if arg == "refresh":
        mode = read_mode(path)
        if mode is None:
            print("No context mode is active for this session. Set one with admin, review or ship.")
            return 0
        print(announce(mode))
        return 0

    if arg == "status":
        mode = read_mode(path)
        print(f"Active context mode: {mode}" if mode else "No context mode is active.")
        return 0

    if arg == "off":
        if path is not None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                print(
                    f"Could not clear the saved mode ({exc.__class__.__name__}).", file=sys.stderr
                )
                return 1
        print("Context mode cleared. Only CLAUDE.md and .claude/rules/ apply.")
        return 0

    print("Unknown mode. Valid values: admin, review, ship, refresh, status, off.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
