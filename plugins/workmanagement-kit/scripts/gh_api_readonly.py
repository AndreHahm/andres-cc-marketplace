#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read-only wrapper around `gh api` -- enforces GET-only requests.

`gh api`'s own CLI grammar has no way to express "GET-only" at the tool-permission
level: Claude Code's `Bash(gh api:*)` grant permits any argument, and `gh api`
itself switches to a write request the moment `-f`/`-F` is given, or `--method`/
`-X` names anything other than GET (verified against `gh api --help`: "The
default HTTP request method is GET normally and POST if any parameters were
added"). A skill that only ever needs to read GitHub state and grants
`Bash(gh api:*)` directly is broader than what it actually uses, with nothing at
the permission layer narrowing that back down -- a textual "this skill only
ever issues read calls" disclosure in the skill's own prose is not something
the tool-permission system can verify or enforce.

This wrapper closes that gap for the three workmanagement-kit skills that only
ever need a read: they grant `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/gh_api_readonly.py:*)`
instead of `Bash(gh api:*)`, so the permission grant itself is exactly as wide
as what they use, not wider.

Usage: gh_api_readonly.py <endpoint> [--jq <expr>] [--paginate]

Only `--jq` (read-side filtering) and `--paginate` (read-side pagination) are
permitted past the endpoint -- an explicit allowlist, not a denylist of known
write flags, so an unrecognized future `gh api` flag fails closed rather than
silently passing through untested. `--method` is always forced to `GET`
internally; a caller cannot override it.
"""

from __future__ import annotations

import subprocess
import sys

_ALLOWED_FLAGS = {"--jq", "--paginate"}


def main(argv: list[str]) -> int:
    if not argv:
        print("gh_api_readonly.py: missing endpoint argument", file=sys.stderr)
        return 2

    endpoint = argv[0]
    rest = argv[1:]

    i = 0
    while i < len(rest):
        token = rest[i]
        if token not in _ALLOWED_FLAGS:
            print(
                f"gh_api_readonly.py: rejected argument {token!r} -- only "
                f"{sorted(_ALLOWED_FLAGS)} are permitted through this read-only "
                "wrapper; --method/-f/-F/-X/--input and any other flag are refused",
                file=sys.stderr,
            )
            return 1
        if token == "--jq":
            if i + 1 >= len(rest):
                print("gh_api_readonly.py: --jq requires a value", file=sys.stderr)
                return 2
            i += 2
        else:
            i += 1

    cmd = ["gh", "api", "--method", "GET", endpoint, *rest]
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
