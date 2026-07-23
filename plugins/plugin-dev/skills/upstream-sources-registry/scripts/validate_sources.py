#!/usr/bin/env python3
"""Schema/consistency check for sources.json. Run after any manual edit.

Usage:
    python validate_sources.py [path/to/sources.json]
"""
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "id", "name", "url", "authority", "volatility", "enabled",
    "manual_rank_override", "cited_by", "last_verified",
    "last_verified_snapshot", "custom",
}
VALID_AUTHORITY = {"spec", "guide", "changelog", "informal"}
VALID_VOLATILITY = {"stable", "evolving", "frequent"}
VALID_RANK = {"critical", "standard", "opportunistic", None}


def main() -> int:
    sources_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "assets" / "sources.json"
    if not sources_path.exists():
        print(f"sources.json not found at {sources_path}", file=sys.stderr)
        return 1

    with open(sources_path, encoding="utf-8") as f:
        data = json.load(f)

    errors = []
    seen_ids = set()

    for i, source in enumerate(data.get("sources", [])):
        label = source.get("id", f"entry[{i}]")

        missing = REQUIRED_FIELDS - source.keys()
        if missing:
            errors.append(f"{label}: missing fields {sorted(missing)}")

        if source.get("id") in seen_ids:
            errors.append(f"{label}: duplicate id")
        seen_ids.add(source.get("id"))

        if source.get("authority") not in VALID_AUTHORITY:
            errors.append(f"{label}: invalid authority '{source.get('authority')}' (must be one of {sorted(VALID_AUTHORITY)})")

        if source.get("volatility") not in VALID_VOLATILITY:
            errors.append(f"{label}: invalid volatility '{source.get('volatility')}' (must be one of {sorted(VALID_VOLATILITY)})")

        if source.get("manual_rank_override") not in VALID_RANK:
            errors.append(f"{label}: invalid manual_rank_override '{source.get('manual_rank_override')}' (must be one of {sorted(r for r in VALID_RANK if r)} or null)")

        if not isinstance(source.get("enabled"), bool):
            errors.append(f"{label}: 'enabled' must be a bool")

        if not isinstance(source.get("custom"), bool):
            errors.append(f"{label}: 'custom' must be a bool")

        if not isinstance(source.get("cited_by"), list):
            errors.append(f"{label}: 'cited_by' must be an array")

    if errors:
        print(f"{len(errors)} issue(s) found:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: {len(data.get('sources', []))} source(s), no issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
