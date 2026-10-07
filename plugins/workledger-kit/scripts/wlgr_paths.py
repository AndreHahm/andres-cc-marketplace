#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Path-safety and process helpers shared by every workledger-kit script.

The scripts never take a filesystem path from the model. They derive the repo root and one
validated,
gitignored working folder themselves (wlgr_config.workdir) and accept only plain file *names* inside
it. This module holds the checks behind that:

  confine(path, root)       resolve `path` and require it to sit inside `root`, with no symlink or
                            junction component below `root` (including the last one) and no
                            Windows-reserved, stream (`:`) or trailing-dot/space segment.
  work_name(name)           accept only a plain file name (no separators, no leading dot, no
  reserved name).
  write_text / read_text    IO that refuses to follow a symlink in the final component (O_NOFOLLOW
  where
                            the platform has it; `confine` covers the rest).
  find_exe(name, exclude)   locate an executable on PATH only, never in the current directory and
  never
                            inside an excluded directory (Windows searches the current directory
                            first).
"""

from __future__ import annotations

import io
import os
import re
import stat
import sys
from pathlib import Path

_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    "conin$",
    "conout$",
    *(f"com{i}" for i in [*range(1, 10), "¹", "²", "³"]),
    *(f"lpt{i}" for i in [*range(1, 10), "¹", "²", "³"]),
}
_NAME_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
)  # used with fullmatch: `$` would admit a trailing newline


def utf8_stdio() -> None:
    """Make stdin and stdout UTF-8. On Windows they default to the locale code page (cp1252), which
    cannot carry collected issue, PR or report text."""
    for stream in (sys.stdin, sys.stdout):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def md_text(text: object) -> str:
    """Collected text for one markdown line: whitespace collapsed to single spaces, and `[`, `]`,
    `<` and `>` backslash-escaped so untrusted text cannot form an image, a link or an HTML tag
    that a viewer would load when the report is opened."""
    return re.sub(r"([\[\]<>])", r"\\\1", " ".join(str(text).split()))


def _bad_segment(part: str) -> str | None:
    """Reason a single path segment is unsafe on Windows or POSIX, or None."""
    if ":" in part:
        return "colon (drive letter or alternate data stream)"
    if part != part.rstrip(" ."):
        return "trailing dot or space"
    if part.split(".")[0].rstrip(" ").lower() in _RESERVED:
        return "reserved device name"
    return None


def _is_link(p: Path) -> bool:
    """Symlink or Windows junction/reparse point. Python 3.11 has no os.path.isjunction, so the
    reparse-point attribute is read directly."""
    if p.is_symlink():
        return True
    try:
        attrs = getattr(os.lstat(p), "st_file_attributes", 0)
    except FileNotFoundError:
        return False  # a path that does not exist yet is not a link
    except OSError:
        return True  # cannot tell (permissions, device error): fail closed
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def confine(path: Path, root: Path) -> Path:
    """Return the resolved `path`, or raise ValueError if it escapes `root` or crosses a link."""
    root_r = root.resolve()
    candidate = path if path.is_absolute() else root_r / path
    resolved = candidate.resolve()
    try:
        rel = resolved.relative_to(root_r)
    except ValueError:
        raise ValueError(f"{path} resolves outside {root}") from None
    probe = root_r
    for part in rel.parts:
        reason = _bad_segment(part)
        if reason:
            raise ValueError(f"unsafe path segment {part!r}: {reason}")
        probe = probe / part
        if _is_link(probe):
            raise ValueError(f"{probe} is a symlink or junction")
    # Also reject a link in any spelled-out component (including the last), which `resolve()` would
    # silently follow. The path must be spelled under the resolved root; callers pass resolved
    # roots.
    if not candidate.is_relative_to(root_r):
        raise ValueError(f"{path} is not spelled under the resolved root {root_r}")
    walker = root_r
    for part in candidate.relative_to(root_r).parts:
        walker = walker / part
        if _is_link(walker):
            raise ValueError(f"{walker} is a symlink or junction")
    return resolved


def work_name(name: str) -> str:
    """A plain file name for the working folder; anything path-like is refused."""
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name) or name != Path(name).name:
        raise ValueError(f"not a plain file name: {name!r}")
    reason = _bad_segment(name)
    if reason:
        raise ValueError(f"unsafe file name {name!r}: {reason}")
    return name


def write_text(path: Path, text: str) -> None:
    """Write `path` atomically: encode first (a lone surrogate from hostile JSON becomes '?',
    never an
    exception after the file was opened), write a sibling temp file created exclusively, then
    `os.replace` it over the target. `os.replace` replaces a symlink at the target instead of
    following
    it, and an interrupted write never leaves an empty or partial target."""
    data = text.encode("utf-8", errors="replace")
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def create_text(path: Path, text: str) -> None:
    """Create `path` exclusively (FileExistsError if it exists), never following a symlink."""
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(text.encode("utf-8"))


def read_text(path: Path) -> str:
    """Read `path` without following a symlink in the final component."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "rb") as fh:
        return fh.read().decode("utf-8")


def find_repo_root(start: Path) -> Path | None:
    """The nearest directory at or above `start` that holds a `.git` entry (a directory, or the
    file a
    work tree or submodule uses). Found by walking the filesystem, never by running git, so it can
    be
    used to exclude the repository from the search for the git executable itself."""
    here = start.resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def find_exe(name: str, exclude: list[Path] | None = None) -> str | None:
    """Absolute path of `name` found on PATH only. The current directory is never searched (Windows
    would search it before PATH, so a repo could ship a `git.exe`), and any PATH entry inside an
    excluded directory is skipped. Returns None if nothing safe is found."""
    banned = [p.resolve() for p in (exclude or [])] + [Path.cwd().resolve()]
    # Only a real executable on Windows: Python passes list arguments to cmd.exe for a .cmd or
    # .bat shim
    # without escaping them, so a shim would turn an `&` or `%VAR%` in an argument into a command.
    exts = [""] if sys.platform != "win32" else ["", ".exe"]
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue  # an empty PATH entry means "the current directory" on some platforms
        directory = Path(entry)
        if not directory.is_absolute():
            continue  # a relative entry resolves against the current directory
        try:
            d = directory.resolve()
        except OSError:
            continue
        if any(d == b or b in d.parents for b in banned):
            continue
        for ext in exts:
            candidate = d / (name + ext)
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None
