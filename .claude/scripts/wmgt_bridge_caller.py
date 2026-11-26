#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Dispatch work-transition-reviewer / work-intake-classifier live through
codex-kit's codex-review-bridge (see plugins/codex-kit/skills/codex-review-bridge/SKILL.md).

Reads the target agent's .md file, strips its YAML frontmatter, writes the body
to a scratch instruction file outside the repository entirely (an OS temp
directory -- --instruction-file is not repo-root-bound the way --target-paths
is, and this guarantees no --target-paths value, however broad, can ever
contain it), then calls bridge-invoke.mjs and returns the parsed canonical
envelope (or typed failure) as a dict.

Per GitHub issue #251 / plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md.

Finding codex-kit (issue #279): the bridge and the repository under review are two
independent locations. codex-kit's root is the installPath recorded under
codex-kit@andres-cc-marketplace in ~/.claude/plugins/installed_plugins.json, where ~ is
the account's home from the password database (POSIX) or the profile folder API
(Windows), never an environment variable a repository's settings could set. It is refused
when ambiguous, or when it lies inside this repository or one of its worktrees. Only when
no codex-kit is registered is the sibling plugins/codex-kit used, and only when this very
script runs from that checkout (plugins/workmanagement-kit or its .claude mirror). That
fallback skips the inside-the-repository refusal on purpose: it runs the checkout's own bridge
at the trust level of this script, which is the same checkout's code.
--repo-root bounds the evidence paths; it never selects the code that runs. The location
logic follows git-kit's git-review-codex-kit.py, copied because an installed plugin
cannot import a sibling plugin's scripts. Not covered: CODEX_HOME, SystemRoot, LD_* and
similar variables reach the child, so a project whose settings the user trusts to set
variables can still influence it.
"""

import argparse
import ctypes
import functools
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

AGENTS = {"work-transition-reviewer", "work-intake-classifier"}

# Same charset/length bridge-invoke.mjs's own isValidToken enforces on
# --dispatch-id (^[A-Za-z0-9._-]{1,64}$) -- mirrored here deliberately so this
# script never constructs a filesystem path from an unvalidated dispatch_id
# before handing off to a separate process that would reject it anyway.
_DISPATCH_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def repo_root_from(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    # ValueError, not SystemExit -- SystemExit is a BaseException, not an
    # Exception, so it silently bypasses main()'s own
    # except (ValueError, FileNotFoundError, OSError) and crashes with an
    # uncaught traceback instead of the documented typed-failure dict (found
    # by CodeRabbit's PR #278 review).
    raise ValueError(f"could not resolve repo root from {start}")


REGISTRY_KEY = "codex-kit@andres-cc-marketplace"
BRIDGE = Path("skills/codex-review-bridge/scripts/bridge-invoke.mjs")
# FOLDERID_Profile, the current user's profile folder.
_PROFILE_FOLDER = uuid.UUID("5e6c858f-0e22-4760-9afe-ea3317b67173")


def _home() -> Path:
    """The account's home as the OS records it, whatever the environment says."""
    if os.name == "posix":
        import pwd

        return Path(pwd.getpwuid(os.getuid()).pw_dir)
    folder = ctypes.create_string_buffer(_PROFILE_FOLDER.bytes_le, 16)
    found = ctypes.c_wchar_p()
    get_path = ctypes.windll.shell32.SHGetKnownFolderPath
    get_path.argtypes = [ctypes.c_char_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
    get_path.restype = ctypes.c_long
    if get_path(folder, 0, None, ctypes.byref(found)) != 0 or not found.value:
        raise ValueError("the account's home could not be found")
    return Path(found.value)


@functools.cache  # _safe_path asks about the same folders many times
def _common_git_dir(folder: Path) -> Path | None:
    """The common git directory that folder's own .git names, read without running git."""
    found = folder / ".git"
    try:
        if found.is_file():
            found = folder / found.read_text(encoding="utf-8").removeprefix("gitdir:").strip()
        if (found / "commondir").is_file():
            found = found / (found / "commondir").read_text(encoding="utf-8").strip()
        return found.resolve() if found.is_dir() else None
    except (OSError, ValueError, RuntimeError):
        return None


def repository_roots(root: Path) -> list[Path]:
    """root, its git directory, the main checkout and every worktree."""
    roots = [root]
    common = _common_git_dir(root)
    if common is None:
        if (root / ".git").exists():
            # For example a Windows-made worktree read under WSL: its other checkouts are
            # unknown, so nothing could be refused for lying inside them.
            raise ValueError(f"could not read the git directory of {root}")
        return roots
    roots.append(common)
    if common.name == ".git":
        roots.append(common.parent)
    try:
        entries = sorted((common / "worktrees").iterdir())
    except FileNotFoundError:
        return roots
    except OSError as error:
        # Fail closed, as above: an unlisted worktree could not be refused.
        raise ValueError(f"could not list the worktrees of {root}") from error
    for entry in entries:
        if not entry.is_dir():
            # A stray file (an editor backup, say): git ignores it too.
            continue
        try:
            # <worktree>/.git, absolute or relative to the entry.
            text = (entry / "gitdir").read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            # No gitdir: git does not list the entry as a worktree either.
            continue
        except (OSError, ValueError) as error:
            raise ValueError(f"could not read the worktree entry {entry.name}") from error
        roots.append((entry / text).parent)
    return roots


def _inside(path: Path, roots: Sequence[Path]) -> bool:
    """Whether path, or a directory above it, is one of roots: by identity, not spelling."""
    for ancestor in (path, *path.parents):
        common = _common_git_dir(ancestor)
        for candidate in (ancestor,) if common is None else (ancestor, common):
            for root in roots:
                try:
                    if candidate.samefile(root):
                        return True
                except (OSError, ValueError):
                    continue
    return False


def _node(forbidden: Sequence[Path]) -> str:
    """node from absolute PATH entries only: for a bare name, Windows would also search the
    working directory, which is the repository under review."""
    name = "node.exe" if os.name == "nt" else "node"
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not os.path.isabs(entry):
            continue
        candidate = Path(entry) / name
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        if _inside(candidate, forbidden) or _inside(candidate.resolve(), forbidden):
            raise ValueError("the node on PATH lies inside the repository under review")
        return str(candidate)
    raise FileNotFoundError("node was not found on PATH")


def _safe_path(forbidden: Sequence[Path]) -> str:
    """PATH without entries that are relative or lead into forbidden: the bridge looks codex
    up itself."""
    kept = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not os.path.isabs(entry):
            continue
        folder = Path(entry)
        suffixes = ("", ".exe", ".com", ".cmd", ".bat")
        names = [n + ext for n in ("codex", "node", "git") for ext in suffixes]
        try:
            programs = [folder / n for n in names if (folder / n).is_file()]
            resolved = [p.resolve() for p in (folder, *programs)]
        except (OSError, RuntimeError):  # a symlink loop
            continue
        if not any(_inside(p, forbidden) for p in (folder, *resolved)):
            kept.append(entry)
    return os.pathsep.join(kept)


def checkout_of(plugin_root: Path) -> Path | None:
    """The marketplace checkout this script runs from, or None for an installed plugin."""
    if plugin_root.name == ".claude":
        candidate = plugin_root.parent
    elif plugin_root.parent.name == "plugins":
        candidate = plugin_root.parent.parent
    else:
        return None
    return candidate if (candidate / ".git").exists() else None


def registered_codex_kit() -> Path | None:
    """The one installed codex-kit, None when none is registered. Anything unclear raises."""
    registry = _home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        paths = [entry["installPath"] for entry in data["plugins"].get(REGISTRY_KEY, [])]
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as err:
        raise ValueError(f"{registry.name} could not be read") from err
    if not paths:
        return None
    roots = set()
    for path in paths:
        if not isinstance(path, str) or not os.path.isabs(path):
            raise ValueError("the registered codex-kit path is not absolute")
        roots.add(Path(path).resolve(strict=True))
    if len(roots) != 1:
        raise ValueError(f"expected one installed codex-kit, found {len(roots)}")
    return roots.pop()


def find_bridge(checkout: Path | None, forbidden: Sequence[Path]) -> Path:
    installed = registered_codex_kit()
    if installed is not None:
        bridge = (installed / BRIDGE).resolve()
        if _inside(installed, forbidden) or _inside(bridge, forbidden):
            raise ValueError("the installed codex-kit lies inside the repository under review")
    elif checkout is not None:
        bridge = checkout / "plugins" / "codex-kit" / BRIDGE
    else:
        raise FileNotFoundError("codex-kit is not installed")
    if not bridge.is_file():
        raise FileNotFoundError(bridge)
    return bridge


def strip_frontmatter(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[i + 1 :]).lstrip("\n")
    return text


def dispatch(
    agent: str,
    target_paths: list[str],
    dispatch_id: str,
    execution_profile: str,
    dry_run: bool,
    repo_root: str | None = None,
    cwd: str | None = None,
) -> dict:
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}, expected one of {sorted(AGENTS)}")
    if not target_paths:
        raise ValueError("target_paths must be non-empty")
    # bridge-invoke.mjs itself refuses danger-full-access -- rejected here too,
    # as a local, no-cost defense-in-depth check across the process boundary,
    # not a replacement for the bridge's own authoritative refusal.
    if execution_profile == "danger-full-access":
        raise ValueError(
            "execution_profile 'danger-full-access' is always refused by "
            "codex-review-bridge -- use codex-windows-guardrails instead for that profile"
        )
    # Validated before any path is constructed from it -- dispatch_id is
    # caller-supplied and was previously interpolated straight into a
    # filesystem path with no check, letting a value like "../../foo" write
    # the agent body outside the intended scratch directory (found by
    # security-reviewer, see GitHub issue #251's finalize session).
    if not _DISPATCH_ID_RE.fullmatch(dispatch_id):
        raise ValueError(
            f"dispatch_id {dispatch_id!r} does not match {_DISPATCH_ID_RE.pattern} "
            "-- refusing to use it in a filesystem path"
        )

    plugin_root = Path(__file__).resolve().parent.parent
    checkout = checkout_of(plugin_root)
    root = Path(repo_root).resolve() if repo_root else checkout or repo_root_from(Path.cwd())
    cwd_path = Path(cwd).resolve() if cwd else root
    # relposix() below computes every path relative to `root`, but --cwd is
    # what the dispatched Node process actually resolves relative paths
    # against -- an independently-supplied --cwd that diverges from root
    # would silently make every --target-paths/--instruction-file value
    # wrong from that process's own perspective (found by cross-model review,
    # GitHub issue #251's finalize session). Rejected here rather than
    # supporting two independent roots, which nothing currently needs.
    if cwd_path != root:
        raise ValueError(
            f"--cwd {cwd_path} must equal the resolved repo root {root} -- "
            "every path this script computes is relative to root, not an "
            "independently-configurable --cwd"
        )

    agent_file = plugin_root / "agents" / f"{agent}.md"
    if not agent_file.is_file():
        raise FileNotFoundError(agent_file)
    body = strip_frontmatter(agent_file.read_text(encoding="utf-8"))

    # A relative target path must resolve against `root`, not the process's
    # actual OS cwd -- Path.resolve() on a relative path resolves against
    # Path.cwd(), which only matches `root` by coincidence unless the caller
    # happens to invoke this script from the repo root itself. A caller using
    # --repo-root from a different directory would otherwise get a target
    # resolved against the wrong base (found by Codex/CodeRabbit/Devin's
    # PR #278 review).
    resolved_targets = [
        (Path(t) if Path(t).is_absolute() else root / t).resolve() for t in target_paths
    ]
    # The bridge accepts a missing target (a deleted file), so a review of nothing could
    # come back looking valid.
    for target in resolved_targets:
        if not target.exists():
            raise FileNotFoundError(f"target path does not exist: {target}")

    # Scratch instruction file: a fresh OS temp directory, deliberately
    # OUTSIDE the repository entirely. An earlier version put this under
    # `root/.temp/`, reasoning that bridge-invoke.mjs's repo-root containment
    # check required it -- that reasoning was wrong: --instruction-file is
    # explicitly NOT bound by that check (bridge-invoke.mjs's own comment:
    # "instruction-file is deliberately NOT bound by the repo-root
    # containment gate... plugin-auditor's documented Codex path writes the
    # trusted reviewer instructions to the session scratchpad precisely
    # because that directory must live OUTSIDE the repository root"). Being
    # inside root meant a broad --target-paths entry (e.g. the repo root
    # itself, ".") would always contain the scratch dir too, rejecting every
    # such dispatch via the nested-instruction-file check that used to live
    # here (found by Codex's PR #278 full review). A directory outside the
    # repo entirely can never be contained by any --target-paths value, so
    # that check is no longer needed at all.
    scratch_dir = Path(tempfile.mkdtemp(prefix="workmanagement-kit-bridge-"))
    instruction_file = scratch_dir / f"{dispatch_id}-{agent}-instruction.md"
    instruction_file.write_text(body, encoding="utf-8")

    # Everything from here on must run inside the try/finally below --
    # instruction_file now exists on disk, and every remaining precondition
    # check (the bridge_script existence check right below included) can
    # still raise before dispatch ever happens. An earlier version only
    # wrapped the subprocess.run call itself, so a missing bridge_script
    # raised FileNotFoundError before the try block even started, leaking
    # the instruction file on every such failure (found by Devin's PR #278
    # round-2 review).
    try:
        # The working directory's repository too: --repo-root must not be able to narrow
        # what counts as "inside the repository under review".
        forbidden = repository_roots(root)
        try:
            cwd_root = repo_root_from(Path.cwd())
        except ValueError:
            cwd_root = None
        if cwd_root is not None:
            forbidden += repository_roots(cwd_root)
        bridge_script = find_bridge(checkout, forbidden)
        node = _node(forbidden)
        search_path = _safe_path(forbidden)
        if not search_path:
            # With an empty PATH the bridge would find codex in the working directory.
            raise ValueError("no PATH entry is usable outside the repository under review")
        # GIT_* and NODE_* variables can preload code.
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.upper().startswith(("GIT_", "NODE_")) and k.upper() != "PATH"
        }
        env["PATH"] = search_path
        # Otherwise cmd.exe, running an npm codex shim, finds a bare `node` in the working
        # directory, the repository under review, before PATH.
        env["NoDefaultCurrentDirectoryInExePath"] = "1"

        # bridge-invoke.mjs validates --target-paths (but NOT
        # --instruction-file -- see the scratch_dir comment above) against
        # ^[A-Za-z0-9._/-]+$ -- no backslash (Windows' native separator) and
        # no colon (a Windows drive letter, e.g. "C:") are in that charset.
        # An absolute Windows path fails this check either way it's
        # rendered, so every --target-paths value handed to the bridge must
        # be relative to --cwd, using forward slashes. --instruction-file
        # carries no such restriction and is passed as an absolute path
        # unchanged, since it now lives outside `root` and has no
        # `root`-relative form to begin with.
        def relposix(p: Path) -> str:
            return p.relative_to(root).as_posix()

        cmd = [
            node,
            str(bridge_script),
            "--reviewer-type",
            agent,
            "--instruction-file",
            str(instruction_file.resolve()),
            "--target-paths",
            ",".join(relposix(tp) for tp in resolved_targets),
            "--execution-profile",
            execution_profile,
            "--dispatch-id",
            dispatch_id,
            "--cwd",
            cwd_path.as_posix(),
        ]
        if agent == "work-intake-classifier":
            # The repository's AGENTS.md and skills must not steer a classification.
            cmd += ["--isolate-project", "true"]
        if dry_run:
            cmd += ["--dry-run", "true"]

        # encoding="utf-8" is required explicitly -- subprocess.run's
        # text=True alone decodes with the platform's locale-preferred
        # encoding (cp1252 on a default Windows install, not UTF-8), which
        # silently corrupts any non-ASCII character (e.g. an em dash) the
        # child process writes as UTF-8.
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(root), env=env
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        # bridge-invoke.mjs writes every typed failure via console.error
        # (stderr) and only a real success envelope via console.log
        # (stdout) -- verified directly against its source. Parsing stdout
        # only silently discarded the bridge's own failure category (e.g.
        # isolation_profile_unavailable, cli_unavailable) on every real
        # failure, always falling back to the generic
        # bridge_caller_invocation_error below (found by Codex/Devin's
        # PR #278 review).
        try:
            payload_text = stdout if stdout else stderr
            payload = json.loads(payload_text) if payload_text else None
        except json.JSONDecodeError:
            payload = None

        if payload is None:
            return {
                "ok": False,
                "category": "bridge_caller_invocation_error",
                "detail": {
                    "returncode": result.returncode,
                    "stdout": stdout[-4000:],
                    "stderr": stderr[-4000:],
                },
            }
        return payload
    finally:
        # Otherwise every dispatch -- success or failure -- permanently
        # leaves a file (and now a whole temp directory) behind (found by
        # Devin's PR #278 round-2 review). Runs on every exit path,
        # including a subprocess.run OSError propagating out of this
        # function. rmdir() only removes an empty directory -- since this
        # scratch_dir is a fresh mkdtemp() used for exactly one file, it's
        # always empty immediately after that file is unlinked; ignored if
        # something unexpected leaves it non-empty rather than failing the
        # whole dispatch over cleanup.
        instruction_file.unlink(missing_ok=True)
        try:
            scratch_dir.rmdir()
        except OSError:
            pass


class _Parser(argparse.ArgumentParser):
    """Python before 3.13 still exits for a missing or unknown option with exit_on_error=False."""

    def error(self, message: str) -> NoReturn:
        raise argparse.ArgumentError(None, message)


def main() -> None:
    # exit_on_error=False: without it, an invalid --agent choice or a missing
    # required option makes parse_args() print a raw argparse usage message
    # to stderr and call sys.exit(2) directly -- bypassing this script's own
    # documented typed-JSON-failure contract entirely, since that happens
    # before the try/except below ever runs (found by CodeRabbit's PR #278
    # review). With it, parse_args() raises argparse.ArgumentError instead,
    # which is caught below like any other precondition failure. -h/--help
    # is unaffected -- argparse's help action still calls sys.exit(0)
    # directly regardless of this flag, which is the correct, expected
    # behavior for --help, not a failure to convert.
    parser = _Parser(description=__doc__, exit_on_error=False)
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--target-paths", required=True, help="comma-separated evidence paths")
    parser.add_argument("--dispatch-id", required=True)
    parser.add_argument("--execution-profile", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo-root")
    parser.add_argument("--cwd")

    # Every one of dispatch()'s own precondition checks, argument-parsing
    # failures (see exit_on_error above), and subprocess.run's own OSError
    # (e.g. node missing/unlaunchable), previously propagated as an uncaught
    # traceback or a bare non-JSON exit instead of this script's documented
    # dict/typed-failure return -- found live during this session's own
    # C1-fix verification, by cross-model review, and by CodeRabbit's PR #278
    # review (GitHub issue #251's finalize session). Caught here so every
    # failure path returns the same shape.
    try:
        args = parser.parse_args()
        result = dispatch(
            agent=args.agent,
            target_paths=[p for p in args.target_paths.split(",") if p],
            dispatch_id=args.dispatch_id,
            execution_profile=args.execution_profile,
            dry_run=args.dry_run,
            repo_root=args.repo_root,
            cwd=args.cwd,
        )
    except (ValueError, RuntimeError, OSError, argparse.ArgumentError) as exc:
        result = {
            "ok": False,
            "category": "bridge_caller_precondition_error",
            "detail": str(exc),
        }
    print(json.dumps(result, indent=2))
    sys.exit(1 if isinstance(result, dict) and result.get("ok") is False else 0)


if __name__ == "__main__":
    main()
