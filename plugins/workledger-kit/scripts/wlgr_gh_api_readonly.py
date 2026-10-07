#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read-only wrapper around `gh api` -- enforces GET-only requests.

Same control as workmanagement-kit's `wmgt_gh_api_readonly.py`, carried as this plugin's own copy
because workledger-kit must stay self-contained (no cross-plugin script paths). Claude Code's
`Bash(gh api:*)` grant permits any argument, and `gh api` switches to a write request the moment
`-f`/`-F` is given or `--method`/`-X` names anything other than GET. Granting this wrapper instead
makes the permission grant exactly as wide as what the collectors use: reads only.

Usage: wlgr_gh_api_readonly.py <endpoint> [--jq <expr>] [--paginate]

Only `--jq` and `--paginate` are permitted past the endpoint (an allowlist, so an unrecognized
future `gh api` flag fails closed). `--method` is always forced to GET internally.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wlgr_paths  # noqa: E402

os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"  # inherited by children

_ALLOWED_FLAGS = {"--jq", "--paginate"}

# A REST path with an optional query string. No scheme, host, placeholder, shell metacharacter or
# space.
_ENDPOINT_RE = re.compile(r"/?[A-Za-z0-9_.][A-Za-z0-9_./?=&%,+:-]*")  # used with fullmatch

# gh's bundled jq supports env/$ENV/$__loc__, which would let a --jq value dump credentials
# (e.g. GITHUB_TOKEN) into this wrapper's stdout.
_JQ_ENV_LEAK_RE = re.compile(r"\benv\b|\$ENV\b|\$__loc__\b")


def build_command(argv: list[str]) -> tuple[list[str] | None, str | None, int]:
    """Validate argv; return (command, error message, exit code). Command is None on rejection."""
    if not argv:
        return None, "missing endpoint argument", 2

    endpoint, rest = argv[0], argv[1:]
    if endpoint.startswith("-"):
        return None, f"rejected endpoint {endpoint!r} -- endpoint must not look like a flag", 1
    if (
        not _ENDPOINT_RE.fullmatch(endpoint)
        or "://" in endpoint
        or endpoint.lstrip("/").split("?", 1)[0].lower() == "graphql"
    ):
        return (
            None,
            f"rejected endpoint {endpoint!r} -- only plain REST paths are permitted (no URL, "
            f"host, graphql or placeholder)",
            1,
        )

    i = 0
    while i < len(rest):
        token = rest[i]
        if token not in _ALLOWED_FLAGS:
            return (
                None,
                f"rejected argument {token!r} -- only {sorted(_ALLOWED_FLAGS)} are permitted; "
                "--method/-f/-F/-X/--input and any other flag are refused",
                1,
            )
        if token == "--jq":
            if i + 1 >= len(rest):
                return None, "--jq requires a value", 2
            if _JQ_ENV_LEAK_RE.search(rest[i + 1]):
                return (
                    None,
                    f"rejected --jq value {rest[i + 1]!r} -- env/$ENV/$__loc__ access is refused",
                    1,
                )
            i += 2
        else:
            i += 1

    return ["gh", "api", "--method", "GET", endpoint, *rest], None, 0


def main(argv: list[str]) -> int:
    cmd, error, code = build_command(argv)
    if cmd is None:
        print(f"wlgr_gh_api_readonly.py: {error}", file=sys.stderr)
        return code
    here = wlgr_paths.find_repo_root(Path.cwd())  # never run a gh that lives inside the repository
    exe = wlgr_paths.find_exe(
        "gh", [here] if here else []
    )  # PATH only: a repo could ship its own gh.exe
    if exe is None:
        print(
            "wlgr_gh_api_readonly.py: gh was not found on PATH (the current directory is never "
            "searched)",
            file=sys.stderr,
        )
        return 1
    return subprocess.run([exe, *cmd[1:]]).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
