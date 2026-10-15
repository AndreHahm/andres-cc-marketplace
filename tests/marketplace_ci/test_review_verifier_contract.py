"""Whole-module guarantees of the script verifiers (issue #576).

Every rule id they can emit is in the rule inventory with the same class, and the same head gives
the same findings on every run.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.marketplace_ci import review_contract
from scripts.marketplace_ci import review_verifiers as rv
from scripts.marketplace_ci.git_state import ChangedPath

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY = REPO_ROOT / "docs" / "review-rule-inventory.md"

SKILL = "plugins/demo-kit/skills/demo/SKILL.md"
SCRIPT = "plugins/demo-kit/scripts/tool.sh"


def _inventory() -> dict[str, dict[str, str]]:
    rows = {}
    for line in INVENTORY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `r") and not line.startswith("| `f"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7:
            rows[cells[0].strip("`")] = {"class": cells[2], "status": cells[5], "family": cells[6]}
    return rows


def test_every_rule_id_a_verifier_can_emit_is_a_phase_2_inventory_row_of_the_same_class():
    inventory = _inventory()
    for rule, rule_class in rv.VERIFIER_RULES.items():
        assert rule in inventory, rule
        assert inventory[rule]["class"] == rule_class, rule
        assert inventory[rule]["status"] == "phase-2", rule
        assert inventory[rule]["family"] != "-", rule


def test_the_rule_classes_are_the_contracts():
    assert set(rv.VERIFIER_RULES.values()) <= set(review_contract.RULE_CLASSES)


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo_exercising_every_verifier(git_repo):
    git_repo.stage(".claude/marketplace-sync.json", json.dumps({"scripts_mirrors": []}))
    git_repo.write("docs/guide.md", "guide")
    git_repo.write(SCRIPT, "#!/bin/sh\n").chmod(0o644)
    body = (
        "[guide](../../../../docs/guide.md)\n" + "```bash\n" + "x\n" * 35 + "```\n" + "line\n" * 520
    )
    git_repo.write(
        SKILL,
        "---\nname: demo\ndescription: short\n"
        "allowed-tools: Bash Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)\n---\n" + body,
    )
    return _commit(git_repo.root, "add")


def test_the_same_head_gives_the_same_findings_on_every_run(git_repo):
    _repo_exercising_every_verifier(git_repo)
    change = (ChangedPath("A", None, SKILL), ChangedPath("A", None, SCRIPT))
    first = rv.run_verifiers(git_repo.root, change, None)
    second = rv.run_verifiers(git_repo.root, change, None)
    assert first == second
    emitted = {f.rule for outcome in first for f in outcome.findings}
    assert emitted == {
        "r6-bash-scope",
        "r13-skillmd-line-count",
        "r21-description-length",
        "r18-code-block-line-count",
        "r34-escaping-path",
        "r37-executable-bit",
    }
    assert emitted <= set(rv.VERIFIER_RULES)


def test_the_order_of_the_change_list_does_not_change_the_findings(git_repo):
    _repo_exercising_every_verifier(git_repo)
    forward = (ChangedPath("A", None, SKILL), ChangedPath("A", None, SCRIPT))
    reverse = tuple(reversed(forward))
    assert rv.run_verifiers(git_repo.root, forward, None) == rv.run_verifiers(
        git_repo.root, reverse, None
    )
