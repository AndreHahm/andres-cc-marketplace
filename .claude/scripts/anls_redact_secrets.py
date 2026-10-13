#!/usr/bin/env python3
"""Deterministic secret redaction for analysis-kit report text.

Applied immediately before every skill's `Write` to `.claude/output/` --
strips or masks common secret-shaped patterns from already-drafted report
text. Never fails or blocks the write: matched values are replaced with
`[REDACTED]` in place (structure is preserved), and text with no matches
passes through unchanged. A missing/unreadable --input-file is a genuine
script error (distinct from "no secrets found") and returns exit code 1.

Pattern set is intentionally conservative and pattern-based, not a general
secret-scanning service -- it catches common, recognizable shapes
(Authorization/Bearer headers, .env-shaped KEY=value lines, known cloud key
prefixes) rather than attempting exhaustive coverage. A generic high-entropy
catch-all was deliberately not included -- see the comment above _PATTERNS
for why it did more harm than good in this specific plugin.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import typing
from pathlib import Path


def _load_token_shapes(path: Path | None = None) -> list[tuple[str, re.Pattern]]:
    """Prefix-based token shapes, shared with the other redactors through one canonical file.

    anls-token-shapes.json is a byte-identical copy of scripts/marketplace_ci/token_shapes.json;
    edit that file and run `python -m scripts.marketplace_ci sync-token-shapes`, never this copy.
    Compiled with re.ASCII so a word boundary behaves like the JavaScript redactor's (the default
    Unicode boundary missed a token next to an accented or CJK character). A missing or
    malformed file raises at import: silently redacting nothing would fail open.
    """
    document = json.loads(
        (path or Path(__file__).with_name("anls-token-shapes.json")).read_text("utf-8")
    )
    valid = (
        isinstance(document, dict)
        and document.get("version") == 1
        and isinstance(document.get("shapes"), list)
        and bool(document["shapes"])
        and all(
            isinstance(shape, dict)
            and isinstance(shape.get("name"), str)
            and isinstance(shape.get("pattern"), str)
            and shape["pattern"]
            for shape in document["shapes"]
        )
    )
    if not valid:
        raise ValueError(
            "anls-token-shapes.json: expected version 1 and a non-empty list of name/pattern shapes"
        )
    return [(shape["name"], re.compile(shape["pattern"], re.ASCII)) for shape in document["shapes"]]


_TOKEN_SHAPES = _load_token_shapes()

# The token shapes above are shared; everything else here is this plugin's own. A sibling list,
# SECRET_PATTERNS in plugins/promptlibrary-kit/scripts/plib_catalog_validate.py, was seeded from
# these rules and diverges on purpose (extra shapes; it detects and blocks, never rewrites).
# When changing a non-shared pattern here, check whether the sibling needs the same change.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    # "authorization" alone is common English prose -- only treat it as a header when
    # followed by an explicit separator. "bearer" is rare enough outside real tokens
    # that it's caught even without one (defensive default: over-redact, not under-).
    ("authorization_header", re.compile(r"(?im)\bauthorization\s*[:=]\s*.+$")),
    ("bearer_token", re.compile(r"(?im)\bbearer\b\s*[:=]?\s*.+$")),
    (
        "dotenv_secret_line",
        re.compile(
            r"(?im)^\s*[A-Za-z_][A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|API)[A-Za-z0-9_]*\s*=\s*.+$"
        ),
    ),
    # The line-anchored rule above misses an assignment that is not at the start of a
    # line, and swallowing the rest of a mid-line match would eat surrounding prose, so
    # this one replaces only the value (the `keep` group is the name and stays). Unlike the
    # line-anchored rule, the noisy words KEY and API must be a whole `_`-delimited segment of the
    # name (or part of a known compound such as apiKey), so prose-embedded fields like
    # sortKey=asc are left alone; TOKEN, SECRET and PASSWORD may appear anywhere in the name
    # (databasePassword, DB_PASSWORD), since they rarely occur in non-secret names. A quoted
    # value runs to its closing quote, or to the end of its line when the quote is never
    # closed, so one stray quote cannot swallow the lines after it.
    (
        "dotenv_secret_assignment",
        re.compile(
            r"(?i)(?P<keep>\b(?:[A-Za-z0-9_]*"
            r"(?:TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|ACCESSKEY|AUTHKEY|PRIVATEKEY|SIGNINGKEY)"
            r"[A-Za-z0-9_]*|(?:[A-Za-z0-9]*_)*(?:KEY|API)(?:_[A-Za-z0-9_]*)?)[^\S\r\n]*=[^\S\r\n]*)"
            r"(?!\[REDACTED\])"
            r"""(?:"(?:[^"\\\r\n]|\\[^\r\n]?)*(?:"|(?=[\r\n])|$)"""
            r"""|'(?:[^'\\\r\n]|\\[^\r\n]?)*(?:'|(?=[\r\n])|$)|\S+)"""
        ),
    ),
    *_TOKEN_SHAPES,
    (
        "pem_private_key_block",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL
        ),
    ),
    # Matches only the drive/home-root-plus-username prefix (e.g. "C:\Users\andre",
    # "C:/Users/andre", "/home/andre", "/Users/andre") -- the character class excludes
    # both path separators, so it stops at the username and never consumes the trailing
    # repo-relative segment, which stays intact as citable evidence (per
    # anls-report-evidence-convention.md's "never a bare absolute path that reveals the OS
    # username" rule -- this is the mechanical backstop that rule already claimed to have).
    (
        "home_directory_path",
        re.compile(r"(?:[A-Za-z]:[\\/]Users[\\/][^\\/]+|/home/[^/]+|/Users/[^/]+)"),
    ),
]

# A generic "long mixed-alphanumeric string" entropy heuristic was tried and
# deliberately dropped: analysis-kit's own report filenames
# (<scope-slug>-<timestamp>.md, e.g. "smoke-test-fixture-a-2026-08-05T05-00-00Z")
# and relative paths built from them are themselves long, hyphenated, and
# mixed-case -- indistinguishable from a real secret to a naive length/charset
# check. That heuristic redacted this plugin's own file-path citations, which
# are exactly the evidence these reports exist to preserve. The named patterns
# above (known header/prefix/env-var shapes) catch realistic report-context
# secrets with far lower false-positive risk; a true entropy scanner would need
# a real detection library, not a regex, and is out of scope here.


def redact(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    result = text
    for name, pattern in _PATTERNS:

        def _sub(match: re.Match, _name=name) -> str:
            counts[_name] = counts.get(_name, 0) + 1
            return (match.groupdict().get("keep") or "") + "[REDACTED]"

        result = pattern.sub(_sub, result)
    return result, counts


def main() -> int:
    # Report text routinely contains em-dashes, arrows, and emoji (the standard
    # analysis-kit "written:" confirmation line). Windows' default console
    # encoding (cp1252) can't represent those -- force UTF-8 on stdio so this
    # script doesn't crash on the exact kind of text it's meant to process.
    typing.cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8", newline="\n")
    typing.cast(io.TextIOWrapper, sys.stdin).reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-file",
        default=None,
        help="Path to the drafted report text (default: read from stdin)",
    )
    args = parser.parse_args()

    if args.input_file:
        path = Path(args.input_file)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Error: could not read {path}: {exc}", file=sys.stderr)
            return 1
    else:
        text = sys.stdin.read()

    redacted, counts = redact(text)
    sys.stdout.write(redacted)

    if counts:
        summary = ", ".join(f"{name}={n}" for name, n in sorted(counts.items()))
        print(f"anls_redact_secrets: {summary}", file=sys.stderr)
    else:
        print("anls_redact_secrets: no matches", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
