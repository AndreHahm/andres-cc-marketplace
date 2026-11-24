"""The two-arm prompt comparison (issue #862). No test makes a model call: dispatch is replaced."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci import review
from scripts.reviewer_eval import ab, score

REVIEWERS = ("plugin-rulebook-checker", "dependency-reviewer", "security-reviewer")
SKILL = "plugins/demo/skills/one/SKILL.md"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _prompts(text: str) -> dict[str, str]:
    names = {*REVIEWERS, *review.DELTA_VALIDATE, "skill-reviewer"}
    return {f".codex/agents/{n}.toml": f'developer_instructions = "{text} {n}"\n' for n in names}


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """A repository with a base, a head that edits a skill, and two commits used as arms."""
    repo = tmp_path / "head"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    for key, value in {"user.name": "t", "user.email": "t@example.invalid"}.items():
        _git(repo, "config", key, value)
    _git(repo, "config", "commit.gpgsign", "false")
    body = "---\nname: one\ndescription: d\n---\n"
    base = _commit(repo, {SKILL: body + "old\n", **_prompts("base")}, "base")
    old = _commit(repo, _prompts("old"), "old arm")
    new = _commit(repo, _prompts("new"), "new arm")
    _git(repo, "checkout", "-q", "--detach", base)
    head = _commit(repo, {SKILL: body + "new\n"}, "head")
    monkeypatch.setenv("CODEX_KIT_REVIEW_MODEL", "gpt-test")
    return {"repo": repo, "base": base, "old": old, "new": new, "head": head, "tmp": tmp_path}


def _plan(lab, **overrides):
    kwargs = {
        "repo": lab["repo"],
        "head_sha": lab["head"],
        "base_sha": lab["base"],
        "arms": {"old": lab["old"], "new": lab["new"]},
        "repeats": 2,
        **overrides,
    }
    return ab.make_plan(**kwargs)


def _envelope(reviewer: str, severity: str | None, line: int = 5) -> dict:
    findings = []
    if severity:
        findings.append(
            {
                "id": "f1",
                "severity": severity,
                "axis": "injection-surface",
                "location": f"{SKILL}:{line}",
                "evidence": "e",
                "finding": "t",
                "fix": "r",
                "confidence": "high",
            }
        )
    return {
        "contract_version": "1",
        "dispatch": {"id": "d", "reviewer": reviewer, "backend": "codex", "target_paths": [SKILL]},
        "provenance": {"model": "m", "cli_version": "c"},
        "findings": findings,
        "verdict": "ok",
        "inspection_limits": [],
    }


def _fake_dispatch(calls: list, outcome):
    """Replaces dispatch_reviewers; `outcome(sha, reviewer)` is a severity, None or "FAIL"."""

    def dispatch(scope, *, base_sha, repo, **kwargs):
        calls.append({"sha": base_sha, "repo": repo, "bridge": review.BRIDGE_INVOKE_RELATIVE_PATH})
        calls[-1].update(kwargs)
        reports = []
        for name in dict.fromkeys((*scope.validate, *scope.audit)):
            result = outcome(base_sha, name)
            if result == "FAIL":
                reports.append(review.ReviewerReport(name, "failed", error="boom"))
            else:
                reports.append(
                    review.ReviewerReport(name, "completed", output=_envelope(name, result))
                )
        return tuple(reports)

    return dispatch


# --- plan ---------------------------------------------------------------------------------------


def test_plan_counts_one_call_per_reviewer_arm_and_repeat(lab):
    plan = _plan(lab)
    assert plan.calls == len(plan.reviewers) * 2 * 2
    assert set(REVIEWERS) <= set(plan.reviewers)
    assert plan.scope.paths == (SKILL,)


def test_plan_records_a_different_prompt_digest_per_arm(lab):
    plan = _plan(lab)
    for digests in plan.prompts.values():
        assert digests["old"] != digests["new"]
    assert plan.identical_prompts == ()


def test_plan_names_reviewers_whose_prompt_is_the_same_in_both_arms(lab):
    plan = _plan(lab, arms={"old": lab["old"], "new": lab["old"]})
    assert plan.identical_prompts == plan.reviewers


@pytest.mark.parametrize("field", ["head_sha", "base_sha"])
@pytest.mark.parametrize("value", ["main", "abc123", "A" * 40, "--help"])
def test_plan_refuses_anything_but_a_full_sha(lab, field, value):
    with pytest.raises(ab.AbError, match="40 lowercase hex"):
        _plan(lab, **{field: value})


def test_plan_refuses_an_arm_that_is_not_a_full_sha(lab):
    with pytest.raises(ab.AbError, match="40 lowercase hex"):
        _plan(lab, arms={"old": lab["old"], "new": "main"})


@pytest.mark.parametrize("names", [("a/b", "new"), ("..", "new"), ("", "new")])
def test_plan_refuses_an_arm_name_that_is_not_a_plain_word(lab, names):
    with pytest.raises(ab.AbError, match="arm name"):
        _plan(lab, arms=dict.fromkeys(names, lab["old"]))


def test_plan_needs_exactly_two_arms(lab):
    with pytest.raises(ab.AbError, match="two arms"):
        _plan(lab, arms={"old": lab["old"]})


@pytest.mark.parametrize("repeats", [0, -1, ab.MAX_REPEATS + 1])
def test_plan_refuses_repeats_out_of_range(lab, repeats):
    with pytest.raises(ab.AbError, match="repeats"):
        _plan(lab, repeats=repeats)


def test_plan_refuses_a_checkout_that_is_not_the_head(lab):
    with pytest.raises(ab.AbError, match="checked out"):
        _plan(lab, head_sha=lab["base"])


def test_plan_refuses_a_dirty_checkout(lab):
    (lab["repo"] / SKILL).write_text("edited\n", encoding="utf-8")
    with pytest.raises(ab.AbError, match="not clean"):
        _plan(lab)


def test_plan_refuses_a_base_that_is_not_an_ancestor_of_the_head(lab):
    with pytest.raises(ab.AbError, match="ancestor"):
        _plan(lab, base_sha=lab["old"])


def test_plan_refuses_an_arm_without_a_reviewers_prompt(lab):
    with pytest.raises(ab.AbError, match="prompt"):
        _git(lab["repo"], "checkout", "-q", "--detach", lab["base"])
        _git(lab["repo"], "rm", "-q", "-r", ".codex")
        _git(lab["repo"], "commit", "-q", "-m", "no prompts")
        bare = _git(lab["repo"], "rev-parse", "HEAD")
        _git(lab["repo"], "checkout", "-q", "--detach", lab["head"])
        _plan(lab, arms={"old": lab["old"], "new": bare})


def test_plan_refuses_a_head_that_starts_no_reviewer(lab):
    _git(lab["repo"], "checkout", "-q", "--detach", lab["base"])
    head = _commit(lab["repo"], {"notes.txt": "x\n"}, "no reviewer")
    with pytest.raises(ab.AbError, match="no reviewer"):
        _plan(lab, head_sha=head)


def test_plan_refuses_without_the_model_pin(lab, monkeypatch):
    """`score --stability` refuses a run that records no configured model."""
    monkeypatch.delenv("CODEX_KIT_REVIEW_MODEL")
    with pytest.raises(ab.AbError, match="CODEX_KIT_REVIEW_MODEL"):
        _plan(lab)


# --- run ----------------------------------------------------------------------------------------


def test_run_alternates_the_arms_within_each_repeat(lab, monkeypatch):
    calls: list = []
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch(calls, lambda *_: None))
    ab.run_experiment(_plan(lab), lab["tmp"] / "out")
    assert [c["sha"] for c in calls] == [lab["old"], lab["new"], lab["old"], lab["new"]]


def test_run_uses_this_checkouts_bridge_on_the_head_and_restores_it(lab, monkeypatch):
    """The head's own bridge is never run: it can be older, and it is the reviewed code."""
    calls: list = []
    before = review.BRIDGE_INVOKE_RELATIVE_PATH
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch(calls, lambda *_: None))
    ab.run_experiment(_plan(lab), lab["tmp"] / "out")
    root = Path(ab.__file__).resolve().parents[2]
    for call in calls:
        assert call["repo"] == lab["repo"]
        # `repo / absolute` is the absolute path, which is how dispatch_reviewers resolves it.
        assert call["repo"] / call["bridge"] == root / before
        assert (call["repo"] / call["bridge"]).is_file()
    assert before == review.BRIDGE_INVOKE_RELATIVE_PATH


def test_the_real_dispatcher_launches_the_overridden_bridge(lab, monkeypatch):
    """Pins that dispatch_reviewers builds the bridge path from the constant the runner sets."""
    launched: list = []

    def fake_bridge(argv, **_):
        launched.append(argv)
        out = json.dumps(_envelope(argv[argv.index("--reviewer-type") + 1], None)).encode()
        return subprocess.CompletedProcess(argv, 0, out, b"")

    monkeypatch.setattr(review, "_run_bridge", fake_bridge)
    monkeypatch.setattr(review, "_executable_outside_checkout", lambda name: name)
    plan = _plan(lab, repeats=1)
    ab.run_experiment(plan, lab["tmp"] / "out")
    bridge = Path(ab.__file__).resolve().parents[2] / review.BRIDGE_INVOKE_RELATIVE_PATH
    assert len(launched) == plan.calls
    assert {argv[1] for argv in launched} == {str(bridge)}


def test_run_never_retries_so_the_planned_calls_are_a_ceiling(lab, monkeypatch):
    calls: list = []
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch(calls, lambda *_: None))
    ab.run_experiment(_plan(lab), lab["tmp"] / "out")
    for call in calls:
        assert call["max_timeout_retries"] == 0
        assert call["max_empty_retries"] == 0
        assert not call.get("allow_guardrails_fallback")


def test_run_writes_results_the_stability_scorer_accepts(lab, monkeypatch, capsys):
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], lambda *_: "major"))
    out = lab["tmp"] / "out"
    assert ab.run_experiment(_plan(lab), out) == 0
    runs = [str(out / "old" / f"run{n}.json") for n in (1, 2)]
    assert score.main(["--stability", *runs, "--reviewer", "security-reviewer"]) == 0
    assert json.loads(capsys.readouterr().out)["agree"] == 2


def test_run_records_the_arm_and_the_gates_own_verdict(lab, monkeypatch):
    def outcome(sha, _):
        return "major" if sha == lab["old"] else "minor"

    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], outcome))
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=1), out)
    old = json.loads((out / "old" / "run1.json").read_text(encoding="utf-8"))
    new = json.loads((out / "new" / "run1.json").read_text(encoding="utf-8"))
    assert (old["arm"], old["arm_sha"]) == ("old", lab["old"])
    assert old["provenance"]["base_sha"] == lab["base"]
    assert old["provenance"]["head_sha"] == lab["head"]
    model_old = [f for f in old["findings"] if f["source"] == "model"]
    model_new = [f for f in new["findings"] if f["source"] == "model"]
    assert model_old and all(f["blocking"] for f in model_old)
    assert model_new and not any(f["blocking"] for f in model_new)


def test_a_finding_off_the_changed_lines_does_not_block(lab, monkeypatch):
    def dispatch(scope, *, base_sha, repo, **_):
        return tuple(
            review.ReviewerReport(n, "completed", output=_envelope(n, "major", line=2))
            for n in (*scope.validate, *scope.audit)
        )

    monkeypatch.setattr(review, "dispatch_reviewers", dispatch)
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=1), out)
    result = json.loads((out / "old" / "run1.json").read_text(encoding="utf-8"))
    assert not any(f["blocking"] for f in result["findings"] if f["source"] == "model")


def test_a_failed_reviewer_is_recorded_and_the_other_reviewers_are_kept(lab, monkeypatch):
    def outcome(sha, name):
        return "FAIL" if name == "security-reviewer" and sha == lab["new"] else "major"

    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], outcome))
    out = lab["tmp"] / "out"
    assert ab.run_experiment(_plan(lab, repeats=1), out) == 1
    result = json.loads((out / "new" / "run1.json").read_text(encoding="utf-8"))
    assert result["failed_reviewers"] == {"security-reviewer": "boom"}
    assert "security-reviewer" not in result["reviewers"]
    assert result["findings"]


def test_an_invalid_envelope_counts_as_a_failed_reviewer(lab, monkeypatch):
    def dispatch(scope, *, base_sha, repo, **_):
        reports = []
        for n in (*scope.validate, *scope.audit):
            output = _envelope(n, None)
            if n == "security-reviewer":
                del output["verdict"]
            reports.append(review.ReviewerReport(n, "completed", output=output))
        return tuple(reports)

    monkeypatch.setattr(review, "dispatch_reviewers", dispatch)
    out = lab["tmp"] / "out"
    assert ab.run_experiment(_plan(lab, repeats=1), out) == 1
    result = json.loads((out / "old" / "run1.json").read_text(encoding="utf-8"))
    assert list(result["failed_reviewers"]) == ["security-reviewer"]


def test_run_stops_when_every_reviewer_of_a_run_failed(lab, monkeypatch):
    """A bad key or a down sandbox fails every call; the rest would only spend more."""
    calls: list = []
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch(calls, lambda *_: "FAIL"))
    assert ab.run_experiment(_plan(lab), lab["tmp"] / "out") == 1
    assert len(calls) == 1


def test_run_refuses_an_output_directory_that_already_exists(lab, monkeypatch):
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], lambda *_: None))
    out = lab["tmp"] / "out"
    out.mkdir()
    with pytest.raises(ab.AbError, match="exists"):
        ab.run_experiment(_plan(lab), out)


def test_run_refuses_an_output_directory_inside_the_reviewed_checkout(lab):
    """Results written there would be files the next run's reviewers can read."""
    with pytest.raises(ab.AbError, match="inside"):
        ab.run_experiment(_plan(lab), lab["repo"] / "out")


def test_run_writes_a_manifest_with_the_inputs(lab, monkeypatch):
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], lambda *_: None))
    out = lab["tmp"] / "out"
    plan = _plan(lab)
    ab.run_experiment(plan, out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["arms"] == {"old": lab["old"], "new": lab["new"]}
    assert manifest["head_sha"] == lab["head"]
    assert manifest["base_sha"] == lab["base"]
    assert manifest["planned_calls"] == plan.calls
    assert manifest["prompts"] == plan.prompts
    assert manifest["configured_model"] == "gpt-test"


# --- report -------------------------------------------------------------------------------------


def _report(lab, monkeypatch, outcome, *, repeats=3, cases=()):
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], outcome))
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=repeats), out)
    return ab.build_report(out, list(cases))


def test_report_gives_the_spread_of_blocking_counts_per_arm(lab, monkeypatch):
    seen = {"old": 0}

    def outcome(sha, name):
        if name != "security-reviewer":
            return None
        if sha == lab["old"]:
            seen["old"] += 1
            return "major" if seen["old"] != 2 else None
        return "minor"

    report = _report(lab, monkeypatch, outcome)
    arms = report["reviewers"]["security-reviewer"]
    assert arms["old"]["blocking_per_run"] == [1, 0, 1]
    assert (arms["old"]["min"], arms["old"]["median"], arms["old"]["max"]) == (0, 1, 1)
    assert arms["old"]["agree"] == 2
    assert arms["new"]["blocking_per_run"] == [0, 0, 0]
    (finding,) = arms["old"]["findings"]
    assert (finding["reported"], finding["blocking"], finding["runs"]) == (2, 2, 3)


def test_report_gives_no_stability_verdict_below_five_runs(lab, monkeypatch):
    report = _report(lab, monkeypatch, lambda *_: "major")
    for arms in report["reviewers"].values():
        assert arms["old"]["stable"] is None


def test_report_never_counts_a_failed_run_as_zero_findings(lab, monkeypatch):
    def outcome(sha, name):
        return "FAIL" if name == "security-reviewer" and sha == lab["new"] else "major"

    new = _report(lab, monkeypatch, outcome)["reviewers"]["security-reviewer"]["new"]
    assert new["runs"] == 0
    assert new["failed"] == 3
    assert new["blocking_per_run"] == []
    assert (new["min"], new["median"], new["max"], new["agree"]) == (None, None, None, None)


def test_report_shows_precision_only_over_labelled_findings(lab, monkeypatch):
    case = {
        "schema_version": 1,
        "pr": 1,
        "head_sha": lab["head"],
        "kind": "findings",
        "findings": [
            {
                "id": "f1",
                "reviewer": "security-reviewer",
                "path": SKILL,
                "line": 5,
                "rule": None,
                "label": "false_positive",
                "source": "owner",
                "note": "",
                "known_issue": None,
            }
        ],
        "known_issues": [],
    }
    report = _report(lab, monkeypatch, lambda *_: "major", cases=[case])
    labelled = report["reviewers"]["security-reviewer"]["old"]
    assert (labelled["labelled"], labelled["precision"]) == (3, 0.0)
    unlabelled = report["reviewers"]["dependency-reviewer"]["old"]
    assert (unlabelled["labelled"], unlabelled["precision"]) == (0, None)


def test_report_ignores_labels_of_another_head(lab, monkeypatch):
    case = {"head_sha": "0" * 40, "findings": [], "known_issues": [], "pr": 1}
    case["findings"] = [
        {"reviewer": "security-reviewer", "path": SKILL, "line": 5, "label": "true"}
    ]
    report = _report(lab, monkeypatch, lambda *_: "major", cases=[case])
    assert report["reviewers"]["security-reviewer"]["old"]["labelled"] == 0


def test_report_markdown_says_what_it_is_not(lab, monkeypatch):
    text = ab.render_markdown(_report(lab, monkeypatch, lambda *_: "major"))
    assert "security-reviewer" in text
    assert "not a significance test" in text


def test_report_markdown_escapes_model_text_in_table_cells(lab, monkeypatch):
    report = _report(lab, monkeypatch, lambda *_: "major", repeats=1)
    report["reviewers"]["security-reviewer"]["old"]["findings"][0]["rule"] = "a|b\n<img>`x"
    text = ab.render_markdown(report)
    assert "<img>" not in text
    assert "a|b" not in text


# --- command line -------------------------------------------------------------------------------


def _argv(lab, command, *extra):
    return [
        command,
        "--repo", str(lab["repo"]),
        "--head", lab["head"],
        "--base", lab["base"],
        "--arm", f"old={lab['old']}",
        "--arm", f"new={lab['new']}",
        "--repeats", "1",
        *extra,
    ]  # fmt: skip


def test_plan_command_makes_no_call_and_prints_the_count(lab, monkeypatch, capsys):
    def boom(*_, **__):
        raise AssertionError("plan must not dispatch")

    monkeypatch.setattr(review, "dispatch_reviewers", boom)
    assert ab.main(_argv(lab, "plan")) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["planned_calls"] == len(printed["prompts"]) * 2


@pytest.mark.parametrize("approved", ["0", "1", "999"])
def test_run_command_refuses_unless_the_approved_count_is_the_planned_one(
    lab, monkeypatch, capsys, approved
):
    def boom(*_, **__):
        raise AssertionError("must not dispatch")

    monkeypatch.setattr(review, "dispatch_reviewers", boom)
    out = lab["tmp"] / "out"
    argv = _argv(lab, "run", "--approved-calls", approved, "--out", str(out))
    assert ab.main(argv) == 2
    assert "approved" in capsys.readouterr().err
    assert not out.exists()


def test_run_command_runs_with_the_planned_count(lab, monkeypatch):
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], lambda *_: None))
    calls = str(_plan(lab, repeats=1).calls)
    out = lab["tmp"] / "out"
    assert ab.main(_argv(lab, "run", "--approved-calls", calls, "--out", str(out))) == 0
    assert (out / "new" / "run1.json").is_file()


def test_bad_input_exits_2_with_a_message(lab, capsys):
    argv = _argv(lab, "plan")
    argv[argv.index("--head") + 1] = "main"
    assert ab.main(argv) == 2
    assert "40 lowercase hex" in capsys.readouterr().err


def test_report_command_reads_the_run_directory(lab, monkeypatch, capsys):
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], lambda *_: "major"))
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=1), out)
    corpus = lab["tmp"] / "corpus"
    corpus.mkdir()
    assert ab.main(["report", str(out), "--corpus", str(corpus)]) == 0
    assert "security-reviewer" in json.loads(capsys.readouterr().out)["reviewers"]


# --- from the security review -------------------------------------------------------------------


def test_plan_refuses_when_git_status_fails(lab, monkeypatch):
    real = review._run_git

    def failing(repo, *args, **kwargs):
        if args[0] == "status":
            raise RuntimeError("boom")
        return real(repo, *args, **kwargs)

    monkeypatch.setattr(review, "_run_git", failing)
    with pytest.raises(ab.AbError, match="git status failed"):
        _plan(lab)


def test_plan_refuses_a_path_the_bridge_does_not_accept(lab):
    head = _commit(lab["repo"], {"plugins/demo/skills/one/a b.md": "x\n"}, "space")
    with pytest.raises(ab.AbError, match="does not accept"):
        _plan(lab, head_sha=head)


def test_a_verifier_that_cannot_run_fails_the_plan_before_any_call(lab, monkeypatch):
    def boom(*_, **__):
        raise RuntimeError("broken")

    monkeypatch.setattr(ab.review_verifiers, "run_verifiers", boom)
    with pytest.raises(ab.AbError, match="verifier"):
        _plan(lab)


def test_a_failure_after_the_calls_keeps_the_raw_reports(lab, monkeypatch):
    def boom(*_, **__):
        raise RuntimeError("gate broke")

    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], lambda *_: "major"))
    monkeypatch.setattr(review, "mark_symlinked", boom)
    out = lab["tmp"] / "out"
    with pytest.raises(RuntimeError, match="gate broke"):
        ab.run_experiment(_plan(lab), out)
    raw = json.loads((out / "old" / "raw" / "run1.json").read_text(encoding="utf-8"))
    assert raw["reports"][0]["output"]["findings"]


def test_token_shaped_model_text_is_redacted_in_every_file(lab, monkeypatch):
    token = "ghp_" + "a1B2" * 9

    def dispatch(scope, *, base_sha, repo, **_):
        reports = []
        for name in (*scope.validate, *scope.audit):
            output = _envelope(name, "major")
            output["findings"][0]["evidence"] = f"found {token}"
            reports.append(review.ReviewerReport(name, "completed", output=output))
        return tuple(reports)

    monkeypatch.setattr(review, "dispatch_reviewers", dispatch)
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=1), out)
    files = list(out.rglob("*.json"))
    assert len(files) == 5
    for path in files:
        assert token not in path.read_text(encoding="utf-8"), path


def test_report_markdown_leaves_no_link_or_reference_in_model_text(lab, monkeypatch):
    report = _report(lab, monkeypatch, lambda *_: "major", repeats=1)
    rule = "https://x.invalid www.x.invalid #12 @me"
    report["reviewers"]["security-reviewer"]["old"]["findings"][0]["rule"] = rule
    text = ab.render_markdown(report)
    for part in ("https://", "www.", " #12", "@me"):
        assert part not in text


# --- from the cross-model review ------------------------------------------------------------------


def test_a_reviewer_is_not_credited_with_another_reviewers_severity(lab, monkeypatch):
    """Same rule, path and line: the merged finding takes the higher severity for every reporter."""

    def outcome(sha, name):
        return {"security-reviewer": "major", "dependency-reviewer": "minor"}.get(name)

    report = _report(lab, monkeypatch, outcome)
    security = report["reviewers"]["security-reviewer"]["old"]
    dependency = report["reviewers"]["dependency-reviewer"]["old"]
    assert security["blocking_per_run"] == [1, 1, 1]
    assert dependency["blocking_per_run"] == [0, 0, 0]
    assert dependency["findings"][0]["severities"] == {"Minor": 3}


def test_the_combined_gate_result_keeps_the_merged_finding(lab, monkeypatch):
    def outcome(sha, name):
        return "major" if name == "security-reviewer" else "minor"

    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch([], outcome))
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=1), out)
    result = json.loads((out / "old" / "run1.json").read_text(encoding="utf-8"))
    (merged,) = [f for f in result["findings"] if f["source"] == "model"]
    assert merged["blocking"] and set(merged["reporters"]) >= set(REVIEWERS)


def test_report_counts_runs_that_never_happened(lab, monkeypatch):
    calls: list = []
    monkeypatch.setattr(review, "dispatch_reviewers", _fake_dispatch(calls, lambda *_: "FAIL"))
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=3), out)
    arms = ab.build_report(out, [])["reviewers"]["security-reviewer"]
    assert (arms["old"]["failed"], arms["old"]["missing"]) == (1, 2)
    assert (arms["new"]["runs"], arms["new"]["missing"]) == (0, 3)
    assert "Missing" in ab.render_markdown(ab.build_report(out, []))


def test_a_complete_run_reports_nothing_missing(lab, monkeypatch):
    report = _report(lab, monkeypatch, lambda *_: None, repeats=2)
    for arms in report["reviewers"].values():
        assert {a["missing"] for a in arms.values()} == {0}


def _labelled_case(lab, *rules_and_labels):
    findings = [
        {"reviewer": "security-reviewer", "path": SKILL, "line": 5, "rule": rule, "label": label}
        for rule, label in rules_and_labels
    ]
    return {"pr": 1, "head_sha": lab["head"], "findings": findings, "known_issues": []}


@pytest.mark.parametrize(
    ("labels", "labelled", "precision"),
    [
        ([("injection-surface", "true"), ("other-rule", "false_positive")], 3, 1.0),
        ([("other-rule", "true")], 0, None),
        ([(None, "true"), (None, "false_positive")], 0, None),
        ([(None, "true"), ("injection-surface", "true")], 3, 1.0),
    ],
    ids=["same-line-other-rule", "another-rule", "ambiguous", "agreeing"],
)
def test_labels_match_the_rule_and_ambiguous_ones_are_left_out(
    lab, monkeypatch, labels, labelled, precision
):
    case = _labelled_case(lab, *labels)
    report = _report(lab, monkeypatch, lambda *_: "major", cases=[case])
    arm = report["reviewers"]["security-reviewer"]["old"]
    assert (arm["labelled"], arm["precision"]) == (labelled, precision)


def test_a_verdict_named_script_does_not_hide_a_reviewers_findings(lab, monkeypatch):
    def dispatch(scope, *, base_sha, repo, **_):
        reports = []
        for name in (*scope.validate, *scope.audit):
            output = _envelope(name, "major") | {"verdict": "script"}
            reports.append(review.ReviewerReport(name, "completed", output=output))
        return tuple(reports)

    monkeypatch.setattr(review, "dispatch_reviewers", dispatch)
    out = lab["tmp"] / "out"
    ab.run_experiment(_plan(lab, repeats=1), out)
    arm = ab.build_report(out, [])["reviewers"]["security-reviewer"]["old"]
    assert arm["blocking_per_run"] == [1]


def test_the_plan_runs_the_structural_checks_the_gate_uses(lab, monkeypatch):
    seen: dict = {}
    drift = (review.StructuralFinding(path=SKILL, operation="update", reason="drift"),)
    real = ab.review_verifiers.run_verifiers

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(review, "run_delta_structural_checks", lambda *_: drift)
    monkeypatch.setattr(ab.review_verifiers, "run_verifiers", spy)
    _plan(lab)
    assert seen["structural"] == drift
