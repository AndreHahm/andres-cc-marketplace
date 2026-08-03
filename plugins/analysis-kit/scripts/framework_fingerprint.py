#!/usr/bin/env python3
"""Detects which developer framework(s) a project uses.

Priority order:
1. framework_override in .claude/analysis-kit.local.json (if present) -- always wins.
2. framework_override in <plugin-root>/analysis-kit.settings.json (git-tracked default).
3. Auto-detection against a framework-signatures.json file's marker paths.

Signature confidence is reported explicitly -- a "low" confidence entry means
its marker paths are unconfirmed against the real tool's own documented
conventions and should be corrected once verified, not trusted at face value.
"""

import argparse
import json
import sys
from pathlib import Path


def _load_json(path: Path):
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def detect(project_root: Path, signatures_path: Path, plugin_root: Path) -> dict:
    local_override = _load_json(project_root / ".claude" / "analysis-kit.local.json") or {}
    if local_override.get("framework_override"):
        return {
            "source": "local_override",
            "framework": local_override["framework_override"],
            "confidence": "declared",
        }

    settings = _load_json(plugin_root / "analysis-kit.settings.json") or {}
    if settings.get("framework_override"):
        return {
            "source": "settings_default",
            "framework": settings["framework_override"],
            "confidence": "declared",
        }

    signatures = _load_json(signatures_path) or {}
    candidates = []
    for framework_id, spec in signatures.items():
        matched = [m for m in spec.get("markers", []) if (project_root / m).exists()]
        if matched:
            candidates.append({
                "framework": framework_id,
                "label": spec.get("label", framework_id),
                "confidence": spec.get("confidence", "unknown"),
                "matched_markers": matched,
                "note": spec.get("note"),
            })

    if not candidates:
        return {
            "source": "auto_detect",
            "framework": None,
            "candidates": [],
            "note": (
                "No known framework markers matched. If this project uses a framework "
                "not in framework-signatures.json, add it there or set framework_override."
            ),
        }

    return {"source": "auto_detect", "framework": None, "candidates": candidates}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Project root to scan")
    parser.add_argument("--signatures", required=True, help="Path to framework-signatures.json")
    parser.add_argument("--plugin-root", required=True, help="analysis-kit plugin root (for analysis-kit.settings.json)")
    args = parser.parse_args()

    result = detect(
        Path(args.project_root).resolve(),
        Path(args.signatures).resolve(),
        Path(args.plugin_root).resolve(),
    )
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
