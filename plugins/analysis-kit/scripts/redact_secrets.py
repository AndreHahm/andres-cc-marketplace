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
import re
import sys
from pathlib import Path

_PATTERNS: list[tuple[str, re.Pattern]] = [
    # "authorization" alone is common English prose -- only treat it as a header when
    # followed by an explicit separator. "bearer" is rare enough outside real tokens
    # that it's caught even without one (defensive default: over-redact, not under-).
    ("authorization_header", re.compile(r"(?im)\bauthorization\s*[:=]\s*.+$")),
    ("bearer_token", re.compile(r"(?im)\bbearer\b\s*[:=]?\s*.+$")),
    ("dotenv_secret_line", re.compile(r"(?im)^\s*[A-Za-z_][A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|API)[A-Za-z0-9_]*\s*=\s*.+$")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+\b")),
    # Anthropic keys (sk-ant-api03-...) contain hyphens, so the character class
    # must span them -- unlike the removed high-entropy catch-all (see the note
    # below _PATTERNS), this stays anchored to the literal "sk-" prefix, which
    # doesn't collide with this plugin's own <scope-slug>-<timestamp> filenames.
    ("generic_sk_token", re.compile(r"\bsk-[A-Za-z0-9-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("jwt_token", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\b")),
    ("pem_private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)),
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
            return "[REDACTED]"
        result = pattern.sub(_sub, result)
    return result, counts


def main() -> int:
    # Report text routinely contains em-dashes, arrows, and emoji (the standard
    # analysis-kit "written:" confirmation line). Windows' default console
    # encoding (cp1252) can't represent those -- force UTF-8 on stdio so this
    # script doesn't crash on the exact kind of text it's meant to process.
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stdin.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", default=None, help="Path to the drafted report text (default: read from stdin)")
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
        print(f"redact_secrets: {summary}", file=sys.stderr)
    else:
        print("redact_secrets: no matches", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
