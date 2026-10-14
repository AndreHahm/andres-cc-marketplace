"""`run-codex-review` result: an honest `status` and provenance (issue #572, item 6-7).

Before, an infrastructure failure, a failed dispatch and a real finding all
wrote `blocking: true`, so the artifact could not say whether the review had
run at all. Every payload shape now carries `status` (`findings`, `clean` or
`could_not_run`) at the top level and per reviewer, keeps `blocking`, and
records what the review ran on.
"""

import json
import subprocess

import pytest

from scripts.marketplace_ci.__main__ import main

STATUSES = {"findings", "clean", "could_not_run"}
ROSTER = ("plugin-rulebook-checker", "dependency-reviewer", "security-reviewer")
CHANGED = "plugins/demo-kit/hooks/hooks.json"
PROVENANCE_KEYS = {
    "head_sha",
    "merge_ref_sha",
    "base_sha",
    "model",
    "cli_version",
}


def _envelope(findings, verdict) -> bytes:
    return json.dumps(
        {
            "contract_version": "1",
            "dispatch": {
                "id": "test-dispatch",
                "reviewer": "security-reviewer",
                "backend": "codex",
                "target_paths": [CHANGED],
            },
            "provenance": {
                "provider": "openai",
                "model": "test-model",
                "cli_version": "9.9.9",
                "execution_profile": "read-only",
            },
            "findings": findings,
            "verdict": verdict,
            "inspection_limits": [],
        }
    ).encode()


CLEAN = _envelope([], "pass")
BLOCKING = _envelope(
    [
        {
            "id": "C1",
            "severity": "critical",
            "axis": "R6",
            "location": CHANGED,
            "evidence": "e",
            "finding": "f",
            "fix": "m",
            "confidence": "high",
        }
    ],
    "reject",
)


@pytest.fixture
def review_repo(git_repo):
    """A repo with a base commit and one changed file; returns (root, base_sha)."""
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    git_repo.write("README.md", "original")
    subprocess.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()
    git_repo.write(CHANGED, "{}")
    subprocess.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "change"], cwd=git_repo.root, check=True)
    return git_repo.root, base_sha


def _run(monkeypatch, review_repo, tmp_path, bridge):
    """Run the command with `bridge` standing in for the Codex bridge; return (rc, payload)."""
    root, base_sha = review_repo
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return bridge(argv)
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base_sha, "--output", str(out)])
    return rc, json.loads(out.read_text(encoding="utf-8"))


def _answers(stdout: bytes):
    return lambda argv: subprocess.CompletedProcess(argv, returncode=0, stdout=stdout, stderr=b"")


def _bridge_fails(argv):
    return subprocess.CompletedProcess(argv, returncode=1, stdout=b"", stderr=b"bridge exploded")


def test_a_clean_review_reports_status_clean(monkeypatch, review_repo, tmp_path):
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(CLEAN))
    assert rc == 0
    assert payload["status"] == "clean"
    assert payload["blocking"] is False
    assert {r["status"] for r in payload["reviewer_results"].values()} == {"clean"}


def test_a_blocking_finding_reports_status_findings(monkeypatch, review_repo, tmp_path):
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(BLOCKING))
    assert rc == 1
    assert payload["status"] == "findings"
    assert payload["blocking"] is True
    assert {r["status"] for r in payload["reviewer_results"].values()} == {"findings"}


def test_a_failed_dispatch_reports_could_not_run(monkeypatch, review_repo, tmp_path):
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _bridge_fails)
    assert rc == 2
    assert payload["status"] == "could_not_run"
    assert payload["blocking"] is True
    assert {r["status"] for r in payload["reviewer_results"].values()} == {"could_not_run"}
    assert all(r["attempts"] >= 1 for r in payload["reviewer_results"].values())
    assert payload["dispatch_failed"]  # the existing field stays


def test_one_failed_reviewer_makes_the_whole_run_could_not_run(monkeypatch, review_repo, tmp_path):
    """A review that skipped a reviewer is not a clean review of the rest."""
    calls = []

    def one_fails(argv):
        calls.append(argv)
        if len(calls) == 1:
            return _bridge_fails(argv)
        return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")

    rc, payload = _run(monkeypatch, review_repo, tmp_path, one_fails)
    assert rc == 2
    assert payload["status"] == "could_not_run"
    statuses = {r["status"] for r in payload["reviewer_results"].values()}
    assert statuses == {"could_not_run", "clean"}


def test_an_infrastructure_failure_reports_could_not_run(monkeypatch, git_repo, tmp_path):
    monkeypatch.chdir(git_repo.root)
    out = tmp_path / "result.json"
    assert main(["run-codex-review", "--base-sha", "0" * 40, "--output", str(out)]) == 2
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "could_not_run"
    assert payload["blocking"] is True
    assert "cannot resolve base SHA" in payload["error"]
    # Every shape run-codex-review writes itself carries the same keys, empty where nothing ran.
    assert payload["reviewer_results"] == {}
    assert PROVENANCE_KEYS <= set(payload["provenance"])


@pytest.mark.parametrize("bridge_key", ["clean", "blocking"])
def test_a_completed_review_records_what_it_ran_on(monkeypatch, review_repo, tmp_path, bridge_key):
    root, base_sha = review_repo
    stdout = CLEAN if bridge_key == "clean" else BLOCKING
    _, payload = _run(monkeypatch, review_repo, tmp_path, _answers(stdout))
    provenance = payload["provenance"]
    assert PROVENANCE_KEYS <= set(provenance)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert provenance["base_sha"] == base_sha
    assert provenance["merge_ref_sha"] == head
    assert provenance["model"] == "test-model"
    assert provenance["cli_version"] == "9.9.9"
    assert payload["reviewers"] == list(payload["reviewer_results"])


def test_head_sha_is_the_pr_head_when_the_checkout_is_a_merge(monkeypatch, review_repo, tmp_path):
    """On the merge ref, `head_sha` names the PR's own head (second parent), not the merge."""
    root, base_sha = review_repo
    pr_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-q", "-b", "side", base_sha], cwd=root, check=True)
    (root / "other.md").write_text("upstream", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "upstream"], cwd=root, check=True)
    subprocess.run(
        ["git", "merge", "-q", "--no-ff", "-m", "merge ref", pr_head], cwd=root, check=True
    )
    _, payload = _run(monkeypatch, (root, base_sha), tmp_path, _answers(CLEAN))
    assert payload["provenance"]["head_sha"] == pr_head
    assert payload["provenance"]["merge_ref_sha"] != pr_head


def test_every_failure_shape_has_a_known_status(monkeypatch, review_repo, tmp_path):
    for bridge in (_answers(CLEAN), _answers(BLOCKING), _bridge_fails):
        _, payload = _run(monkeypatch, review_repo, tmp_path, bridge)
        assert payload["status"] in STATUSES


def _run_with_reports(monkeypatch, review_repo, tmp_path, reports):
    """Run the command with `dispatch_reviewers` returning `reports`; return (rc, payload)."""
    import scripts.marketplace_ci.review as review_module

    root, base_sha = review_repo
    monkeypatch.setattr(review_module, "dispatch_reviewers", lambda *a, **kw: reports)
    monkeypatch.chdir(root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base_sha, "--output", str(out)])
    return rc, json.loads(out.read_text(encoding="utf-8")), base_sha


def test_a_failure_after_dispatch_keeps_the_reviewers_that_ran(monkeypatch, review_repo, tmp_path):
    """No output from one reviewer: the artifact still says who ran, how often, and on what."""
    from scripts.marketplace_ci.review import ReviewerReport

    good = json.loads(CLEAN)
    reports = [
        ReviewerReport(reviewer="security-reviewer", status="completed", output=None, attempts=2),
        ReviewerReport(reviewer="dependency-reviewer", status="completed", output=good, attempts=1),
    ]
    rc, payload, base_sha = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 2
    assert payload["status"] == "could_not_run"
    assert payload["reviewer_results"] == {
        "security-reviewer": {"status": "could_not_run", "attempts": 2},
        "dependency-reviewer": {"status": "clean", "attempts": 1},
    }
    assert payload["provenance"]["base_sha"] == base_sha
    assert payload["provenance"]["model"] == "test-model"  # reported by the reviewer that answered


def test_an_invalid_envelope_marks_that_reviewer_could_not_run(monkeypatch, review_repo, tmp_path):
    from scripts.marketplace_ci.review import ReviewerReport

    reports = [
        ReviewerReport(
            reviewer="security-reviewer", status="completed", output={"x": 1}, attempts=1
        ),
        ReviewerReport(
            reviewer="dependency-reviewer", status="completed", output=json.loads(CLEAN), attempts=1
        ),
    ]
    rc, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 2
    assert "returned invalid output" in payload["error"]
    assert payload["reviewer_results"]["security-reviewer"]["status"] == "could_not_run"
    assert payload["reviewer_results"]["dependency-reviewer"]["status"] == "clean"


def test_every_malformed_envelope_is_marked_could_not_run_not_just_the_first(
    monkeypatch, review_repo, tmp_path
):
    """A malformed envelope can still carry a list-valued `findings`; none of them may read as
    a completed review just because validation stopped at the first bad one."""
    from scripts.marketplace_ci.review import ReviewerReport

    reports = [
        ReviewerReport(reviewer="security-reviewer", status="completed", output={"findings": []}),
        ReviewerReport(
            reviewer="dependency-reviewer", status="completed", output={"findings": [{"x": 1}]}
        ),
        ReviewerReport(
            reviewer="plugin-rulebook-checker", status="completed", output=json.loads(CLEAN)
        ),
    ]
    rc, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 2
    assert payload["status"] == "could_not_run"
    results = {name: r["status"] for name, r in payload["reviewer_results"].items()}
    assert results == {
        "security-reviewer": "could_not_run",
        "dependency-reviewer": "could_not_run",
        "plugin-rulebook-checker": "clean",  # a valid envelope stays what it is
    }
    # The error still names the first failure, and says there were more.
    assert "security-reviewer" in payload["error"]
    assert "dependency-reviewer" in payload["error"]


def test_a_missing_output_and_a_malformed_one_are_both_marked(monkeypatch, review_repo, tmp_path):
    from scripts.marketplace_ci.review import ReviewerReport

    reports = [
        ReviewerReport(reviewer="security-reviewer", status="completed", output=None),
        ReviewerReport(reviewer="dependency-reviewer", status="completed", output={"findings": []}),
    ]
    rc, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 2
    assert {r["status"] for r in payload["reviewer_results"].values()} == {"could_not_run"}
