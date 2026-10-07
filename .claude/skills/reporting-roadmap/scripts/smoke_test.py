#!/usr/bin/env python3
"""Structural smoke test for this skill: frontmatter, referenced files and Bash grants.
The logic lives in the plugin's scripts/wlgr_smoke_checks.py (shared by every skill)."""

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR.parent.parent / "scripts"))

import wlgr_smoke_checks  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(wlgr_smoke_checks.run(SKILL_DIR))
