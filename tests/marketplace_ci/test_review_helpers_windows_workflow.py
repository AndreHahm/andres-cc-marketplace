"""Wiring of the informational `review-helpers-windows` job in marketplace-ci.yml (issue #714).

The job tests review-helper scripts, not dependencies, so a Dependabot PR skips it with the same two
checks the `codex-review` job uses. It must stay out of every job's `needs`, so the skip can never
turn into a required check that reports skipped or blocks a merge.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
JOBS = yaml.safe_load((ROOT / ".github/workflows/marketplace-ci.yml").read_text("utf-8"))["jobs"]
JOB = "review-helpers-windows"


def test_dependabot_prs_skip_the_job():
    cond = JOBS[JOB]["if"]
    assert "github.actor != 'dependabot[bot]'" in cond
    assert "github.event.pull_request.user.login != 'dependabot[bot]'" in cond
    assert "&&" in cond and "||" not in cond


def test_the_job_stays_out_of_every_needs_list():
    for name, spec in JOBS.items():
        needs = spec.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        assert JOB not in needs, name
