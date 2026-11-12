"""The advisory Claude delta review's settings, prompts and publisher
(docs/ci-claude-review-user-requirements.md, "R<n>")."""

from __future__ import annotations

import json
import subprocess

import pytest

from scripts.marketplace_ci import claude_review as cr
from scripts.marketplace_ci.__main__ import main

HEAD = "a" * 40


# R8, R10: settings.


@pytest.mark.parametrize(
    ("bypass", "model", "timeout", "expected"),
    [
        ("", "", "", cr.Settings(False, "claude-sonnet-5-5", 20)),
        ("0", "claude-haiku-5-5", "1200000", cr.Settings(False, "claude-haiku-5-5", 20)),
        ("", "", "60001", cr.Settings(False, "claude-sonnet-5-5", 2)),
        # switched off: nothing else is read
        ("1", "not a model!", "nonsense", cr.Settings(True, "", 0)),
    ],
)
def test_valid_settings(bypass, model, timeout, expected):
    assert cr.review_settings(bypass, model, timeout) == expected


@pytest.mark.parametrize(
    ("bypass", "model", "timeout", "message"),
    [
        ("2", "", "", "CLAUDE_CI_REVIEW_BYPASS"),
        ("true", "", "", "CLAUDE_CI_REVIEW_BYPASS"),
        ("", "bad model", "", "CLAUDE_KIT_REVIEW_MODEL"),
        ("", "x" * 65, "", "CLAUDE_KIT_REVIEW_MODEL"),
        ("", "", "0", "positive whole number"),
        ("", "", "-5", "positive whole number"),
        ("", "", "6e5", "positive whole number"),
        ("", "", "1200001", "does not fit"),
    ],
)
def test_invalid_settings_fail_with_a_clear_message(bypass, model, timeout, message):
    with pytest.raises(cr.SettingsError, match=message):
        cr.review_settings(bypass, model, timeout)


def test_the_settings_cli_writes_outputs_and_fails_on_a_bad_value(monkeypatch, tmp_path):
    out = tmp_path / "out"
    monkeypatch.setenv("CLAUDE_CI_REVIEW_BYPASS", "0")
    monkeypatch.setenv("CLAUDE_KIT_REVIEW_MODEL", "claude-haiku-5-5")
    monkeypatch.delenv("CLAUDE_KIT_REVIEW_TIMEOUT_MS", raising=False)
    assert main(["claude-review-settings", "--github-output", str(out)]) == 0
    assert out.read_text("utf-8").splitlines() == [
        "switched_off=false",
        "model=claude-haiku-5-5",
        "pass_minutes=20",
    ]
    monkeypatch.setenv("CLAUDE_CI_REVIEW_BYPASS", "yes")
    assert main(["claude-review-settings", "--github-output", str(out)]) == 2


# R5: prompts.


def test_a_value_is_never_substituted_twice():
    template = "paths: {{PATHS}}\nrules: {{REVIEW_MD}}"
    got = cr.build_prompt(template, {"PATHS": "{{REVIEW_MD}}", "REVIEW_MD": "R"})
    assert got == "paths: {{REVIEW_MD}}\nrules: R"


def test_an_unknown_placeholder_is_an_error():
    with pytest.raises(KeyError):
        cr.build_prompt("{{NOPE}}", {})


def _scope(*entries, anchor=""):
    return {"anchor_sha": anchor, "anchor_status": "trusted" if anchor else "none",
            "paths": [dict(e) for e in entries]}  # fmt: skip


def test_the_prompts_cli_adds_a_security_prompt_only_for_a_gate_critical_delta(tmp_path):
    template = tmp_path / "prompt.md"
    template.write_text("{{PASS}} {{PATHS}} {{DELETED_PATHS}} {{SECURITY_REVIEWER_MD}}", "utf-8")
    review, security = tmp_path / "REVIEW.md", tmp_path / "sec.md"
    review.write_text("rules", "utf-8")
    security.write_text("SECURITY-INSTRUCTIONS", "utf-8")

    def run(scope):
        scope_file, out_dir, out = tmp_path / "s.json", tmp_path / "p", tmp_path / "o"
        scope_file.write_text(json.dumps(scope), "utf-8")
        for f in out_dir.glob("*") if out_dir.exists() else []:
            f.unlink()
        out.write_text("", "utf-8")
        assert main(["claude-review-prompts", "--scope", str(scope_file), "--template",
                     str(template), "--review-md", str(review), "--security-md", str(security),
                     "--base-sha", "b" * 40, "--head-sha", HEAD, "--out-dir", str(out_dir),
                     "--github-output", str(out)]) == 0  # fmt: skip
        return out.read_text("utf-8"), {f.name: f.read_text("utf-8") for f in out_dir.glob("*")}

    plain = {"status": "M", "path": "a.py", "gate_critical": False}
    gone = {"status": "D", "path": "old.py", "gate_critical": False}
    output, prompts = run(_scope(plain, gone))
    assert output == "security=false\n"
    assert set(prompts) == {"general.md"}
    assert '"a.py"' in prompts["general.md"] and '"old.py"' in prompts["general.md"]
    assert "SECURITY-INSTRUCTIONS" not in prompts["general.md"]

    critical = {"status": "M", "path": ".github/workflows/x.yml", "gate_critical": True}
    output, prompts = run(_scope(plain, critical))
    assert output == "security=true\n"
    assert set(prompts) == {"general.md", "security.md"}
    assert "SECURITY-INSTRUCTIONS" in prompts["security.md"]
    assert "SECURITY-INSTRUCTIONS" not in prompts["general.md"]


def test_the_template_names_only_known_values():
    from pathlib import Path

    template = (Path(__file__).resolve().parents[2] / ".github/claude-review/prompt.md").read_text(
        "utf-8"
    )
    values = cr.prompt_values(_scope(), "", "", "general", "b" * 40, HEAD)
    cr.build_prompt(template, values)  # raises on an unknown placeholder
    assert set(cr._PLACEHOLDER.findall(template)) == set(values)


# R6, R7: decide.


def _record(
    name,
    findings=(),
    verdict="LGTM",
    outcome="success",
    subtype="success",
    cost=0.12,
    api_error_status=None,
):
    return {
        "pass": name,
        "outcome": outcome,
        "structured_output": json.dumps({"verdict": verdict, "findings": list(findings)}),
        "result": {"subtype": subtype, "is_error": subtype != "success", "num_turns": 4,
                   "total_cost_usd": cost, "api_error_status": api_error_status},
    }  # fmt: skip


def _finding(severity="Major", path="a.py", line=3, **extra):
    return {"severity": severity, "path": path, "line": line, "title": "t", "body": "b", **extra}


_PLAIN = {"status": "M", "path": "a.py", "gate_critical": False}
_CRITICAL = {"status": "M", "path": "scripts/x.py", "gate_critical": True}


def _decide(scope, raw, review_job="success", **kw):
    return cr.decide(scope=scope, raw=raw, review_job=review_job, model="m", head_sha=HEAD,
                     run_attempt="2", **kw)  # fmt: skip


def test_minor_findings_pass_and_record_the_run():
    got = _decide(_scope(_PLAIN), {"passes": [_record("general", [_finding("Minor")])]})
    assert (got["status"], got["verdict"]) == ("clean", "LGTM")
    assert got["head_sha"] == HEAD and got["run_attempt"] == 2
    assert got["passes"] == {"general": {"cost_usd": 0.12, "turns": 4}}
    assert got["reviewed_paths"] == ["a.py"]


@pytest.mark.parametrize("severity", ["Critical", "Major"])
def test_a_blocking_finding_in_either_pass_fails(severity):
    raw = {
        "passes": [_record("general"), _record("security", [_finding(severity, "scripts/x.py")])]
    }
    got = _decide(_scope(_PLAIN, _CRITICAL), raw)
    assert (got["status"], got["verdict"], got["security_review"]) == (
        "findings", "Changes Requested", True,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("raw", "review_job", "reason"),
    [
        (None, "failure", "did not complete"),
        (None, "cancelled", "did not complete"),
        ({"passes": [_record("general", outcome="failure")]}, "success", "did not complete"),
        # the HTTP status of a rejected request is shown; only an integer, never API text
        (
            {"passes": [_record("general", outcome="failure", api_error_status=401)]},
            "success",
            "(failure, API status 401)",
        ),
        (
            {"passes": [_record("general", outcome="failure", api_error_status="key sk-ant-x")]},
            "success",
            "did not complete (failure)",
        ),
        (
            {
                "passes": [
                    _record("general", subtype="error_during_execution", api_error_status=400)
                ]
            },
            "success",
            "stopped early (error_during_execution, API status 400)",
        ),
        # R9: a per-pass cap reached
        ({"passes": [_record("general", subtype="error_max_turns")]}, "success", "stopped early"),
        ({"passes": [_record("general", subtype="error_max_budget_usd")]}, "success", "early"),
        ({"passes": [{**_record("general"), "structured_output": ""}]}, "success", "valid JSON"),
        ({"passes": [_record("general", verdict="Fine")]}, "success", "verdict"),
        ({"passes": [_record("general", [_finding(line=0)])]}, "success", "malformed"),
        ({"passes": [_record("general", [_finding(line=True)])]}, "success", "malformed"),
        ({"passes": [_record("general", [_finding(severity="High")])]}, "success", "malformed"),
        ({"passes": [_record("general", [_finding("Minor")] * 31)]}, "success", "findings list"),
        ({"skipped": "head_moved", "passes": []}, "success", "newer push"),
        ({"skipped": "lookup_failed", "passes": []}, "success", "could not be re-checked"),
    ],
)
def test_a_review_that_could_not_run_fails_and_is_not_an_anchor(raw, review_job, reason):
    got = _decide(_scope(_PLAIN), raw, review_job)
    assert got["status"] == "could_not_run"
    assert reason in got["reason"]
    assert got["findings"] == []


def test_a_missing_security_pass_could_not_run():
    got = _decide(_scope(_PLAIN, _CRITICAL), {"passes": [_record("general")]})
    assert got["status"] == "could_not_run" and "security" in got["reason"]


def test_nothing_to_review_is_a_clean_anchor_without_an_api_call():
    got = _decide(_scope(anchor="c" * 40), None, review_job="skipped")
    assert (got["status"], got["reason"]) == ("clean", "nothing new to review")


@pytest.mark.parametrize(
    ("kw", "status"),
    [({"switched_off": True}, "skipped"), ({}, "skipped")],
)
def test_switched_off_and_draft_runs_are_skipped(kw, status):
    raw = None if kw else {"skipped": "draft", "passes": []}
    assert _decide(_scope(_PLAIN), raw, **kw)["status"] == status


def test_a_missing_scope_could_not_run():
    assert _decide(None, None, review_job="skipped")["status"] == "could_not_run"


def test_model_text_cannot_mention_anyone_or_forge_the_marker():
    body = f"ping @codex review {cr.SUMMARY_MARKER}"
    raw = {"passes": [_record("general", [_finding("Minor", body=body, title="@x")])]}
    f = _decide(_scope(_PLAIN), raw)["findings"][0]
    assert "@codex" not in f["body"] and "@x" not in f["title"]
    assert cr.SUMMARY_MARKER not in f["body"]


def test_a_finding_outside_the_reviewed_paths_is_not_placed_inline_or_echoed():
    raw = {"passes": [_record("general", [_finding("Major", path="x` @bot <!-- y")])]}
    got = _decide(_scope(_PLAIN), raw)
    f = got["findings"][0]
    assert got["status"] == "findings" and f["in_scope"] is False
    assert f["path"] == "" and f["display_path"] == "(outside the reviewed paths)"


# Security review M1 and n1: credential-shaped text is redacted, never posted; the exact key
# refuses the whole pass.


@pytest.mark.parametrize("field", ["title", "body"])
@pytest.mark.parametrize(
    "secret", ["sk-ant-api03-" + "A" * 40, "ghs_" + "a" * 36, "github_pat_" + "b" * 30]
)
def test_a_secret_shaped_finding_is_redacted(field, secret):
    raw = {"passes": [_record("general", [_finding("Minor", **{field: f"see {secret} here"})])]}
    got = _decide(_scope(_PLAIN), raw)
    assert got["status"] == "clean"
    f = got["findings"][0]
    assert secret not in f[field] and "[REDACTED]" in f[field]
    assert secret not in cr.summary_body(got, [])


def test_a_pass_whose_output_held_the_key_is_refused():
    record = {**_record("general"), "secret_found": True, "structured_output": ""}
    got = _decide(_scope(_PLAIN), {"passes": [record]})
    assert got["status"] == "could_not_run" and "API key" in got["reason"]


# Security review M2 and its minors: nothing model-written breaks out of the summary.


def test_a_reviewed_path_cannot_break_out_of_its_code_span():
    odd = {"status": "M", "path": "a`b\n@x.py", "gate_critical": False}
    raw = {"passes": [_record("general", [_finding("Minor", path=odd["path"])])]}
    f = _decide(_scope(odd), raw)["findings"][0]
    assert f["path"] == odd["path"]  # the inline comment API gets the real path
    assert "`" not in f["display_path"] and "\n" not in f["display_path"]
    assert "@x" not in f["display_path"]


def test_entities_and_line_breaks_cannot_forge_mentions_or_lines():
    title = "a\n- **Status:** clean &#64;bot"
    raw = {"passes": [_record("general", [_finding("Major", title=title, path="nope.py")])]}
    result = _decide(_scope(_PLAIN), raw)
    f = result["findings"][0]
    assert "\n" not in f["title"] and "&#64;" not in f["title"]
    body = cr.summary_body(result, [f])
    assert "\n- **Status:** clean" not in body


def test_the_summary_stays_under_githubs_limit():
    many = [_finding("Minor", title="t" * 190, body="b") for _ in range(cr.MAX_FINDINGS)]
    raw = {"passes": [_record("general", many), _record("security", many)]}
    result = _decide(_scope(_PLAIN, _CRITICAL), raw)
    result["findings"] = result["findings"] * 20  # far more rows than fit
    body = cr.summary_body(result, [])
    assert len(body) <= cr.MAX_SUMMARY
    assert "more entries are in the result artifact" in body
    assert body.rstrip().endswith("Findings are not carried to later runs.")


# R6: publish.


class FakeGh:
    def __init__(self, existing="", fail_inline=False):
        self.calls = []
        self.existing = existing
        self.fail_inline = fail_inline

    def __call__(self, args, payload=None):
        self.calls.append((list(args), payload))
        rc, out = 0, ""
        if "--paginate" in args:
            out = self.existing
        elif "pulls" in args[2] and self.fail_inline:
            rc = 1
        return subprocess.CompletedProcess(args, rc, out, "")


def _result(*findings):
    raw = {"passes": [_record("general", list(findings))]}
    return _decide(_scope(_PLAIN), raw)


def test_publish_posts_blocking_findings_inline_and_one_new_summary():
    gh = FakeGh()
    cr.publish(_result(_finding("Major"), _finding("Minor")), repo="o/r", pr_number=7, gh=gh)
    inline = [p for a, p in gh.calls if a[:3] == ["-X", "POST", "repos/o/r/pulls/7/comments"]]
    assert len(inline) == 1
    assert inline[0]["commit_id"] == HEAD and inline[0]["side"] == "RIGHT"
    assert (inline[0]["path"], inline[0]["line"]) == ("a.py", 3)
    summary = [p for a, p in gh.calls if a[:3] == ["-X", "POST", "repos/o/r/issues/7/comments"]]
    assert len(summary) == 1 and summary[0]["body"].startswith(cr.SUMMARY_MARKER)
    for field in ("Verdict", "Reviewed head", "Anchor", "Model", "Security pass", "Cost"):
        assert field in summary[0]["body"]


def test_publish_updates_the_existing_summary():
    gh = FakeGh(existing="55\n")
    cr.publish(_result(), repo="o/r", pr_number=7, gh=gh)
    assert [a[:3] for a, _ in gh.calls][-1] == ["-X", "PATCH", "repos/o/r/issues/comments/55"]


def test_a_finding_github_cannot_place_inline_goes_into_the_summary():
    gh = FakeGh(fail_inline=True)
    cr.publish(_result(_finding("Critical", line=999)), repo="o/r", pr_number=7, gh=gh)
    body = gh.calls[-1][1]["body"]
    assert "not on a changed line" in body and "`a.py:999`" in body


def test_the_publish_cli_fails_the_check_on_findings(monkeypatch, tmp_path):
    scope, raw, out = tmp_path / "scope.json", tmp_path / "raw.json", tmp_path / "result.json"
    scope.write_text(json.dumps(_scope(_PLAIN)), "utf-8")
    raw.write_text(json.dumps({"passes": [_record("general", [_finding("Major")])]}), "utf-8")
    monkeypatch.setattr(cr, "publish", lambda *a, **k: [])
    args = ["publish-claude-review", "--scope", str(scope), "--raw", str(raw), "--review-job",
            "success", "--model", "m", "--head-sha", HEAD, "--run-attempt", "1", "--repo",
            "o/r", "--pr-number", "7", "--result-out", str(out)]  # fmt: skip
    assert main(args) == 1
    assert json.loads(out.read_text("utf-8"))["status"] == "findings"
    raw.write_text(json.dumps({"passes": [_record("general")]}), "utf-8")
    assert main(args) == 0
    assert main([*args, "--switched-off", "true"]) == 0
    assert json.loads(out.read_text("utf-8"))["status"] == "skipped"


# R5: the pull request's own patch, which the review job places in the checkout.


def _git(root, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip


def _patch_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    for name, text in {"a.py": "a = 1\n", "b.py": "b = 1\n", "gone.py": "removed = 1\n",
                       "old.py": "x = 1\n" * 20, "base_only.py": "1\n"}.items():  # fmt: skip
        (root / name).write_text(text, "utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    fork = _git(root, "rev-parse", "HEAD")
    _git(root, "switch", "-q", "-c", "pr")
    (root / "a.py").write_text("a = 2\n", "utf-8")
    (root / "b.py").write_text("b = 2\n", "utf-8")
    (root / "gone.py").unlink()
    _git(root, "mv", "old.py", "new.py")
    _git(root, "commit", "-q", "-am", "pr")
    head = _git(root, "rev-parse", "HEAD")
    # the base moves on after the fork: its own change is not the pull request's
    _git(root, "switch", "-q", "main")
    (root / "base_only.py").write_text("2\n", "utf-8")
    _git(root, "commit", "-q", "-am", "base moves")
    base = _git(root, "rev-parse", "HEAD")
    _git(root, "switch", "-q", "pr")
    assert fork != base
    return root, base, head


_PATCH_SCOPE = _scope(
    {"status": "M", "path": "a.py", "gate_critical": False},
    {"status": "D", "path": "gone.py", "gate_critical": False},
    {"status": "R", "path": "new.py", "old_path": "old.py", "gate_critical": False},
)


def test_the_patch_is_the_pull_requests_own_change_to_the_reviewed_paths(tmp_path):
    root, base, head = _patch_repo(tmp_path)
    patch = cr.review_patch(root, _PATCH_SCOPE, base, head)
    assert "-a = 1\n+a = 2\n" in patch
    assert "-removed = 1\n" in patch  # a deleted path's removed content
    assert "diff --git a/old.py b/old.py" in patch and "diff --git a/new.py b/new.py" in patch
    assert "b.py" not in patch  # changed, but not a reviewed path
    assert "base_only.py" not in patch  # the base's own change after the fork


def test_the_patch_is_bounded(monkeypatch, tmp_path):
    root, base, head = _patch_repo(tmp_path)
    monkeypatch.setattr(cr, "MAX_PATCH_BYTES", 40)
    patch = cr.review_patch(root, _PATCH_SCOPE, base, head)
    assert patch.endswith("read the files themselves]\n") and "[patch truncated: " in patch
    assert len(patch.split("\n[patch truncated")[0].encode()) <= 40


def test_no_reviewed_path_is_an_empty_patch(tmp_path):
    assert cr.review_patch(tmp_path, _scope(), "b" * 40, HEAD) == ""


def test_the_patch_cli_writes_the_patch_and_fails_closed(monkeypatch, tmp_path):
    root, base, head = _patch_repo(tmp_path)
    scope, out = tmp_path / "scope.json", tmp_path / "delta.diff"
    scope.write_text(json.dumps(_PATCH_SCOPE), "utf-8")
    monkeypatch.chdir(root)
    args = ["claude-review-patch", "--scope", str(scope), "--head-sha", head, "--out", str(out)]
    assert main([*args, "--base-sha", base]) == 0
    assert "+a = 2" in out.read_text("utf-8")
    out.unlink()
    assert main([*args, "--base-sha", "1" * 40]) == 2  # git cannot build it: no patch, no pass
    assert not out.exists()
