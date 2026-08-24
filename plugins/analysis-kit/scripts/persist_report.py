#!/usr/bin/env python3
"""Shared report-persistence ritual for analysis-kit's report-producing skills.

Wraps the redact-then-write sequence every report-producing skill's own
Persist step independently re-describes in prose: read a scratch draft,
redact it via redact_secrets.redact(), verify the result is byte-level
LF-only, write the final file, re-verify the written file is still
LF-only, and print the standard confirmation line. Centralizes the exact
bug class this plugin already found and fixed once (redact_secrets.py's
missing newline="\\n" on stdout, which corrupted every report written on
Windows before that fix) behind one call site instead of ten
independently-trusting ones.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redact_secrets import redact  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")  # ty: ignore[unresolved-attribute]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", required=True, help="Path to the drafted report text")
    parser.add_argument(
        "--final",
        required=True,
        help="Final .claude/output/<skill>/<scope-slug>-<timestamp>.md path",
    )
    parser.add_argument(
        "--label",
        required=True,
        help="Report type label for the confirmation line, e.g. 'Session Analysis Report'",
    )
    args = parser.parse_args()

    scratch_path = Path(args.scratch)
    final_path = Path(args.final)

    try:
        text = scratch_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Error: could not read {scratch_path}: {exc}", file=sys.stderr)
        return 1

    redacted, counts = redact(text)
    redacted_bytes = redacted.encode("utf-8")

    if redacted_bytes.count(b"\r\n") != 0:
        print(
            "Error: redacted text still contains CRLF sequences before write "
            "-- refusing to persist a corrupted report",
            file=sys.stderr,
        )
        return 1

    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(redacted_bytes)

    written_bytes = final_path.read_bytes()
    if written_bytes.count(b"\r\n") != 0:
        print(
            f"Error: written file at {final_path} contains CRLF sequences after write "
            "-- the write itself introduced corruption",
            file=sys.stderr,
        )
        return 1

    if counts:
        summary = ", ".join(f"{name}={n}" for name, n in sorted(counts.items()))
        print(f"persist_report: redacted ({summary})", file=sys.stderr)
    else:
        print("persist_report: no redaction matches", file=sys.stderr)

    print(f"\U0001f4c4 {args.label} written: `{final_path}`")

    return 0


if __name__ == "__main__":
    sys.exit(main())
