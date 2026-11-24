#!/usr/bin/env python3
"""Find the installed codex-kit and run its review bridge (issue #697).

usage: git-review-codex-kit.py locate
       git-review-codex-kit.py bridge <bridge-invoke.mjs arguments>...

`cross-model-review` must never run a bridge that the repository under review supplies, so its
allowed-tools grant names this script instead of a path relative to the working directory. The
codex-kit root is the `installPath` recorded under `codex-kit@andres-cc-marketplace` in
`~/.claude/plugins/installed_plugins.json`, where `~` is the account's home from the password
database on POSIX and from the profile folder API on Windows, never from $HOME or %USERPROFILE% (a
repository's own settings can set variables). CLAUDE_CONFIG_DIR is ignored for the same reason. The
root is refused unless it is absolute, exists, holds the bridge as a regular file, and lies outside
this repository and all of its worktrees; several different installed roots are refused as
ambiguous. This is a check on the location, not on the content: who can write to the user's own
plugin folder is trusted.

`git` and `node` are looked up in the absolute PATH entries only and refused inside the repository:
a bare name would let Windows find one in the working directory, which is the reviewed repository.
The bridge gets a PATH reduced the same way, because it looks `codex` up itself.

`locate` prints `{"ok": true, "root": ...}` (exit 0) or `{"ok": false, "reason": ...}` (exit 3).
`bridge` runs `node <root>/<bridge>` with the arguments unchanged and returns its exit status. GIT_*
and NODE_* variables (some preload code) are dropped for it. With no usable root it prints a
`cli_unavailable` failure and exits 3. Exit 2 is a usage error.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import uuid
from collections.abc import Sequence
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import CodeType, ModuleType


class _SourceOnlyLoader(SourceFileLoader):
    """Compiles the source itself: a plain import would also run a planted __pycache__ file."""

    def get_code(self, fullname: str) -> CodeType:
        return self.source_to_code(self.get_data(self.path), self.path)


def _load_common() -> ModuleType:
    path = Path(__file__).resolve().with_name("git_review_common.py")
    module = ModuleType("git_review_common")
    _SourceOnlyLoader(module.__name__, str(path)).exec_module(module)
    return module


common = _load_common()

REGISTRY_KEY = "codex-kit@andres-cc-marketplace"
BRIDGE = Path("skills/codex-review-bridge/scripts/bridge-invoke.mjs")
_GIT_TIMEOUT_SECONDS = 30
# FOLDERID_Profile, the current user's profile folder.
_PROFILE_FOLDER = uuid.UUID("5e6c858f-0e22-4760-9afe-ea3317b67173")


class Unavailable(Exception):
    """No codex-kit may be run; the message says why."""


def _home() -> Path:
    if os.name == "posix":
        import pwd

        return Path(pwd.getpwuid(os.getuid()).pw_dir)
    return _windows_profile()


def _windows_profile() -> Path:
    """The account's profile folder as Windows records it, whatever the environment says."""
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        raise Unavailable("the account's home could not be found")
    folder = ctypes.create_string_buffer(_PROFILE_FOLDER.bytes_le, 16)
    found = ctypes.c_wchar_p()
    get_path = windll.shell32.SHGetKnownFolderPath
    get_path.argtypes = [ctypes.c_char_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
    get_path.restype = ctypes.c_long
    result = get_path(folder, 0, None, ctypes.byref(found))
    if result != 0 or not found.value:
        raise Unavailable("the account's home could not be found")
    return Path(found.value)


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.upper().startswith(("GIT_", "NODE_"))}


def worktree_roots() -> list[Path]:
    """The checkout and every worktree: another worktree can hold an unreviewed branch."""
    checkout = common.checkout_root(Path.cwd())
    program = common.tool("git", checkout)
    try:
        result = subprocess.run(
            [program, "worktree", "list", "--porcelain", "-z"],
            env=_clean_env(),
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise Unavailable("could not list this repository's worktrees") from err
    prefix = b"worktree "
    roots = [
        Path(os.fsdecode(field[len(prefix) :]))
        for field in result.stdout.split(b"\0")
        if field.startswith(prefix)
    ]
    if result.returncode != 0 or not roots:
        raise Unavailable("could not list this repository's worktrees")
    return [*checkout, *roots]


def registered_roots(registry: Path) -> set[Path]:
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        entries = data["plugins"].get(REGISTRY_KEY, [])
        paths = [entry["installPath"] for entry in entries]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as err:
        raise Unavailable(f"{registry.name} could not be read") from err
    roots = set()
    for path in paths:
        if not isinstance(path, str) or not os.path.isabs(path):
            continue
        try:
            roots.add(Path(path).resolve(strict=True))
        except (OSError, RuntimeError, ValueError):
            continue
    return roots


def locate() -> tuple[Path, list[Path]]:
    """The codex-kit root, and the directories nothing may be run from."""
    roots = registered_roots(_home() / ".claude" / "plugins" / "installed_plugins.json")
    if len(roots) != 1:
        raise Unavailable(f"expected one installed codex-kit, found {len(roots)}")
    root = roots.pop()
    bridge = root / BRIDGE
    if not bridge.is_file():
        raise Unavailable("the installed codex-kit has no review bridge")
    # The resolved bridge too: a link inside the root could lead back into the repository.
    repo_roots = worktree_roots()
    if common.inside(root, repo_roots) or common.inside(bridge.resolve(), repo_roots):
        raise Unavailable("the installed codex-kit lies inside the repository under review")
    return root, repo_roots


def main(argv: Sequence[str]) -> int:
    if not argv or argv[0] not in ("locate", "bridge") or (argv[0] == "locate" and argv[1:]):
        print("usage: git-review-codex-kit.py locate | bridge <arguments>...", file=sys.stderr)
        return 2
    try:
        root, repo_roots = locate()
        node = common.tool("node", repo_roots) if argv[0] == "bridge" else ""
    except (Unavailable, FileNotFoundError) as err:
        if argv[0] == "locate":
            print(json.dumps({"ok": False, "reason": str(err)}))
        else:
            failure = {"ok": False, "category": "cli_unavailable", "detail": str(err)}
            print(json.dumps(failure), file=sys.stderr)
        return 3
    if argv[0] == "locate":
        print(json.dumps({"ok": True, "root": root.as_posix()}))
        return 0
    env = {**_clean_env(), "PATH": common.safe_path(repo_roots)}
    try:
        return subprocess.run(
            [node, str(root / BRIDGE), *argv[1:]], env=env, check=False
        ).returncode
    except OSError as err:
        failure = {"ok": False, "category": "cli_unavailable", "detail": f"node: {err.strerror}"}
        print(json.dumps(failure), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
