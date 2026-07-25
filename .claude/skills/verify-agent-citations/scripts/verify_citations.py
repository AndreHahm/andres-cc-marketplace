#!/usr/bin/env python3
"""Verify file:line + quote citations from an agent report against the real files on disk.

Checks each citation's line number is within range and its quoted text appears near that
line -- catches fabricated line numbers or misquoted text. Does not judge whether the
underlying finding is correct, only whether the cited evidence for it holds up.

Citation `file`/`line`/`quote` values originate from an agent's report -- untrusted content
that could be manipulated. Every cited path is confined to the repo root (reject anything
that resolves outside it, including absolute paths pointing elsewhere) before it is ever
read, and file content is never echoed back for a path that looks credential-shaped, even
one inside the repo root. This is not a general-purpose file reader.

Usage:
    python verify_citations.py --input citations.json
    python verify_citations.py --input citations.json --repo-root /path/to/repo
    python verify_citations.py < citations.json

Input: a JSON array of {"file": str, "line": int, "quote": str (optional)}.
"""
import argparse
import json
import sys
from pathlib import Path

CONTEXT_BEFORE = 3
CONTEXT_AFTER = 2

# Substrings that mark a path as credential-shaped -- content from a matching path is never
# echoed back, even when the path itself is legitimately inside the repo root (e.g. a
# gitignored .env file that still exists on disk).
SENSITIVE_PATH_PATTERNS = (
    ".env", ".pem", "_rsa", "id_ed25519", ".ssh", ".aws", ".npmrc", ".pypirc",
    ".git-credentials", ".pgpass", "credentials", "secret", "token", ".netrc",
)


def is_sensitive_path(path: Path) -> bool:
    lowered = str(path).lower()
    return any(pat in lowered for pat in SENSITIVE_PATH_PATTERNS)


def resolve_in_scope(file_str: str, repo_root: Path) -> tuple[Path | None, str | None]:
    """Resolve a citation's file path and confirm it stays within repo_root.

    Returns (resolved_path, None) if in scope, or (None, status) if not -- the caller
    must not read the file at all when status is returned, not just skip echoing it.
    """
    candidate = Path(file_str)
    target = candidate if candidate.is_absolute() else repo_root / candidate
    try:
        resolved = target.resolve()
    except OSError:
        return None, "INVALID_PATH"

    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None, "PATH_OUTSIDE_SCOPE"

    return resolved, None


def verify_one(citation: dict, repo_root: Path) -> dict:
    resolved, scope_error = resolve_in_scope(citation["file"], repo_root)
    if scope_error:
        return {**citation, "status": scope_error}

    if not resolved.is_file():
        return {**citation, "status": "FILE_NOT_FOUND"}

    try:
        lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
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
        result = {**citation, "status": "QUOTE_NOT_FOUND"}
        if is_sensitive_path(resolved):
            result["actual_nearby"] = "[redacted -- credential-shaped path, content not echoed]"
        else:
            result["actual_nearby"] = snippet
        return result

    return {**citation, "status": "CONFIRMED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", help="Path to a JSON file of citations (default: read stdin)")
    parser.add_argument("--repo-root", default=".", help="Root directory citations are confined to (default: cwd)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        citations = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        return 2

    results = [verify_one(c, repo_root) for c in citations]

    for r in results:
        print(f"{r['status']:20} {r['file']}:{r['line']}")

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
