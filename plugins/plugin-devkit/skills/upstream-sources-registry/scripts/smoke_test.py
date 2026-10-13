#!/usr/bin/env python3
"""Persisted smoke test for upstream-sources-registry.

Covers frontmatter validity, referenced-file existence, `validate_sources.py`
against the real registry plus fixture-based positive and negative controls,
`compute_priority.py`'s derivation table, and its `manual_rank_override`
precedence. No network or LLM calls: the Freshness Check procedure (WebFetch /
WebSearch) is conversational and is deliberately not exercised here.
"""

import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SOURCES = SKILL_DIR / "assets" / "sources.json"
VALIDATE = SKILL_DIR / "scripts" / "validate_sources.py"
COMPUTE = SKILL_DIR / "scripts" / "compute_priority.py"


def _entry(**overrides):
    entry = {
        "id": "fixture-source",
        "name": "Fixture",
        "url": "https://docs.claude.com/en/docs/fixture",
        "authority": "spec",
        "volatility": "stable",
        "enabled": True,
        "manual_rank_override": None,
        "cited_by": [],
        "last_verified": "2026-01-01",
        "last_verified_snapshot": "snapshot",
        "custom": False,
    }
    entry.update(overrides)
    return entry


def _run(script, sources_path, timeout=300):
    return subprocess.run(
        [sys.executable, str(script), str(sources_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )


def _run_fixture(script, entries):
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "sources.json"
        path.write_text(json.dumps({"sources": entries}), encoding="utf-8")
        return _run(script, path)


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    for key in ("name", "description"):
        if not re.search(rf"^{key}:", fm, re.MULTILINE):
            return False, f"missing required frontmatter field '{key}'"
    return True, "frontmatter present and closed"


def check_reference_files_exist():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("## Reference Guide")
    if start == -1:
        return False, "no '## Reference Guide' section found"
    targets = {
        t
        for t in re.findall(r"\|\s*`([^`]+)`\s*\|", text[start:])
        if re.match(r"(assets|scripts|references)/", t)
    }
    if not targets:
        return False, "no file paths found in '## Reference Guide'"
    missing = sorted(t for t in targets if not (SKILL_DIR / t).is_file())
    if missing:
        return False, "Reference Guide file(s) do not exist: " + ", ".join(missing)
    return True, f"all {len(targets)} Reference Guide file path(s) exist"


def check_validate_real_registry():
    result = _run(VALIDATE, SOURCES)
    if result.returncode != 0:
        return False, f"validate_sources.py failed on assets/sources.json: {result.stdout.strip()}"
    return True, result.stdout.strip()


def check_validate_fixtures():
    good = _run_fixture(VALIDATE, [_entry()])
    if good.returncode != 0 or "OK:" not in good.stdout:
        return False, f"positive control failed: {good.stdout.strip()}"

    warned = _run_fixture(
        VALIDATE,
        [_entry(custom=True, url="https://example.org/post", authority="informal")],
    )
    if warned.returncode != 0 or "warning" not in warned.stdout:
        return False, "off-allowlist custom source should warn and still exit 0"

    negatives = {
        "invalid authority": ([_entry(authority="bogus")], "invalid authority"),
        "duplicate id": ([_entry(), _entry()], "duplicate id"),
        "non-https url": ([_entry(url="http://docs.claude.com/x")], "must be https"),
        "off-allowlist built-in": (
            [_entry(url="https://example.org/x")],
            "outside the allowlist",
        ),
        "missing field": ([{"id": "partial"}], "missing fields"),
    }
    for label, (entries, expected) in negatives.items():
        result = _run_fixture(VALIDATE, entries)
        if result.returncode == 0 or expected not in result.stdout:
            return False, f"negative control '{label}' not rejected as expected"
    return True, f"positive, warning and {len(negatives)} negative controls behave"


def _load_compute_module():
    spec = importlib.util.spec_from_file_location("compute_priority", COMPUTE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {COMPUTE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_derive_priority_table():
    derive = _load_compute_module().derive_priority
    cases = [
        (_entry(volatility="frequent", authority="changelog"), 5, "critical"),
        (_entry(authority="spec", cited_by=["R5"]), 5, "critical"),
        (_entry(authority="guide", volatility="evolving"), 5, "standard"),
        (_entry(authority="guide", volatility="stable"), 1, "opportunistic"),
        (_entry(authority="guide", volatility="stable"), 5, "standard"),
        (_entry(authority="informal", volatility="evolving"), 5, "opportunistic"),
        (_entry(authority="spec", cited_by=[]), 5, "standard"),
    ]
    for source, blast, expected in cases:
        got = derive(source, blast)
        if got != expected:
            return False, (
                f"derive_priority({source['authority']}/{source['volatility']}, "
                f"blast={blast}) = {got}, expected {expected}"
            )
    return True, f"{len(cases)} derivation cases match the documented tiers"


def check_override_precedence():
    # An override is applied without grepping the tree, so this stays fast.
    result = _run_fixture(
        COMPUTE,
        [_entry(volatility="stable", authority="informal", manual_rank_override="critical")],
    )
    if result.returncode != 0:
        return False, f"compute_priority.py failed: {result.stderr.strip()}"
    line = result.stdout.strip()
    if "critical" not in line or "manual_rank_override" not in line:
        return False, f"override did not win over the derived tier: {line}"
    return True, "manual_rank_override takes precedence over the derived tier"


def check_compute_real_registry():
    result = _run(COMPUTE, SOURCES)
    if result.returncode != 0:
        return False, f"compute_priority.py failed on assets/sources.json: {result.stderr.strip()}"
    count = len(json.loads(SOURCES.read_text(encoding="utf-8"))["sources"])
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if len(lines) != count:
        return False, f"expected {count} priority line(s), got {len(lines)}"
    return True, f"priority derived for all {count} source(s)"


CHECKS = [
    check_frontmatter,
    check_reference_files_exist,
    check_validate_real_registry,
    check_validate_fixtures,
    check_derive_priority_table,
    check_override_precedence,
    check_compute_real_registry,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
