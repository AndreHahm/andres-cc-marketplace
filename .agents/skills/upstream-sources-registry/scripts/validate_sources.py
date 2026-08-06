#!/usr/bin/env python3
"""Schema/consistency check for sources.json. Run after any manual edit.

Usage:
    python validate_sources.py [path/to/sources.json]
"""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_FIELDS = {
    "id", "name", "url", "authority", "volatility", "enabled",
    "manual_rank_override", "cited_by", "last_verified",
    "last_verified_snapshot", "custom",
}
VALID_AUTHORITY = {"spec", "guide", "changelog", "informal"}
VALID_VOLATILITY = {"stable", "evolving", "frequent"}
VALID_RANK = {"critical", "standard", "opportunistic", None}

# Built-in (non-custom) sources must resolve to one of these domains -- a
# non-custom entry pointing anywhere else would mean the seed data itself was
# tampered with. Custom sources outside this list are allowed (that's the
# whole point of "add a custom source") but get a visible warning rather than
# a silent pass, since a URL is exactly what a later WebFetch/WebSearch step
# will treat as trusted enough to inform a rule-file edit.
ALLOWLISTED_DOMAINS = {"docs.claude.com", "code.claude.com", "github.com"}


def main() -> int:
    sources_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "assets" / "sources.json"
    if not sources_path.exists():
        print(f"sources.json not found at {sources_path}", file=sys.stderr)
        return 1

    try:
        with open(sources_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Malformed JSON in {sources_path} at line {e.lineno}, column {e.colno}: {e.msg}", file=sys.stderr)
        return 1

    errors = []
    warnings = []
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

        url = source.get("url") or ""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            errors.append(f"{label}: url must be https:// (got '{url}')")
        elif parsed.netloc.lower() not in ALLOWLISTED_DOMAINS:
            if source.get("custom"):
                warnings.append(f"{label}: custom source url domain '{parsed.netloc}' is outside the allowlist {sorted(ALLOWLISTED_DOMAINS)} -- review before trusting its fetched content")
            else:
                errors.append(f"{label}: non-custom source url domain '{parsed.netloc}' is outside the allowlist {sorted(ALLOWLISTED_DOMAINS)} -- built-in sources must resolve to a known domain")

    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"{len(errors)} issue(s) found:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: {len(data.get('sources', []))} source(s), no issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
