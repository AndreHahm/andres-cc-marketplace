"""How marketplace-ci.yml installs uv (issue #641).

Every job that runs uv installs it once with the SHA-pinned astral-sh/setup-uv action, at a fixed uv
version, before its first uv command, never with an unpinned `pip install uv`. The version is set
explicitly so the action never falls back to PR-controlled config (`pyproject.toml`) or to `latest`,
and the cache stays off: several of these jobs restore trusted code or hold secrets, and a cache
written from a PR run would carry state into later runs.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
JOBS = yaml.safe_load((ROOT / ".github/workflows/marketplace-ci.yml").read_text("utf-8"))["jobs"]
SETUP_UV = "astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2"
UV_VERSION = "0.12.21"


def _uses_uv(step: dict) -> bool:
    return any(line.lstrip().startswith("uv ") for line in str(step.get("run", "")).splitlines())


def _uv_jobs() -> dict[str, list[dict]]:
    return {
        name: spec["steps"]
        for name, spec in JOBS.items()
        if any(_uses_uv(step) for step in spec.get("steps", []))
    }


def test_no_job_installs_uv_with_pip():
    for name, spec in JOBS.items():
        for step in spec.get("steps", []):
            assert "pip install" not in str(step.get("run", "")), name


def test_every_uv_job_sets_up_one_pinned_uv_before_its_first_uv_command():
    jobs = _uv_jobs()
    assert len(jobs) >= 8  # the seven jobs migrated in #641, plus review-helpers-windows
    for name, steps in jobs.items():
        setups = [i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith(SETUP_UV)]
        assert len(setups) == 1, name
        first_uv = next(i for i, s in enumerate(steps) if _uses_uv(s))
        assert setups[0] < first_uv, name
        options = steps[setups[0]]["with"]
        assert options == {"version": UV_VERSION, "enable-cache": "false"}, name
