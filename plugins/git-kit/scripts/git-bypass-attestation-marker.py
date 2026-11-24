#!/usr/bin/env python3
"""Print the bypass-attestation comment body (git-bypass-attestation-protocol.md, step 3).

    git-bypass-attestation-marker.py <reason-file> <actor> <head-sha>

Replaces the `jq -n` grants merge-pr, commit and create-pr held for this one step (issue #861): any
`jq -n ...` prefix grant also pre-approves a program that reads `$ENV`, because jq takes its program
after the options. The reason is read from a file, so the shell never parses it. The output is only
the marker comment, with `created_at` set to the current UTC time.

The body is copied into a file with the Write tool, which can decode a backslash-u escape, so it
never holds one: a reason with an HTML comment delimiter (it would end the hidden comment early), a
backslash followed by `u`, or a non-printable character is refused instead of escaped.

The reason file may be any readable text file of at most 16 KiB (a `Read` as far as access goes).

Exit 0 with the body on stdout, 2 on any invalid input. Standard library only (`python3 -I`).
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
import time

MAX_REASON_BYTES = 16384
# Non-printable to Python, but ordinary in text: line breaks, tab, no-break space, emoji joiner.
ALLOWED = "\n\r\t" + chr(0xA0) + chr(0x200D)
ACTOR_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_-]{0,99})")
SHA_RE = re.compile(r"[0-9a-f]{40}")


class InvalidInput(Exception):
    pass


def read_reason(path: str) -> str:
    # lstat first: Windows has no O_NOFOLLOW.
    if not stat.S_ISREG(os.lstat(path).st_mode):
        raise InvalidInput("the reason file is not a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise InvalidInput("the reason file is not a regular file")
        raw = handle.read(MAX_REASON_BYTES + 1)
    if len(raw) > MAX_REASON_BYTES:
        raise InvalidInput("the reason file is too large")
    reason = raw.decode("utf-8").strip()
    if not reason:
        raise InvalidInput("the reason is empty")
    if any(delimiter in reason for delimiter in ("<!--", "-->", "--!>")):
        raise InvalidInput("the reason holds an HTML comment delimiter")
    if "\\u" in reason:
        raise InvalidInput("the reason holds a backslash followed by u")
    if any(not c.isprintable() and c not in ALLOWED for c in reason):
        raise InvalidInput("the reason holds a non-printable character")
    return reason


def build(reason: str, actor: str, head_sha: str, created_at: str) -> str:
    if not ACTOR_RE.fullmatch(actor):
        raise InvalidInput("the actor is not a GitHub user login")
    if not SHA_RE.fullmatch(head_sha):
        raise InvalidInput("the head SHA is not 40 lowercase hexadecimal characters")
    marker = {
        "schema_version": 1,
        "actor": actor,
        "head_sha": head_sha,
        "reason": reason,
        "created_at": created_at,
    }
    payload = json.dumps(marker, ensure_ascii=False)
    return f"<!-- marketplace-ci-bypass-attestation {payload} -->"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: git-bypass-attestation-marker.py <reason-file> <actor> <head-sha>",
            file=sys.stderr,
        )
        return 2
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        body = build(read_reason(argv[0]), argv[1], argv[2], now)
    except InvalidInput as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as exc:
        print(f"cannot read the reason file: {type(exc).__name__}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(body.encode("utf-8") + b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
