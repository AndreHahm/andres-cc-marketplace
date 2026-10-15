"""Cross-checks for the review rule inventory (issue #576, #568 Phase 2): every rulebook rule
and every exceptions-registry id has a classified row, and the row vocabularies match the
review contract, so the inventory cannot drift from the code and rules it describes."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from scripts.marketplace_ci import review_contract as rc

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY = REPO_ROOT / "docs" / "review-rule-inventory.md"
SETTINGS = (
    REPO_ROOT
    / "plugins"
    / "plugin-devkit"
    / "skills"
    / "plugin-rulebook"
    / "assets"
    / "settings.json"
)
REGISTRY = REPO_ROOT / "scripts" / "marketplace_ci" / "review_exceptions.yaml"

COLUMNS = ("rule", "origin", "class", "check", "existing", "status", "family")
STATUSES = ("phase-2", "candidate", "existing", "model", "disabled")
FAMILIES = (
    "grant-to-body",
    "measurement",
    "path-and-mirror",
    "removed-identifier",
    "structure",
    "call-graph",
)
RULE_ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)+$")
RULEBOOK_ORIGIN = re.compile(r"\bR(\d+)\b")


def _rulebook_id(key: str) -> str:
    match = re.match(r"(R\d+)_", key)
    assert match, key
    return match.group(1)


def _inventory_section() -> list[str]:
    lines = INVENTORY.read_text(encoding="utf-8").splitlines()
    start = lines.index("## Inventory")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def _rows() -> list[dict[str, str]]:
    rows = []
    for line in _inventory_section():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert len(cells) == len(COLUMNS), f"row has {len(cells)} cells: {line}"
        row = dict(zip(COLUMNS, cells, strict=True))
        row["rule"] = row["rule"].strip("`")
        rows.append(row)
    return rows


def test_the_inventory_has_rows():
    assert len(_rows()) > 30


def test_rule_ids_are_unique_stable_kebab_case():
    ids = [r["rule"] for r in _rows()]
    assert len(ids) == len(set(ids)), sorted(i for i in ids if ids.count(i) > 1)
    assert [i for i in ids if not RULE_ID.match(i)] == []


def test_classes_come_from_the_review_contract():
    bad = [r["rule"] for r in _rows() if r["class"] not in rc.RULE_CLASSES]
    assert bad == []


def test_statuses_and_families_use_the_documented_vocabulary():
    rows = _rows()
    assert [r["rule"] for r in rows if r["status"] not in STATUSES] == []
    families = [r["rule"] for r in rows if r["status"] == "phase-2" and r["family"] not in FAMILIES]
    assert families == []
    # A family is named only for rows the Phase 2 issue covers.
    stray = [r["rule"] for r in rows if r["status"] != "phase-2" and r["family"] != "-"]
    assert stray == []


def test_model_rows_are_judgment_and_phase_2_rows_are_not():
    rows = _rows()
    assert [r["rule"] for r in rows if r["status"] == "model" and r["class"] != "judgment"] == []
    assert [r["rule"] for r in rows if r["status"] == "phase-2" and r["class"] == "judgment"] == []


def test_measurement_rows_are_phase_2_measurement_family_or_existing():
    # Only script verifiers may assert `measurement`, so a measurement row needs a script path.
    bad = [
        r["rule"]
        for r in _rows()
        if r["class"] == "measurement" and r["status"] not in ("phase-2", "existing", "candidate")
    ]
    assert bad == []


def test_every_rulebook_rule_has_a_row():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))["rules"]
    in_inventory = {f"R{n}" for r in _rows() for n in RULEBOOK_ORIGIN.findall(r["origin"])}
    wanted = {_rulebook_id(key) for key in settings}
    assert sorted(wanted - in_inventory) == []


def test_disabled_status_matches_the_rulebook_settings():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))["rules"]
    enabled = {_rulebook_id(key): cfg.get("enabled", True) for key, cfg in settings.items()}
    for row in _rows():
        origins = [f"R{n}" for n in RULEBOOK_ORIGIN.findall(row["origin"])]
        if len(origins) != 1 or not row["rule"].startswith(origins[0].lower() + "-"):
            continue
        assert (row["status"] == "disabled") == (not enabled[origins[0]]), row["rule"]


def test_every_exceptions_registry_rule_is_an_inventory_rule_id():
    entries = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["exceptions"]
    ids = {r["rule"] for r in _rows()}
    assert sorted({e["rule"] for e in entries} - ids) == []


def test_the_registry_ids_are_verifier_rule_ids_not_model_only():
    entries = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["exceptions"]
    by_id = {r["rule"]: r for r in _rows()}
    model_only = [e["rule"] for e in entries if by_id[e["rule"]]["status"] in ("model", "disabled")]
    # An entry only suppresses a script finding, so its rule must have a script path.
    assert model_only == []


@pytest.mark.parametrize("family", FAMILIES)
def test_each_phase_2_family_has_at_least_one_row(family):
    assert any(r["family"] == family for r in _rows())
