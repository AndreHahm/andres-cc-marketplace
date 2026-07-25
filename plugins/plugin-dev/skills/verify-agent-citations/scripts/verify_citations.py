#!/usr/bin/env python3
"""Verify file:line + quote citations from an agent report against the real files on disk.

Checks each citation's line number is within range and its quoted text appears near that
line -- catches fabricated line numbers or misquoted text. Does not judge whether the
underlying finding is correct, only whether the cited evidence for it holds up.

Usage:
    python verify_citations.py --input citations.json
    python verify_citations.py < citations.json

Input: a JSON array of {"file": str, "line": int, "quote": str (optional)}.
"""
import argparse
import json
import sys
from pathlib import Path

CONTEXT_BEFORE = 3
CONTEXT_AFTER = 2


def verify_one(citation: dict) -> dict:
    path = Path(citation["file"])
    if not path.is_file():
        return {**citation, "status": "FILE_NOT_FOUND"}

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return {**citation, "status": "READ_ERROR", "error": str(e)}

    line_num = citation["line"]
    if not (1 <= line_num <= len(lines)):
        return {**citation, "status": "LINE_OUT_OF_RANGE", "file_length": len(lines)}

    start = max(0, line_num - 1 - CONTEXT_BEFORE)
    end = min(len(lines), line_num + CONTEXT_AFTER)
    snippet = "\n".join(lines[start:end])

    quote = citation.get("quote", "").strip()
    if quote and quote.lower() not in snippet.lower():
        return {**citation, "status": "QUOTE_NOT_FOUND", "actual_nearby": snippet}

    return {**citation, "status": "CONFIRMED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", help="Path to a JSON file of citations (default: read stdin)")
    args = parser.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        citations = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        return 2

    results = [verify_one(c) for c in citations]

    for r in results:
        print(f"{r['status']:16} {r['file']}:{r['line']}")

    bad = [r for r in results if r["status"] != "CONFIRMED"]
    if bad:
        print(f"\n{len(bad)}/{len(results)} citation(s) failed verification:", file=sys.stderr)
        for r in bad:
            detail = r.get("actual_nearby") or r.get("file_length") or r.get("error") or ""
            print(f"  {r['file']}:{r['line']} -- {r['status']} {detail}".rstrip(), file=sys.stderr)
        return 1

    print(f"\nAll {len(results)} citation(s) confirmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
