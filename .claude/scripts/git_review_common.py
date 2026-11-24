"""Shared by cross-model-review's Python helpers (issue #697). Imported, never run.

The helpers run as `python3 -I`, which keeps this folder off the import path, so each loads this
file by its own path.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from pathlib import Path

# git-scan-staged-files.sh's patterns and a few more, each applied to every path segment.
_SENSITIVE_WORD_RE = re.compile(r"secret|credential|password|token", re.IGNORECASE)
_SENSITIVE_NAME_RE = re.compile(
    r"\.env.*|.*\.env|.*\.(key|pem|p12|pfx|jks|kdbx)(\..*)?|id_(rsa|ed25519|ecdsa|dsa)(\..*)?"
    r"|service-account\.json|\.npmrc|\.pgpass|\.netrc|\.pypirc|\.htpasswd",
    re.IGNORECASE | re.DOTALL,
)


def is_sensitive(path: str) -> bool:
    """Whether a path's name marks it as likely to hold a secret. Unlike the commit scan, no ignore
    file exempts a path and letter case does not matter: the cost of a false match is only that
    Codex does not see the file."""
    return bool(
        _SENSITIVE_WORD_RE.search(path)
        or any(_SENSITIVE_NAME_RE.fullmatch(segment) for segment in path.split("/"))
    )


def inside(path: Path, roots: Sequence[Path]) -> bool:
    """Whether `path` or a directory above it is one of `roots`, by identity, not by spelling."""
    for ancestor in (path, *path.parents):
        for root in roots:
            try:
                if ancestor.samefile(root):
                    return True
            except OSError:
                continue
    return False


def checkout_root(start: Path) -> list[Path]:
    """The nearest directory with a `.git` entry, found without running git, or `start`."""
    start = start.resolve()
    return [d for d in (start, *start.parents) if os.path.lexists(d / ".git")][:1] or [start]


def tool(name: str, forbidden: Sequence[Path]) -> str:
    """The absolute path of program `name`, from absolute PATH entries outside `forbidden` only.

    A bare name would let Windows find the program in the working directory, which is the repository
    under review. Raises FileNotFoundError when there is none, or when the first one is inside.
    """
    if os.name == "nt":
        name += ".exe"
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not os.path.isabs(entry):
            continue
        candidate = Path(entry) / name
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        if inside(candidate, forbidden) or inside(candidate.resolve(), forbidden):
            raise FileNotFoundError(f"the {name} on PATH lies inside the repository under review")
        return str(candidate)
    raise FileNotFoundError(f"{name} was not found on PATH")
