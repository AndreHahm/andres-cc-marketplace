#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Config loader for workledger-kit: a git-tracked defaults file plus an optional gitignored local
override, both JSON, with a trust boundary.

Defaults:  <plugin root>/workledger-kit.settings.json   (ships with the plugin; `repos` is empty,
so a
                                                         project must onboard its own repository)
Override:  <repo root>/.claude/workledger-kit.local.json (per project, gitignored)

Trust boundary. A local file that git does not list is trusted because it is UNTRACKED: nobody with
repo write access could have committed it. That is all this check proves. It does not prove who
wrote
the file: `onboarding-repositories` writes it after approval, but any `Write` (three skills
pre-approve it, for
plugin-rulebook R6) or the person can change it, so a skill that is about to submit re-reads the
config first.

A "local" file that git reports as TRACKED could have been committed by anyone with repo write
access,
so it is not honored for fields that widen what the plugin reads, where it writes, or whether it may
submit: `repos`, `digest`, `intake_capabilities`. Tracked-ness is decided by listing the index and
comparing names case-insensitively and Unicode-normalized (on Windows and macOS a file committed as
`WorkLedger-Kit.local.json` opens under the lowercase name while a plain pathspec lookup misses it).
The file also counts as tracked when it sits under a gitlink (a submodule at `.claude`), or when the
folder holding it belongs to a different git work tree, or when git cannot answer, or when it is a
symlink. Unknown keys in a local file are dropped with a warning (an allowlist, not a denylist).

The repo-to-Linear-team mapping is NOT configured here: this plugin sends only `owner/repo` and
workmanagement-kit resolves the team.

The one working folder (`digest.output_dir`: relative, inside the repo, gitignored, no symlink,
and no
tracked entries) is where every script reads and writes. Scripts take plain file names inside it.

Usage: wlgr_config.py   (run from inside the repository)
       -> {"settings", "warnings", "problems", "local_override": {"exists", "tracked"},
           "repo_root", "workdir"}
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 -- list-form calls only, never a shell
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wlgr_paths  # noqa: E402

os.environ["NoDefaultCurrentDirectoryInExePath"] = (
    "1"  # inherited by children: no current-directory exe search
)

SETTINGS_NAME = "workledger-kit.settings.json"
LOCAL_RELATIVE = Path(".claude") / "workledger-kit.local.json"
ALLOWED_KEYS = ("version", "repos", "digest", "intake_capabilities")
TRUST_GATED_FIELDS = ("repos", "digest", "intake_capabilities")
CAPABILITY_KEYS = ("batch", "query", "update", "classify")
_SLUG_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def valid_slug(slug: object) -> bool:
    """owner/repo; neither half may be all dots (`../..` would reach other API paths)."""
    return (
        isinstance(slug, str)
        and bool(_SLUG_RE.fullmatch(slug))
        and not any(set(part) <= {"."} for part in slug.split("/"))
    )


def _git(
    repo_root: Path, *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess | None:
    """Run git from PATH only (an absolute PATH entry, never the current directory and never
    inside the
    repository). `cwd` is where git runs (default the repo root). None means git could not be run,
    which every caller treats as 'cannot prove anything' and fails closed."""
    exe = wlgr_paths.find_exe("git", [repo_root])
    if exe is None:
        return None
    try:
        # List-form call, no shell: exe is an absolute PATH entry found by find_exe, and every
        # caller passes a fixed git subcommand (a path argument follows a "--" separator).
        return subprocess.run(  # nosec B603  # nosemgrep
            [exe, "-C", str(cwd or repo_root), *args], capture_output=True
        )
    except OSError:
        return None


def _norm(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def _index_entries(repo_root: Path) -> list[tuple[str, str]] | None:
    """[(mode, path)] for every index entry, or None if git cannot answer."""
    result = _git(repo_root, "ls-files", "-s", "-z")
    if result is None or result.returncode != 0:
        return None
    entries = []
    for raw in result.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if raw:
            meta, _, path = raw.partition("\t")
            entries.append((meta.split(" ", 1)[0], path))
    return entries


def is_tracked(path: Path, repo_root: Path) -> bool:
    """Fail closed: True unless the index definitely does not list this file. True when any of these
    holds: git cannot answer; the path is outside the repo; it is a symlink; a different git work
    tree
    owns its folder; an index entry has the same name case-insensitively and NFC-normalized; or a
    gitlink (a submodule) covers a parent directory."""
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        wlgr_paths.confine(
            path, repo_root
        )  # a link anywhere along the path (for example `.claude`) is untrusted
    except (ValueError, OSError):
        return True
    if path.is_symlink():
        return True
    entries = _index_entries(repo_root)
    if entries is None:
        return True
    target = _norm(rel)
    for mode, name in entries:
        n = _norm(name)
        if n == target or (mode == "160000" and target.startswith(n.rstrip("/") + "/")):
            return True
    top = _git(repo_root, "rev-parse", "--show-toplevel", cwd=path.parent)
    if top is None or top.returncode != 0:
        return True
    try:
        return not Path(top.stdout.decode("utf-8").strip()).samefile(repo_root)
    except OSError:
        return True


def is_ignored(rel_path: str, repo_root: Path) -> bool:
    """True only if git definitely reports the path as ignored (exit 0); fail closed otherwise."""
    result = _git(repo_root, "check-ignore", "-q", "--", rel_path)
    return result is not None and result.returncode == 0


def has_tracked_entries(rel_dir: str, repo_root: Path) -> bool:
    """True if the index lists anything at or under `rel_dir`, or git cannot answer (fail
    closed)."""
    entries = _index_entries(repo_root)
    if entries is None:
        return True
    prefix = _norm(rel_dir.strip("/")) + "/"
    return any(
        _norm(name).startswith(prefix) or _norm(name) == prefix.rstrip("/") for _, name in entries
    )


def _safe_relative(value: object) -> bool:
    """A relative path with no '..' segment and no stream or reserved segment. A leading '/' or
    '\\' is
    rejected explicitly because on Windows Path('/etc').is_absolute() is False."""
    if not isinstance(value, str) or not value or value.strip("./\\") == "":
        return False
    p = Path(value)
    return (
        not p.is_absolute()
        and ".." not in p.parts
        and not value.startswith(("/", "\\"))
        and not re.match(r"^[A-Za-z]:", value)
        and all(wlgr_paths._bad_segment(part) is None for part in p.parts if part != ".")
    )


def validate(
    settings: dict,
    repo_root: Path,
    ignored: Callable[[str, Path], bool] = is_ignored,
    tracked_under: Callable[[str, Path], bool] = has_tracked_entries,
) -> list[str]:
    """Return a list of problems; empty means the merged settings are usable."""
    problems: list[str] = []
    repos = settings.get("repos")
    if not isinstance(repos, list) or not repos:
        problems.append(
            "repos is empty: onboard a repository first (the onboarding-repositories skill)"
        )
    else:
        for r in repos:
            if not isinstance(r, dict) or not valid_slug(r.get("slug")):
                problems.append(f"repo entry needs a slug like owner/repo: {r!r}")
                continue
            dirs = r.get("report_dirs", [])
            if not isinstance(dirs, list):
                problems.append(f"report_dirs must be a list: {dirs!r}")
                dirs = []
            for d in dirs:
                if not _safe_relative(d):
                    problems.append(
                        f"report_dirs entry must be a relative path without '..': {d!r}"
                    )
    digest = settings.get("digest")
    out = digest.get("output_dir") if isinstance(digest, dict) else None
    if not _safe_relative(out):
        problems.append(f"digest.output_dir must be a relative path without '..': {out!r}")
    else:
        try:
            resolved = wlgr_paths.confine(repo_root / str(out), repo_root)
            rel = resolved.relative_to(repo_root.resolve()).as_posix()
            if rel in ("", "."):
                raise ValueError("it is the repository root")
        except ValueError as exc:
            problems.append(f"digest.output_dir {out!r} is unsafe: {exc}")
        else:
            if not ignored(rel.rstrip("/") + "/x", repo_root):
                problems.append(
                    f"digest.output_dir {out!r} is not gitignored; working files must never land "
                    f"in a tracked folder"
                )
            if tracked_under(rel, repo_root):
                problems.append(
                    f"digest.output_dir {out!r} contains tracked files (or git cannot be asked); "
                    f"it must hold working files only"
                )
    caps = settings.get("intake_capabilities")
    if (
        not isinstance(caps, dict)
        or set(caps) != set(CAPABILITY_KEYS)
        or not all(isinstance(v, bool) for v in caps.values())
    ):
        problems.append(
            f"intake_capabilities must be an object of booleans with exactly the keys "
            f"{list(CAPABILITY_KEYS)}"
        )
    return problems


def load_settings(
    plugin_root: Path,
    repo_root: Path,
    tracked: Callable[[Path, Path], bool] = is_tracked,
) -> tuple[dict, list[str]]:
    """Merge defaults and the optional local override; return (settings, warnings)."""
    warnings: list[str] = []
    settings = json.loads((plugin_root / SETTINGS_NAME).read_text(encoding="utf-8"))
    local_path = repo_root / LOCAL_RELATIVE
    if not local_path.is_file():
        return settings, warnings
    try:
        wlgr_paths.confine(local_path, repo_root)
    except ValueError as exc:
        return settings, [f"{LOCAL_RELATIVE} ignored: {exc}"]
    try:
        local = json.loads(wlgr_paths.read_text(local_path))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return settings, [f"{LOCAL_RELATIVE} is not readable JSON ({exc}); ignored"]
    if not isinstance(local, dict):
        return settings, [f"{LOCAL_RELATIVE} must be a JSON object; ignored"]
    trusted = not tracked(local_path, repo_root)
    for key, value in local.items():
        if key not in ALLOWED_KEYS:
            warnings.append(f"dropped unknown key '{key}' from {LOCAL_RELATIVE}")
        elif key in TRUST_GATED_FIELDS and not trusted:
            warnings.append(
                f"refused '{key}' from {LOCAL_RELATIVE}: the file is tracked (or tracked-ness "
                f"could not be "
                "determined), so it cannot widen reads, change the working folder or unlock "
                "submission"
            )
        else:
            settings[key] = value
    return settings, warnings


def local_override_state(
    repo_root: Path, tracked: Callable[[Path, Path], bool] = is_tracked
) -> dict:
    """{"exists": bool, "tracked": bool|None}: lets a caller stop before writing into a tracked
    file."""
    path = repo_root / LOCAL_RELATIVE
    exists = path.is_file()
    return {"exists": exists, "tracked": tracked(path, repo_root) if exists else None}


def repo_root_from_cwd() -> Path:
    """The repository root of the current directory, found by walking up to the first `.git` entry
    (never by running git, which must itself be searched for outside the repository). Scripts never
    accept a repo path from the model."""
    root = wlgr_paths.find_repo_root(Path.cwd())
    if root is None:
        raise ValueError("not inside a git repository (no .git found above the current directory)")
    return root


def workdir(
    plugin_root: Path = PLUGIN_ROOT, repo_root: Path | None = None, create: bool = True
) -> Path:
    """The validated working folder. Raises ValueError listing every config problem."""
    repo_root = repo_root or repo_root_from_cwd()
    settings, _warnings = load_settings(plugin_root, repo_root)
    problems = validate(settings, repo_root)
    if problems:
        raise ValueError("; ".join(problems))
    path = wlgr_paths.confine(repo_root / settings["digest"]["output_dir"], repo_root)
    if create:
        path.mkdir(parents=True, exist_ok=True)
        path = wlgr_paths.confine(path, repo_root)
    return path


def work_file(name: str, **kw) -> Path:
    """A file inside the working folder, by plain name. The full path is confined, so a symlink
    planted at the file itself is refused, not followed."""
    folder = workdir(**kw)
    target = folder / wlgr_paths.work_name(name)
    return wlgr_paths.confine(target, folder)


def read_work(name: str, **kw) -> str:
    return wlgr_paths.read_text(work_file(name, **kw))


def write_work(name: str, text: str, **kw) -> Path:
    path = work_file(name, **kw)
    wlgr_paths.write_text(path, text)
    return path


def repo_entry(slug: str, settings: dict) -> dict:
    """The configured entry for `slug`, or ValueError: collectors only read configured
    repositories."""
    for r in settings.get("repos", []):
        if r.get("slug") == slug:
            return r
    raise ValueError(f"{slug!r} is not a configured repository")


def main(argv: list[str]) -> int:
    wlgr_paths.utf8_stdio()
    if argv:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        repo_root = repo_root_from_cwd()
    except ValueError as exc:
        print(json.dumps({"problems": [str(exc)]}))
        return 1
    settings, warnings = load_settings(PLUGIN_ROOT, repo_root)
    problems = validate(settings, repo_root)
    out = {
        "settings": settings,
        "warnings": warnings,
        "problems": problems,
        "local_override": local_override_state(repo_root),
        "repo_root": str(repo_root),
    }
    if not problems:
        out["workdir"] = str(workdir(PLUGIN_ROOT, repo_root))
    print(json.dumps(out, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
