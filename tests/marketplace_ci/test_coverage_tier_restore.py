"""Runs coverage.yml's trusted-restore step against a stub `gh` for each state of the base branch.

The step decides which copies of the tier script, its defaults, its hash-pinned dependencies and the
repository override the tier job trusts. Before this test it was checked only by reading.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "coverage.yml"
STEP_ID = "id: restore"
TIER = "plugins/quality-kit/scripts/qlty-coverage-tier.py"
DEFAULTS = "plugins/quality-kit/assets/qlty-coverage-tiers.yml"
PINS = "plugins/quality-kit/assets/qlty-coverage-tier-requirements.txt"
OVERRIDE = ".github/coverage-tiers.yml"

# The stub answers `gh api --method GET repos/<repo>/contents/<path> ...` from BASE_FILES (a JSON
# object of path -> content); a path that is missing gets an HTTP 404, and STUB_FAIL makes every
# call fail another way.
GH_STUB = """#!/usr/bin/env python3
import base64, json, os, sys
args = sys.argv[1:]
if os.environ.get("STUB_FAIL"):
    print("HTTP 500: server error", file=sys.stderr)
    sys.exit(1)
path = next(a for a in args if a.startswith("repos/")).split("/contents/", 1)[1]
files = json.loads(os.environ["BASE_FILES"])
if path not in files:
    print("gh: Not Found (HTTP 404)", file=sys.stderr)
    sys.exit(1)
print(base64.b64encode(files[path].encode()).decode())
"""


def _restore_script() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").split("\n")
    start = next(i for i, line in enumerate(lines) if line.strip() == STEP_ID)
    run = next(i for i in range(start, start + 10) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    width = min(len(line) - len(line.lstrip()) for line in body if line.strip())
    return "\n".join(line[width:] for line in body)


def _run(tmp_path: Path, base: dict[str, str], *, fail: bool = False):
    workspace, runner_temp, bin_dir = (tmp_path / n for n in ("ws", "rt", "bin"))
    for directory in (workspace, runner_temp, bin_dir):
        directory.mkdir()
    for path in (TIER, DEFAULTS, PINS, OVERRIDE):
        (workspace / path).parent.mkdir(parents=True, exist_ok=True)
        (workspace / path).write_text(f"pr copy of {path}\n", encoding="utf-8")
    stub = bin_dir / "gh"
    stub.write_text(GH_STUB, encoding="utf-8")
    stub.chmod(0o755)
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_OUTPUT": str(output),
        "REPO": "o/r",
        "BASE_SHA": "0" * 40,
        "BASE_FILES": json.dumps(base),
        "STUB_FAIL": "1" if fail else "",
    }
    done = subprocess.run(
        ["bash", "-c", _restore_script()],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    trusted = runner_temp / "trusted"

    def read(name: str) -> str | None:
        path = trusted / name
        return path.read_text(encoding="utf-8") if path.exists() else None

    return done, read, output.read_text(encoding="utf-8")


def base_copy(path: str) -> str:
    return f"base copy of {path}\n"


def test_base_with_every_file_is_used_and_the_pr_copy_never(tmp_path):
    base = {p: base_copy(p) for p in (TIER, DEFAULTS, PINS, OVERRIDE)}
    done, read, output = _run(tmp_path, base)
    assert done.returncode == 0, done.stderr
    assert read("tier.py") == base_copy(TIER)
    assert read("defaults.yml") == base_copy(DEFAULTS)
    assert read("requirements.txt") == base_copy(PINS)
    assert read("override.yml") == base_copy(OVERRIDE)
    assert "fallback=true" not in output


def test_base_without_the_pins_file_leaves_none_so_the_tier_step_keeps_unhashed_pins(tmp_path):
    base = {p: base_copy(p) for p in (TIER, DEFAULTS)}
    done, read, output = _run(tmp_path, base)
    assert done.returncode == 0, done.stderr
    assert read("tier.py") == base_copy(TIER)
    assert read("requirements.txt") is None
    assert read("override.yml") is None
    assert "fallback=true" not in output


def test_base_without_the_tier_files_falls_back_to_the_pr_copies_and_says_so(tmp_path):
    done, read, output = _run(tmp_path, {})
    assert done.returncode == 0, done.stderr
    assert read("tier.py") == f"pr copy of {TIER}\n"
    assert read("defaults.yml") == f"pr copy of {DEFAULTS}\n"
    assert read("requirements.txt") == f"pr copy of {PINS}\n"
    assert read("override.yml") is None, "the PR's own override is never used"
    assert "fallback=true" in output
    assert "PR's own copy computed the tier" in (read("notes.txt") or "")


@pytest.mark.parametrize("present", [TIER, DEFAULTS])
def test_base_with_only_one_tier_file_fails_closed(tmp_path, present):
    done, read, output = _run(tmp_path, {present: base_copy(present)})
    assert done.returncode == 1
    assert "refusing to mix in the PR's copy" in done.stdout
    assert "fallback=true" not in output


def test_a_non_404_read_failure_fails_closed(tmp_path):
    done, _, output = _run(tmp_path, {}, fail=True)
    assert done.returncode == 1
    assert "could not read" in done.stdout
    assert "fallback=true" not in output
