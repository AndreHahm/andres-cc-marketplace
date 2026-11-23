"""Runs the codex-kit smoke tests the review gate depends on (issue #862): no workflow runs that
folder, and they are what ties the bridge's flags to the arguments and prompt Codex gets."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SMOKE = Path(__file__).resolve().parents[2] / "plugins" / "codex-kit" / "scripts" / "smoke-tests"


@pytest.mark.skipif(os.name == "nt", reason="the codex stub is a POSIX script")
@pytest.mark.parametrize(
    "name", ["codex-review-bridge-finding-categories", "codex-review-bridge-isolate-project"]
)
def test_the_bridge_smoke_test_passes(name):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, str(SMOKE / f"{name}.mjs")], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert ", 0 failed" in result.stdout
