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
    r"\.env.*|.*\.env|.*\.(key|pem|p12|p8|pfx|ppk|jks|keystore|kdbx|tfvars|tfstate)(\..*)?"
    r"|.*id_(rsa|ed25519|ecdsa|dsa).*|service-account.*\.json|kubeconfig.*"
    r"|\.(npmrc|pgpass|netrc|pypirc|htpasswd).*",
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
    """The nearest directory with a `.git` entry, found without running git, or `start`; for a
    linked worktree also the main checkout. Other worktrees are not known here."""
    start = start.resolve()
    roots = [d for d in (start, *start.parents) if os.path.lexists(d / ".git")][:1] or [start]
    try:
        text = (roots[0] / ".git").read_text(encoding="utf-8")
        gitdir = roots[0] / text.removeprefix("gitdir:").strip()
        common_dir = (gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()
    except (OSError, ValueError):
        return roots
    return [*roots, common_dir.parent] if common_dir.name == ".git" else roots


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
        if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
            continue
        if inside(candidate, forbidden) or inside(candidate.resolve(), forbidden):
            raise FileNotFoundError(f"the {name} on PATH lies inside the repository under review")
        return str(candidate)
    raise FileNotFoundError(f"{name} was not found on PATH")


def safe_path(forbidden: Sequence[Path]) -> str:
    """PATH without relative entries, entries inside `forbidden`, and entries whose `codex`, `node`
    or `git` leads back inside."""
    kept = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not os.path.isabs(entry):
            continue
        folder = Path(entry)
        names = [n + ext for n in ("codex", "node", "git") for ext in ("", ".exe", ".cmd", ".bat")]
        programs = [folder / n for n in names if os.path.isfile(folder / n)]
        if inside(folder, forbidden) or inside(folder.resolve(), forbidden):
            continue
        if any(inside(program.resolve(), forbidden) for program in programs):
            continue
        kept.append(entry)
    return os.pathsep.join(kept)
