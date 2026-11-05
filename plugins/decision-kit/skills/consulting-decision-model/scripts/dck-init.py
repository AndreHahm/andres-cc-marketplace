#!/usr/bin/env python3
"""Create .env.example in the project, or add the OpenRouter entry to it. Prints one JSON object.

Never reads or writes .env itself. Standard library only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "dck_decide", Path(__file__).resolve().with_name("dck-decide.py")
)
assert SPEC is not None and SPEC.loader is not None
dck = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dck)

EXAMPLE_FILE = ".env.example"
NO_LINK = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
ENTRY = (
    "# OpenRouter API key for decision-kit. Copy this to .env and set your real key.\n"
    f"{dck.KEY_NAME}=your-openrouter-api-key\n"
)


def _write(path: Path, flags: int, data: bytes) -> None:
    """Only the new bytes are written, so a failure cannot cost the existing content."""
    descriptor = os.open(path, os.O_WRONLY | NO_LINK | flags, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def init(root: Path) -> dict:
    """Returns the action taken. A symlink or unreadable file is left alone."""
    path = root / EXAMPLE_FILE
    if path.is_symlink():
        return {"action": "refused", "reason": "is a symlink", "path": str(path)}
    if not path.exists():
        _write(path, os.O_CREAT | os.O_EXCL, ENTRY.encode("utf-8"))
        return {"action": "created", "path": str(path)}
    data = path.read_bytes()
    try:
        lines = data.decode("utf-8-sig").splitlines()
    except ValueError:
        return {"action": "refused", "reason": "is not UTF-8 text", "path": str(path)}
    if any(dck.ENV_LINE.fullmatch(line) for line in lines):
        return {"action": "unchanged", "path": str(path)}
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    start = newline if data and not data.endswith(b"\n") else b""
    _write(path, os.O_APPEND, start + ENTRY.encode("utf-8").replace(b"\n", newline))
    return {"action": "added", "path": str(path)}


def main() -> int:
    try:
        result = init(Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()))
    except OSError as exc:
        result = {"action": "refused", "reason": type(exc).__name__}
    print(json.dumps(result))
    return 1 if result["action"] == "refused" else 0


if __name__ == "__main__":
    sys.exit(main())
