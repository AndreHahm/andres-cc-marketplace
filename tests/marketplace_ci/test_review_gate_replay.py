"""Replays the Codex review results CI saved for PR #856 (issue #862) through the gate. The
fixture holds each finding's recorded outcome, so a gate change shows up here as the exact
findings whose outcome it changes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.marketplace_ci.review import Finding, gate_decision

_FIXTURE = Path(__file__).parent / "fixtures" / "issue-862-replay" / "results.json"
_RUNS = json.loads(_FIXTURE.read_text(encoding="utf-8"))["runs"]
_RECORDED = ("in_diff", "blocking", "gate")
_CASES = [
    pytest.param(entry, id=f"{run['head_sha'][:8]}-{index}-{entry['rule']}")
    for run in _RUNS
    for index, entry in enumerate(run["findings"])
]


def _finding(entry: dict) -> Finding:
    fields = {k: v for k, v in entry.items() if k not in _RECORDED}
    fields["reporters"] = tuple(fields["reporters"])
    fields["components"] = tuple(fields["components"])
    return Finding(**fields)


def test_the_fixture_holds_every_saved_result():
    assert len(_RUNS) == 8
    assert all(run["blocking"] for run in _RUNS)


@pytest.mark.parametrize("entry", _CASES)
def test_the_gate_reproduces_the_outcome_ci_recorded(entry):
    decision = gate_decision(_finding(entry), in_diff=entry["in_diff"])
    assert decision.outcome == entry["gate"]
    assert (decision.outcome == "block") is entry["blocking"]


@pytest.mark.parametrize("run", _RUNS, ids=lambda run: run["head_sha"][:8])
def test_each_run_blocks_exactly_when_ci_did(run):
    own = any(
        gate_decision(_finding(entry), in_diff=entry["in_diff"]).outcome == "block"
        for entry in run["findings"]
    )
    assert (own or run["carried_blocking"] > 0) is run["blocking"]
