#!/usr/bin/env python3
"""Find the installed reviewadapters-kit that `cross-model-review` may run (issue #541, Part B).

The optional reviewer models (agy, pi, devin) run through reviewadapters-kit's
`scripts/rva-dispatch.mjs`, which must come from an installed copy outside the repository under
review: a copy inside it could be the reviewed change's own code, and it runs with the user's vendor
login. git-kit's own plugin root says nothing about where that plugin lives, so this script looks in
two places, in order:

  1. sibling: the plugin cache directory next to this script's own installed copy,
     `<cache>/<marketplace>/reviewadapters-kit/<version>/`, when exactly one version is there
     (counting, when Claude Code's `installed_plugins.json` exists, only a version it lists; the
     manifest must then be a plain file you own and only you can write);
  2. config:  the absolute path in `cross_model_review_rva_root` of the gitignored
     `.claude/git-kit.local.json` in the repository.

The plugin root is taken from this script's own location, never from an environment variable. A
candidate is resolved once, and only that real path is checked and printed. It is accepted only
when:

  - it is absolute, made of `[A-Za-z0-9._/-]` only (it is pasted into shell commands), and neither
    it nor a directory above it is this repository or any of its worktrees (by device and inode);
  - every directory above it belongs to the current user or root and, if others can write it, has
    the sticky bit, so nobody else can swap the root after the check;
  - the root, `scripts/`, `assets/`, and every entry in both (Node imports the dispatcher's
    siblings from `scripts/`; the Devin adapter copies the config that denies Devin every tool from
    `assets/`) and the root's `reviewadapters-kit.settings.json` (the vendors' default models) are
    owned by the current user, writable by nobody else, not symbolic links, and no regular file
    there has a second hard link; `scripts/rva-dispatch.mjs` exists as a regular file.

Group write is accepted only for the user's own private group, on Linux, with no extended ACL
(reviewadapters-kit's rule; see `private_group_gid`), since every plugin installed under umask 002
is group-writable. Where ownership cannot be read (Windows), every candidate is refused. git runs
without the caller's GIT_* variables. The config file is trusted only when it is a plain file (no
symlink component), owned by the current user, writable by nobody else, and neither it nor a
case variant of its name is tracked in the index or HEAD. A git failure counts as tracked.

The result can go stale while the user answers questions, so the caller runs this again right
before each vendor's first real dispatch and drops the vendor if `dispatcher` changed.

Prints one JSON object: `{"ok": true, "root", "dispatcher", "source", "notes"}` (exit 0) or
`{"ok": false, "reasons": [...]}` (exit 3, no usable copy). Exit 2 is a usage error. It never
writes anything and never runs the dispatcher.

This repository's own convention only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

PLUGIN_NAME = "reviewadapters-kit"
LOCAL_PATH = ".claude/git-kit.local.json"
CONFIG_KEY = "cross_model_review_rva_root"
DISPATCHER = ("scripts", "rva-dispatch.mjs")
# Directories whose every entry is checked: the dispatcher's modules and the files it copies.
CHECKED_DIRS = ("scripts", "assets")
# The settings file the dispatcher's loadConfig reads from the root.
SETTINGS_FILE = "reviewadapters-kit.settings.json"
# Claude Code's record of installed plugins, three levels above a version folder in the cache.
INSTALLED_MANIFEST = "installed_plugins.json"
MAX_CONFIG_BYTES = 1_000_000
# The printed path is pasted into shell commands, so it may hold no shell syntax.
_SAFE_PATH_RE = re.compile(r"/[A-Za-z0-9._/-]+\Z")
_GIT_TIMEOUT_SECONDS = 30


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def private_group_gid(passwd: str = "/etc/passwd", group: str = "/etc/group") -> int | None:
    """The user's own private group, or None (same rule as reviewadapters-kit's `privateGroupGid`).

    On a umask-002 system every installed plugin is group-writable, so refusing group write outright
    would refuse every real install. It is harmless only for the user's private group: the primary
    gid, named like the user, on exactly one /etc/group line with no members, and no other account
    in /etc/passwd using it as its primary gid. Linux only; other NSS sources (LDAP, sssd) are not
    read, so a group /etc/group does not list gets no exception. Unreadable files: no exception.
    """
    if not sys.platform.startswith("linux"):
        return None
    try:
        import pwd

        gid = os.getgid()
        user = pwd.getpwuid(os.getuid()).pw_name
        with open(passwd, encoding="utf-8") as handle:
            for line in handle:
                fields = line.rstrip("\n").split(":")
                if (
                    len(fields) > 3
                    and fields[3].isdigit()
                    and int(fields[3]) == gid
                    and fields[0] != user
                ):
                    return None
        found = False
        with open(group, encoding="utf-8") as handle:
            for line in handle:
                fields = line.rstrip("\n").split(":")
                if len(fields) < 3 or not fields[2].isdigit() or int(fields[2]) != gid:
                    continue
                members = fields[3].strip() if len(fields) > 3 else ""
                if found or fields[0] != user or members:
                    return None
                found = True
        return gid if found else None
    except (OSError, KeyError, UnicodeDecodeError):
        return None


_GNU_LS: list[str | None] = []


def _gnu_ls() -> str | None:
    if not _GNU_LS:
        _GNU_LS.append(None)
        for binary in ("/usr/bin/ls", "/bin/ls"):
            try:
                out = subprocess.run(
                    [binary, "--version"],
                    capture_output=True,
                    text=True,
                    env={"LC_ALL": "C"},
                    timeout=10,
                    check=False,
                ).stdout
            except (OSError, subprocess.TimeoutExpired):
                continue
            if out.startswith("ls (GNU coreutils) "):
                _GNU_LS[0] = binary
                break
    return _GNU_LS[0]


def may_have_extended_acl(path: Path) -> bool:
    """True unless GNU coreutils `ls` shows no extended ACL on `path` (fails closed).

    A POSIX ACL can grant write only through the mask the group bits show, so it matters only where
    the private-group exception lets group write pass.
    """
    binary = _gnu_ls()
    if binary is None:
        return True
    try:
        out = subprocess.run(
            [binary, "-ldL", "--", str(path)],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C"},
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    if out.returncode != 0:
        return True
    mode = out.stdout.split(maxsplit=1)[0] if out.stdout.strip() else ""
    return not (len(mode) == 10 or (len(mode) == 11 and mode[10] == "."))


def _others_can_write(st: os.stat_result, path: Path | None) -> bool:
    """World write, or group write by any group but the user's private one (Linux, no ACL)."""
    if st.st_mode & stat.S_IWOTH:
        return True
    if st.st_mode & stat.S_IWGRP:
        private = private_group_gid()
        return (
            private is None or st.st_gid != private or path is None or may_have_extended_acl(path)
        )
    return False


def _owner_problem(st: os.stat_result, label: str, path: Path | None = None) -> str | None:
    if not hasattr(os, "getuid"):
        return f"{label}: ownership cannot be checked on this platform"
    if st.st_uid != os.getuid():
        return f"{label} is not owned by the current user"
    if _others_can_write(st, path):
        return f"{label} is writable by others"
    return None


def _ancestor_problem(real: Path) -> str | None:
    """Why a directory above the root lets another account swap the root, or None.

    Each must belong to the current user or root; one others can write also needs the sticky bit
    (the same rule as reviewadapters-kit's `unsafeDirStat`).
    """
    for directory in real.parents:
        try:
            st = directory.lstat()
        except OSError:
            return f"{directory} could not be checked"
        if hasattr(os, "getuid") and st.st_uid not in (os.getuid(), 0):
            return f"{directory} (above the root) is not owned by the current user or root"
        if _others_can_write(st, directory) and not st.st_mode & stat.S_ISVTX:
            return f"{directory} (above the root) is writable by others without the sticky bit"
    return None


def _same_file_inside(real: Path, roots: Sequence[Path]) -> bool:
    """Whether `real` or a directory above it is one of `roots` (by device and inode)."""
    ids = set()
    for root in roots:
        try:
            st = root.stat()
        except OSError:
            continue
        ids.add((st.st_dev, st.st_ino))
    for path in (real, *real.parents):
        try:
            st = path.stat()
        except OSError:
            return True
        if (st.st_dev, st.st_ino) in ids:
            return True
    return False


def check_root(
    candidate: Path, repo: Path, worktrees: Sequence[Path] = ()
) -> tuple[Path | None, str | None]:
    """(real root, None) when `candidate` may run as reviewadapters-kit's root, else (None, why).

    The returned path is the one checked; use only it afterwards, never resolve the candidate again.
    """
    if not candidate.is_absolute():
        return None, f"{candidate} is not an absolute path"
    try:
        real = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None, f"{candidate} does not exist"
    if not _SAFE_PATH_RE.match(str(real)):
        return None, f"{candidate} has characters outside [A-Za-z0-9._/-]"
    if _inside(real, repo) or _same_file_inside(real, [repo, *worktrees]):
        return None, f"{candidate} lies inside the repository under review or one of its worktrees"
    problem = _ancestor_problem(real) or _dir_problem(real)
    if problem:
        return None, problem
    # Node imports the dispatcher's siblings from scripts/, and the Devin adapter copies the config
    # that denies Devin every tool from assets/, so every entry in both is checked.
    for name in CHECKED_DIRS:
        directory = real / name
        problem = _dir_problem(directory)
        if problem:
            return None, problem
        try:
            entries = list(os.scandir(directory))
        except OSError:
            return None, f"{directory} could not be listed"
        if name == DISPATCHER[0] and not any(e.name == DISPATCHER[-1] for e in entries):
            return None, f"{real.joinpath(*DISPATCHER)} is missing"
        for entry in entries:
            problem = _entry_problem(Path(entry.path))
            if problem:
                return None, problem
    if not real.joinpath(*DISPATCHER).is_file():
        return None, f"{real.joinpath(*DISPATCHER)} is not a regular file"
    # loadConfig reads the vendors' default models (pi's names the recipient) from the root itself.
    settings = real / SETTINGS_FILE
    problem = _entry_problem(settings) or (
        None if settings.is_file() else f"{settings} is not a regular file"
    )
    if problem:
        return None, problem
    return real, None


def _dir_problem(directory: Path) -> str | None:
    """Why `directory` is not a plain directory owned by the user and writable by nobody else."""
    try:
        st = directory.lstat()
    except OSError:
        return f"{directory} is missing"
    if stat.S_ISLNK(st.st_mode):
        return f"{directory} is a symbolic link"
    if not stat.S_ISDIR(st.st_mode):
        return f"{directory} is not a directory"
    return _owner_problem(st, str(directory), directory)


def _entry_problem(path: Path) -> str | None:
    """Why an entry of a checked directory could be swapped or edited by someone else, or None."""
    try:
        st = path.lstat()
    except OSError:
        return f"{path} could not be checked"
    if stat.S_ISLNK(st.st_mode):
        return f"{path} is a symbolic link"
    if stat.S_ISREG(st.st_mode) and st.st_nlink > 1:
        return f"{path} has more than one hard link"
    if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
        return f"{path} is not a regular file"
    return _owner_problem(st, str(path), path)


def sibling_candidate(plugin_root: Path) -> tuple[Path | None, str | None]:
    """The single installed version beside this plugin's cache directory, or why there is none."""
    plugin_dir = plugin_root.parent
    if plugin_dir.name != "git-kit":
        return None, "git-kit does not run from a plugin cache directory"
    sibling = plugin_dir.parent / PLUGIN_NAME
    try:
        versions = sorted(p for p in sibling.iterdir() if p.is_dir() and not p.is_symlink())
    except OSError:
        return None, f"no installed {PLUGIN_NAME} beside git-kit in the plugin cache"
    listed, why = installed_versions(plugin_dir.parent)
    if why:
        return None, why
    if listed is not None:
        versions = [p for p in versions if p.name in listed]
    if len(versions) != 1:
        found = ", ".join(p.name for p in versions) or "none"
        where = " listed as installed" if listed is not None else ""
        return None, f"expected one installed {PLUGIN_NAME} version{where}, found: {found}"
    return versions[0], None


def installed_versions(marketplace_dir: Path) -> tuple[set[str] | None, str | None]:
    """The version folder names Claude Code lists as installed for this marketplace's copy.

    (None, None) when the manifest does not exist, so the single-folder rule alone applies; a
    manifest that exists but is not a plain file you own and only you can write, or cannot be read
    or parsed, refuses the sibling. It only narrows the choice among folders already in the cache,
    each still checked by `check_root`, but whoever could write it could pick an older copy.
    """
    manifest = marketplace_dir.parent.parent / INSTALLED_MANIFEST
    if not os.path.lexists(manifest):
        return None, None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(manifest, flags)
    except OSError:
        return None, f"{INSTALLED_MANIFEST} could not be opened"
    with os.fdopen(fd, "rb") as handle:
        st = os.fstat(handle.fileno())
        if not stat.S_ISREG(st.st_mode):
            return None, f"{INSTALLED_MANIFEST} is not a regular file"
        fd_path = Path(f"/proc/{os.getpid()}/fd/{handle.fileno()}")
        problem = _owner_problem(st, INSTALLED_MANIFEST, fd_path)
        if problem:
            return None, problem
        raw = handle.read(MAX_CONFIG_BYTES + 1)
    if len(raw) > MAX_CONFIG_BYTES:
        return None, f"{INSTALLED_MANIFEST} is too large"
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None, f"{INSTALLED_MANIFEST} could not be read"
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return None, f"{INSTALLED_MANIFEST} has no plugins object"
    entries = plugins.get(f"{PLUGIN_NAME}@{marketplace_dir.name}") or []
    if not isinstance(entries, list):
        return None, f"{INSTALLED_MANIFEST} has an unexpected {PLUGIN_NAME} entry"
    sibling = Path(os.path.realpath(marketplace_dir / PLUGIN_NAME))
    listed = set()
    for entry in entries:
        install = entry.get("installPath") if isinstance(entry, dict) else None
        if not isinstance(install, str) or not os.path.isabs(install):
            continue
        resolved = Path(os.path.realpath(install))
        if resolved.parent == sibling:
            listed.add(resolved.name)
    return listed, None


def _git(repo: Path, *args: str) -> bytes | None:
    """git's stdout, run without the caller's GIT_* variables (they could point it elsewhere)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            env=env,
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _git_names(repo: Path) -> list[str] | None:
    names: list[str] = []
    for args in (("ls-files", "-z"), ("ls-tree", "-r", "--name-only", "-z", "HEAD")):
        out = _git(repo, *args)
        if out is None:
            return None
        names += out.decode("utf-8", "surrogateescape").split("\0")
    return names


def worktree_roots(repo: Path) -> list[Path] | None:
    """Every worktree of this repository (another may have an unreviewed branch checked out)."""
    out = _git(repo, "worktree", "list", "--porcelain", "-z")
    if out is None:
        return None
    return [
        Path(field[len("worktree ") :])
        for field in out.decode("utf-8", "surrogateescape").split("\0")
        if field.startswith("worktree ")
    ]


def config_candidate(repo: Path) -> tuple[Path | None, str | None]:
    """The configured root from the local file, or why it is absent or untrusted."""
    path = repo / LOCAL_PATH
    if not os.path.lexists(path):
        return None, f"{LOCAL_PATH} does not exist"
    current = repo
    for part in Path(LOCAL_PATH).parts:
        current = current / part
        if current.is_symlink():
            return None, f"{LOCAL_PATH} is reached through a symbolic link"
    names = _git_names(repo)
    if names is None:
        return None, f"could not check whether {LOCAL_PATH} is tracked"
    if any(n.lower() == LOCAL_PATH.lower() for n in names):
        return None, f"{LOCAL_PATH} is tracked by git, so it may not name the dispatcher"
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None, f"{LOCAL_PATH} could not be opened"
    with os.fdopen(fd, "rb") as handle:
        st = os.fstat(handle.fileno())
        if not stat.S_ISREG(st.st_mode):
            return None, f"{LOCAL_PATH} is not a regular file"
        problem = _owner_problem(st, LOCAL_PATH, Path(f"/proc/{os.getpid()}/fd/{handle.fileno()}"))
        if problem:
            return None, problem
        raw = handle.read(MAX_CONFIG_BYTES + 1)
    if len(raw) > MAX_CONFIG_BYTES:
        return None, f"{LOCAL_PATH} is too large"
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, f"{LOCAL_PATH} is not valid JSON"
    if not isinstance(data, dict) or CONFIG_KEY not in data:
        return None, f"{LOCAL_PATH} does not set {CONFIG_KEY}"
    value = data[CONFIG_KEY]
    if not isinstance(value, str) or not value or "\0" in value:
        return None, f"{CONFIG_KEY} is not a non-empty string"
    return Path(value), None


def locate(repo: Path, plugin_root: Path) -> dict:
    worktrees = worktree_roots(repo)
    if worktrees is None:
        return {"ok": False, "reasons": ["could not list this repository's worktrees"]}
    reasons: list[str] = []
    candidate, why = sibling_candidate(plugin_root)
    if candidate is not None:
        root, why = check_root(candidate, repo, worktrees)
        if root is not None:
            return _found(root, "sibling", reasons)
    reasons.append(f"sibling: {why}")
    candidate, why = config_candidate(repo)
    if candidate is not None:
        root, why = check_root(candidate, repo, worktrees)
        if root is not None:
            return _found(root, "config", reasons)
    reasons.append(f"config: {why}")
    return {"ok": False, "reasons": reasons}


def _found(root: Path, source: str, notes: list[str]) -> dict:
    return {
        "ok": True,
        "root": str(root),
        "dispatcher": str(root.joinpath(*DISPATCHER)),
        "source": source,
        "notes": notes,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, help="the repository's top-level directory")
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    if not repo.is_absolute() or not repo.is_dir():
        print(json.dumps({"ok": False, "reasons": ["--repo must be an absolute directory"]}))
        return 2
    result = locate(repo.resolve(), Path(__file__).resolve().parent.parent)
    print(json.dumps(result))
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
