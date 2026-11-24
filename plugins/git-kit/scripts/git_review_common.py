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


def has_sensitive_name(text: str) -> bool:
    """Whether a part of the text is a sensitive file name; a sensitive word alone is not one."""
    return any(_SENSITIVE_NAME_RE.fullmatch(part) for part in re.split(r"[/:()]", text))


def common_git_dir(folder: Path) -> Path | None:
    """The common git directory that `folder`'s own `.git` names, read without running git."""
    found = folder / ".git"
    try:
        if found.is_file():
            found = folder / found.read_text(encoding="utf-8").removeprefix("gitdir:").strip()
        if (found / "commondir").is_file():
            found = found / (found / "commondir").read_text(encoding="utf-8").strip()
        return found.resolve() if found.is_dir() else None
    except (OSError, ValueError, RuntimeError):
        return None


def inside(path: Path, roots: Sequence[Path]) -> bool:
    """Whether `path` or a directory above it is one of `roots`, by identity, not by spelling, or a
    worktree whose common git directory is one of them."""
    for ancestor in (path, *path.parents):
        common_dir = common_git_dir(ancestor)
        for candidate in (ancestor,) if common_dir is None else (ancestor, common_dir):
            for root in roots:
                try:
                    if candidate.samefile(root):
                        return True
                except (OSError, ValueError):
                    continue
    return False


def checkout_root(start: Path) -> list[Path]:
    """The nearest directory with a `.git` entry, or `start`, then the repository's git directory,
    main checkout and other worktrees, all found without running git."""
    start = start.resolve()
    roots = [d for d in (start, *start.parents) if os.path.lexists(d / ".git")][:1] or [start]
    common_dir = common_git_dir(roots[0])
    if common_dir is None:
        return roots
    roots.append(common_dir)
    if common_dir.name == ".git":
        roots.append(common_dir.parent)
    try:
        entries = sorted((common_dir / "worktrees").iterdir())
    except OSError:
        return roots
    for entry in entries:
        try:
            # <worktree>/.git, absolute or relative to the entry.
            roots.append((entry / (entry / "gitdir").read_text("utf-8").strip()).parent)
        except (OSError, ValueError):
            continue
    return roots


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
        suffixes = ("", ".exe", ".com", ".cmd", ".bat")
        names = [n + ext for n in ("codex", "node", "git") for ext in suffixes]
        programs = [folder / n for n in names if os.path.isfile(folder / n)]
        try:
            resolved = [p.resolve() for p in (folder, *programs)]
        except (OSError, RuntimeError):  # a symlink loop
            continue
        if any(inside(p, forbidden) for p in (folder, *resolved)):
            continue
        kept.append(entry)
    return os.pathsep.join(kept)
