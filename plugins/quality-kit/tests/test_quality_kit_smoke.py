"""Run quality-kit's three skill smoke tests under pytest, so coverage measures its scripts.

Each smoke test stays a standalone script (the skills and README run it directly); this file only
loads it in-process and asserts that its main() reports no failing check. Bytecode writing is turned
off while a script loads, because a stray __pycache__ in a plugin folder fails this repository's
prefix check.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent.parent / "skills"
SMOKE_TESTS = sorted(SKILLS.glob("*/scripts/smoke_test.py"))


def test_every_skill_smoke_test_is_found() -> None:
    names = {path.parent.parent.name for path in SMOKE_TESTS}
    assert {"collecting-analysis-findings", "resolving-analysis-findings", "using-codecov"} <= names


@pytest.mark.parametrize("path", SMOKE_TESTS, ids=lambda path: path.parent.parent.name)
def test_skill_smoke_test_passes(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    name = f"quality_kit_smoke_{path.parent.parent.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
