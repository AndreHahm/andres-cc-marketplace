"""`run-codex-review` result: an honest `status` and provenance (issue #572, item 6-7).

Before, an infrastructure failure, a failed dispatch and a real finding all
wrote `blocking: true`, so the artifact could not say whether the review had
run at all. Every payload shape now carries `status` (`findings`, `clean` or
`could_not_run`) at the top level and per reviewer, keeps `blocking`, and
records what the review ran on.
"""

import json
import subprocess
from pathlib import Path

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


def _envelope(findings, verdict, reviewer="security-reviewer", paths=(CHANGED,)) -> bytes:
    return json.dumps(
        {
            "contract_version": "1",
            "dispatch": {
                "id": "test-dispatch",
                "reviewer": reviewer,
                "backend": "codex",
                "target_paths": list(paths),
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
    for name in (*ROSTER, "correctness-reviewer"):
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


def _clean_as_dispatched(argv):
    """A clean answer naming the reviewer and the paths this call was dispatched with."""
    name = argv[argv.index("--reviewer-type") + 1]
    listed = Path(argv[argv.index("--target-paths-file") + 1]).read_text(encoding="utf-8")
    stdout = _envelope([], "pass", name, listed.splitlines())
    return subprocess.CompletedProcess(argv, returncode=0, stdout=stdout, stderr=b"")


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
        ReviewerReport(
            reviewer="dependency-reviewer", status="completed", output=good, attempts=1, seconds=7.5
        ),
    ]
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    rc, payload, base_sha = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 2
    assert payload["status"] == "could_not_run"
    assert payload["reviewer_results"] == {
        "security-reviewer": {"status": "could_not_run", "attempts": 2},
        "dependency-reviewer": {"status": "clean", "attempts": 1, "seconds": 7.5},
    }
    assert "dependency-reviewer: 7.5 s, 1 call(s)" in summary.read_text(encoding="utf-8")
    assert "security-reviewer:" not in summary.read_text(encoding="utf-8")
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


def test_an_absolute_citation_reaches_the_result_relative(monkeypatch, review_repo, tmp_path):
    """PR #865: the caps and the merge key compare relative paths."""
    from scripts.marketplace_ci.review import ReviewerReport

    envelope = json.loads(BLOCKING)
    location = envelope["findings"][0]["location"]
    envelope["findings"][0]["location"] = f"{review_repo[0]}/{location}"
    reports = [ReviewerReport(reviewer="security-reviewer", status="completed", output=envelope)]
    _, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert [f["path"] for f in payload["findings"]] == [CHANGED]


def test_the_symlink_check_is_wired_in_and_fails_closed(monkeypatch, review_repo, tmp_path):
    import scripts.marketplace_ci.review as review_module
    from scripts.marketplace_ci.review import ReviewerReport

    def broken(results, root):
        raise RuntimeError("no git")

    monkeypatch.setattr(review_module, "mark_symlinked", broken)
    reports = [
        ReviewerReport(reviewer="security-reviewer", status="completed", output=json.loads(CLEAN))
    ]
    rc, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 2 and "symlink check failed" in payload["error"]


def test_a_grant_finding_on_a_symlinked_command_blocks_the_run(monkeypatch, review_repo, tmp_path):
    """PR #865, end to end: the marked findings are the ones the gate sees, with the git root."""
    from scripts.marketplace_ci.review import ReviewerReport

    root, _ = review_repo
    link = root / "plugins/demo-kit/commands/a.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to("../hooks/hooks.json")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "link"], cwd=root, check=True)
    envelope = json.loads(BLOCKING)
    envelope["findings"][0] |= {
        "location": f"{root}/plugins/demo-kit/commands/a.md:1",
        "category": "allowed-tools-grant",
    }
    reports = [ReviewerReport(reviewer="security-reviewer", status="completed", output=envelope)]
    _, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    (finding,) = [f for f in payload["findings"] if f["rule"] == "R6"]
    assert finding["path"] == "plugins/demo-kit/commands/a.md" and finding["gate"] == "block"


def test_provenance_helpers_return_none_outside_a_repository(tmp_path):
    """`_git_out` backs `_run_provenance`, which also runs on failure paths: git failing must
    give None (a null field), never raise out of the failure writer."""
    from scripts.marketplace_ci.__main__ import _git_out, _run_provenance

    assert _git_out(tmp_path, "rev-parse", "HEAD") is None
    provenance = _run_provenance(tmp_path, "abc", [])
    assert provenance["head_sha"] is None and provenance["merge_ref_sha"] is None
    assert provenance["base_sha"] == "abc"


# --- review contract: registry, gate fields, briefing (issue #573) -----------------------------


def _registry(tmp_path, text):
    path = tmp_path / "exceptions.yaml"
    path.write_text(text, encoding="utf-8")
    return path


MATCHING_EXCEPTION = (
    "exceptions:\n"
    "  - rule: R6\n"
    f"    path: {CHANGED}\n"
    "    reason: Deliberate.\n"
    "    authority: docs/ci.md\n"
)


def test_the_shipped_registry_path_is_the_file_beside_the_contract():
    from scripts.marketplace_ci import review_contract

    assert review_contract.EXCEPTIONS_PATH.name == "review_exceptions.yaml"
    assert (
        review_contract.EXCEPTIONS_PATH.parent
        == Path(__file__).resolve().parents[2] / "scripts" / "marketplace_ci"
    )


@pytest.mark.parametrize("text", ["exceptions: nope\n", "not: [valid", None])
def test_an_unreadable_or_invalid_registry_fails_closed(monkeypatch, review_repo, tmp_path, text):
    from scripts.marketplace_ci import review_contract

    path = tmp_path / "absent.yaml" if text is None else _registry(tmp_path, text)
    monkeypatch.setattr(review_contract, "EXCEPTIONS_PATH", path)
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(CLEAN))
    assert rc == 2
    assert payload["status"] == "could_not_run"
    assert payload["blocking"] is True
    assert "exceptions registry" in payload["error"]


def test_a_blocking_finding_records_its_gate_decision_and_class(monkeypatch, review_repo, tmp_path):
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(BLOCKING))
    assert rc == 1
    (finding,) = payload["findings"]
    assert finding["gate"] == "block" and finding["suppressed"] is False
    assert finding["rule_class"] == "judgment" and finding["source"] == "model"
    assert finding["confidence"] == "high" and finding["exception"] is None
    assert payload["exceptions_loaded"] >= 3


def test_a_registry_entry_does_not_suppress_a_model_finding(monkeypatch, review_repo, tmp_path):
    from scripts.marketplace_ci import review_contract

    monkeypatch.setattr(review_contract, "EXCEPTIONS_PATH", _registry(tmp_path, MATCHING_EXCEPTION))
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(BLOCKING))
    assert rc == 1
    assert payload["findings"][0]["gate"] == "block"
    assert payload["exceptions_loaded"] == 1


def test_every_reviewer_is_briefed_with_the_registry(monkeypatch, review_repo, tmp_path):
    from scripts.marketplace_ci import review_contract

    monkeypatch.setattr(review_contract, "EXCEPTIONS_PATH", _registry(tmp_path, MATCHING_EXCEPTION))
    briefed = []

    def bridge(argv):
        text = open(argv[argv.index("--instruction-file") + 1], encoding="utf-8").read()
        briefed.append("[documented exceptions]" in text and '"rule": "R6"' in text)
        return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")

    rc, _ = _run(monkeypatch, review_repo, tmp_path, bridge)
    assert rc == 0
    assert briefed == [True] * len(ROSTER)


def _commit_on(root, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "more"], cwd=root, check=True)


def test_a_plugin_hook_change_is_code_but_not_advisory(monkeypatch, review_repo, tmp_path):
    # CHANGED is a plugin hooks.json: code no roster reviewer checks for logic (issue #713, M2).
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(CLEAN))
    assert rc == 0
    assert payload["coverage"] == {
        "general_correctness_reviewers": [],
        "uncovered_paths": [CHANGED],
        "complete": False,
    }
    assert payload["advisory"] == {"advisory": False, "reasons": [], "paths": []}


def test_an_added_import_shadow_makes_the_result_advisory(monkeypatch, review_repo, tmp_path):
    root, _ = review_repo
    _commit_on(root, {"json.py": "x = 1\n"})  # a top-level stdlib shadow
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(CLEAN))
    assert rc == 0
    assert payload["advisory"]["reasons"] == ["import-shadow"]
    assert payload["advisory"]["paths"] == ["json.py"]


def test_a_coverage_failure_is_could_not_run(monkeypatch, review_repo, tmp_path):
    from scripts.marketplace_ci import review

    def boom(*_args, **_kwargs):
        raise RuntimeError("broken")

    monkeypatch.setattr(review, "review_advisory", boom)
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(CLEAN))
    assert rc == 2
    assert payload["status"] == "could_not_run"
    assert "coverage/advisory failed" in payload["error"]


def test_a_clean_review_says_which_code_was_not_checked_for_correctness(
    monkeypatch, review_repo, tmp_path
):
    """Issue #713: correctness-reviewer covers CI and script changes, but not a plugin hook."""
    root, _ = review_repo
    _commit_on(root, {".github/workflows/ci.yml": "on: push\n", "scripts/tool.py": "x = 1\n"})
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _clean_as_dispatched)
    # Fields only: the gate, the status and the exit code are unchanged.
    assert rc == 0 and payload["status"] == "clean" and payload["blocking"] is False
    assert payload["reviewer_results"]["correctness-reviewer"]["status"] == "clean"
    assert payload["coverage"] == {
        "general_correctness_reviewers": ["correctness-reviewer"],
        "uncovered_paths": [CHANGED],
        "complete": False,
    }


MINOR = {
    "id": "m1",
    "severity": "minor",
    "axis": "claims",
    "location": "scripts/tool.py",
    "evidence": "e",
    "finding": "f",
    "fix": "m",
    "confidence": "high",
}


@pytest.mark.parametrize("verdict", ["Inconclusive: one file unread", "unable to read it all"])
def test_an_inconclusive_correctness_review_with_findings_covers_nothing(
    monkeypatch, review_repo, tmp_path, verdict
):
    # The gate keeps such a review (findings were raised); coverage must not count its paths.
    from scripts.marketplace_ci.review import ReviewerReport

    root, _ = review_repo
    _commit_on(root, {"scripts/tool.py": "x = 1\n"})
    output = json.loads(_envelope([MINOR], verdict))
    reports = [
        ReviewerReport(
            reviewer="correctness-reviewer", status="completed", output=output, attempts=1
        )
    ]
    rc, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 0 and payload["blocking"] is False
    assert payload["coverage"] == {
        "general_correctness_reviewers": [],
        "uncovered_paths": [CHANGED, "scripts/tool.py"],
        "complete": False,
    }


def test_advisory_keeps_a_mirror_the_reviewer_dispatch_collapses(
    monkeypatch, review_repo, tmp_path
):
    # PR #820 review: dispatch reviews an identical .claude/ mirror once, under its canonical
    # path, but advisory is over the whole PR delta, so the mirror must still be listed.
    from scripts.marketplace_ci import review
    from scripts.marketplace_ci.review import ReviewerReport

    root, _ = review_repo
    mirror = ".claude/agents/security-reviewer.md"
    (root / ".claude/agents").mkdir(parents=True, exist_ok=True)
    (root / mirror).write_text("x\n", encoding="utf-8")
    # -f: a global gitignore may exclude .claude/, which CI's runner does not.
    subprocess.run(["git", "add", "-f", mirror], cwd=root, check=True)
    _commit_on(root, {"plugins/plugin-devkit/agents/security-reviewer.md": "x\n"})
    real_collapse = review.collapse_identical_mirrors
    monkeypatch.setattr(
        review,
        "collapse_identical_mirrors",
        lambda repo, changed, base: tuple(
            c for c in real_collapse(repo, changed, base) if c.new_path != mirror
        ),
    )
    reports = [
        ReviewerReport(
            reviewer="security-reviewer", status="completed", output=json.loads(CLEAN), attempts=1
        )
    ]
    rc, payload, _ = _run_with_reports(monkeypatch, review_repo, tmp_path, reports)
    assert rc == 0
    assert mirror in payload["advisory"]["paths"]
    assert mirror not in payload["reviewed_paths"]


def test_a_change_to_a_reviewer_definition_makes_the_result_advisory(
    monkeypatch, review_repo, tmp_path
):
    root, _ = review_repo
    _commit_on(root, {".codex/agents/security-reviewer.toml": 'developer_instructions = "x"\n'})
    rc, payload = _run(monkeypatch, review_repo, tmp_path, _answers(CLEAN))
    assert rc == 0 and payload["status"] == "clean"
    assert payload["advisory"] == {
        "advisory": True,
        "reasons": ["reviewer-steering"],
        "paths": [".codex/agents/security-reviewer.toml"],
    }


def test_the_result_records_the_waivers_its_reviewers_were_briefed_with(
    monkeypatch, review_repo, tmp_path
):
    """R19: a reviewer may leave a briefed finding out, so the result names the briefed lines
    for the publish step to re-check. A waiver whose line is gone at HEAD is not briefed."""
    from scripts.marketplace_ci.review import line_fingerprint

    root, base_sha = review_repo
    briefed = f"- R6 README.md:1 @{line_fingerprint('original')} – accepted"
    gone = f"- R6 README.md:2 @{line_fingerprint('no such line')} – accepted"
    accepted = tmp_path / "accepted.json"
    accepted.write_text(
        json.dumps(
            {
                "body": f"## Accepted Review Findings\n{briefed}\n{gone}\n",
                "open_issues": [],
                "confirmed": [],
            }
        ),
        encoding="utf-8",
    )
    real_run = subprocess.run
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda argv, **kw: _answers(CLEAN)(argv) if argv[0] == "node" else real_run(argv, **kw),
    )
    monkeypatch.chdir(root)
    out = tmp_path / "result.json"
    args = ["run-codex-review", "--base-sha", base_sha, "--output", str(out)]
    assert main([*args, "--accepted-findings", str(accepted)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["briefed_waivers"] == [briefed]
