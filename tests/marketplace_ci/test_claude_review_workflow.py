"""Wiring of .github/workflows/claude-review-ci.yml, the advisory Claude delta review
(docs/ci-claude-review-user-requirements.md, "R<n>"). The security-relevant shape is pinned here
because nothing else notices it drifting: the API key reaches one job's two pass steps, that job
runs only code from the base SHA beside the PR checkout, and the passes go through the Claude Agent
SDK route, whose read-only options tests/marketplace_ci/test_headless_review.py pins."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.marketplace_ci import claude_review as cr
from scripts.marketplace_ci import headless_review as hr
from scripts.marketplace_ci.review import ANCHOR_PROFILES

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / ".github/workflows/claude-review-ci.yml").read_text(encoding="utf-8")
WF = yaml.safe_load(TEXT)
JOBS = WF["jobs"]
CODEX = yaml.safe_load((ROOT / ".github/workflows/marketplace-ci.yml").read_text("utf-8"))
PASS_STEPS = ("General pass", "Security pass")


def _steps(job):
    return JOBS[job]["steps"]


def _step(job, name):
    found = [s for s in _steps(job) if s.get("name") == name]
    assert len(found) == 1, name
    return found[0]


def _pass_steps():
    return [s for s in _steps("claude-review") if s.get("name") in PASS_STEPS]


def test_triggers_and_concurrency():
    on = WF.get("on", WF.get(True))
    assert set(on) == {"pull_request"}  # R2: never pull_request_target, no on-demand trigger
    assert on["pull_request"]["types"] == ["opened", "synchronize", "reopened", "ready_for_review"]
    assert WF["concurrency"]["cancel-in-progress"] is True
    assert "pull_request.number" in WF["concurrency"]["group"]
    assert "workflow_dispatch" not in TEXT and "issue_comment" not in TEXT


def test_forks_dependabot_and_drafts_are_skipped():
    cond = JOBS["claude-scope"]["if"]
    assert "head.repo.full_name == github.repository" in cond
    assert "github.actor != 'dependabot[bot]'" in cond
    assert "pull_request.user.login != 'dependabot[bot]'" in cond
    assert "pull_request.draft == false" in cond


def test_the_api_key_reaches_only_the_two_pass_steps():
    assert TEXT.count("secrets.") == len(PASS_STEPS)
    for job, spec in JOBS.items():
        for step in spec["steps"]:
            mentions = "secrets." in json.dumps(step)
            assert mentions == (job == "claude-review" and step.get("name") in PASS_STEPS), (
                step.get("name")
            )
    assert "secrets" not in json.dumps(WF.get("env", {}))
    # The sdk route's own key, never the shared one (the Console shows its usage on its own).
    for step in _pass_steps():
        assert step["env"]["ANTHROPIC_API_KEY"] == "${{ secrets.ANTHROPIC_API_KEY_SDK }}"


def test_the_job_with_the_key_runs_only_base_code_beside_the_reviewed_tree():
    steps = _steps("claude-review")
    checkouts = [s for s in steps if "actions/checkout@" in str(s.get("uses"))]
    assert [(s["with"]["ref"], s["with"]["path"]) for s in checkouts] == [
        ("${{ github.event.pull_request.head.sha }}", "pr"),
        ("${{ github.event.pull_request.base.sha }}", "trusted"),
    ]
    assert all(s["with"]["persist-credentials"] is False for s in checkouts)
    names = [s.get("name") for s in steps]
    # Symlinks go before anything reads the tree; the runner must exist at the base SHA.
    assert names.index("Remove symlinks from the reviewed tree") < names.index("General pass")
    assert (
        "trusted/scripts/marketplace_ci/headless_review.py"
        in _step("claude-review", "Check that the base SHA has the review runner")["run"]
    )
    install = _step("claude-review", "Install the review dependencies")
    assert install["working-directory"] == "trusted"
    assert "--only-group headless-review" in install["run"] and "--locked" in install["run"]
    for step in steps:
        assert not str(step.get("uses", "")).startswith("./"), step.get("name")
        if "uv run" in step.get("run", ""):
            assert step["working-directory"] == "trusted", step.get("name")
    assert "id-token" not in JOBS["claude-review"]["permissions"]
    assert "claude-code-action" not in TEXT


def test_every_job_has_least_privilege_and_a_timeout():
    assert WF["permissions"] == {"contents": "read"}
    assert JOBS["claude-scope"]["permissions"] == {
        "contents": "read",
        "actions": "read",
        "pull-requests": "read",
        "issues": "read",
    }
    assert JOBS["claude-review"]["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert JOBS["claude-publish"]["permissions"] == {
        "contents": "read",
        "pull-requests": "write",
        "issues": "read",
    }
    for spec in JOBS.values():
        assert isinstance(spec["timeout-minutes"], int)
    assert JOBS["claude-review"]["timeout-minutes"] == cr.REVIEW_JOB_TIMEOUT_MINUTES


def test_every_action_is_pinned_by_commit_sha():
    for spec in JOBS.values():
        for step in spec["steps"]:
            uses = step.get("uses", "")
            if uses and not uses.startswith("./"):
                assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", uses), uses


def test_uv_is_pinned_and_runs_no_package_setup_code():
    """Sonar S8541/S8544: no unpinned `pip install uv`, and no package's setup code runs."""
    for job in ("claude-scope", "claude-review", "claude-publish"):
        steps = _steps(job)
        runs = [s.get("run", "") for s in steps]
        assert not any("pip install" in r for r in runs), job
        setup = [s for s in steps if str(s.get("uses", "")).startswith("astral-sh/setup-uv@")]
        assert len(setup) == 1 and setup[0]["with"]["version"] == "0.13.7", job
        syncs = [r for r in runs if r.startswith("uv sync")]
        assert len(syncs) == 1 and "--no-build" in syncs[0] and "--locked" in syncs[0], job
        uv_runs = [line for r in runs for line in r.splitlines() if "uv run" in line]
        assert uv_runs and all("uv run --no-sync" in line for line in uv_runs), job


@pytest.mark.parametrize("workflow", ["claude-review-ci.yml", "test-headless-claude-review-ci.yml"])
def test_setup_uv_never_looks_up_a_python_from_the_checkout(workflow):
    """Issue #736: without python-version, setup-uv runs `uv python find` on the working
    directory and executes the interpreter it finds, before the scope jobs restore
    .python-version and uv.toml from the base SHA, so a PR could run code there."""
    jobs = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text("utf-8"))["jobs"]
    setups = [
        (name, step)
        for name, spec in jobs.items()
        for step in spec.get("steps", [])
        if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
    ]
    assert len(setups) == 3, workflow
    for name, step in setups:
        assert step["with"] == {
            "version": "0.13.7",
            "enable-cache": "false",
            "python-version": "3.13",
        }, name


@pytest.mark.parametrize("name", PASS_STEPS)
def test_a_pass_with_no_key_fails_before_running(tmp_path, name):
    step = _step("claude-review", name)
    env = {**os.environ, "ANTHROPIC_API_KEY": "", "RUNNER_TEMP": str(tmp_path)}
    done = subprocess.run(
        ["bash", "-c", step["run"]], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert done.returncode == 1 and "ANTHROPIC_API_KEY_SDK" in done.stdout
    assert not (tmp_path / "claude-raw").exists()


def test_each_pass_runs_the_sdk_route_with_its_caps():
    """R5, R9: the sdk route's options (read-only tools, no settings sources or hooks, reads only
    inside the checkout) are pinned by test_headless_review.test_sdk_pass_options_and_result."""
    assert len(_pass_steps()) == 2
    for step in _pass_steps():
        run = step["run"]
        assert "headless-review-pass" in run and "--route sdk" in run
        assert f"--pass {step['id']}" in run
        assert '--checkout "$GITHUB_WORKSPACE/pr"' in run
        assert f'--out "$RUNNER_TEMP/claude-raw/{step["id"]}.json"' in run
        assert step["working-directory"] == "trusted"
        assert step["env"]["MODEL"] == "${{ needs.claude-scope.outputs.model }}"
        assert step["continue-on-error"] is True
        assert "pass_minutes" in step["timeout-minutes"]
    assert hr.MAX_TURNS == {"general": 50, "security": 50}
    assert hr.MAX_BUDGET_USD == 1.00


def test_the_output_schema_matches_the_publisher():
    schema = hr.REVIEW_SCHEMA
    item = schema["properties"]["findings"]["items"]
    assert tuple(item["properties"]["severity"]["enum"]) == cr.SEVERITIES
    assert tuple(schema["properties"]["verdict"]["enum"]) == cr.VERDICTS
    assert schema["properties"]["findings"]["maxItems"] == cr.MAX_FINDINGS
    path = item["properties"]["path"]
    assert path["maxLength"] == cr.MAX_PATH
    assert re.fullmatch(r"\^\[\^`<>.*\]\+\$", path["pattern"])


def test_the_pull_request_is_rechecked_right_before_each_pass():
    names = [s.get("name") for s in _steps("claude-review")]
    for check, action in (
        ("Re-check the pull request before the general pass", "General pass"),
        ("Re-check the pull request before the security pass", "Security pass"),
    ):
        assert names.index(check) == names.index(action) - 1
        assert "/usr/bin/gh api" in _step("claude-review", check)["run"]
        assert "== 'ok'" in _step("claude-review", action)["if"]


def test_only_the_collected_records_are_uploaded():
    uploads = [s for s in _steps("claude-review") if "upload-artifact" in s.get("uses", "")]
    assert [u["with"]["path"] for u in uploads] == ["${{ runner.temp }}/claude-review-raw.json"]


def _codex_step(job, name):
    found = [s for s in CODEX["jobs"][job]["steps"] if s.get("name") == name]
    assert len(found) == 1
    return found[0]


def test_the_trusted_restores_are_compute_scopes_own_blocks():
    for name in (
        "Restore kill-switch enforcement from the trusted base SHA (trust boundary)",
        "Restore the base SHA's copy of the scope-decision code and its dependency spec "
        "(trust boundary)",
    ):
        assert _step("claude-scope", name) == _codex_step("compute-scope", name)
    names = [s.get("name") for s in _steps("claude-scope")]
    restore = names.index(
        "Restore the base SHA's copy of the scope-decision code and its dependency spec "
        "(trust boundary)"
    )
    for later in (
        "Check the Claude review settings",
        "Find the last reviewed heads",
        "Compute the reviewed paths",
        "Build the reviewer prompts from the base SHA",
    ):
        assert names.index(later) > restore  # fmt: skip


def test_reviewer_instructions_come_from_the_base_sha():
    run = _step("claude-scope", "Build the reviewer prompts from the base SHA")["run"]
    for path in (
        ".github/claude-review/prompt.md",
        "REVIEW.md",
        ".claude/agents/security-reviewer.md",
    ):
        assert f'git show "$BASE_SHA:{path}"' in run


def test_the_reviewer_gets_the_patch_inside_the_checkout():
    """R5: Claude cannot read .git, so the scope job writes each pass's patch (R3: its own delta)
    and the review job places it in the checkout after the checkout, before that pass's re-check,
    at the one path prompt.md tells Claude to read."""
    build = _step("claude-scope", "Build the reviewer prompts from the base SHA")["run"]
    assert "claude-review-patch" in build
    assert 'for pair in "general:scope" "security:security-scope"; do' in build
    assert '--out "$RUNNER_TEMP/claude-scope/prompts/$pass.diff"' in build
    names = [s.get("name") for s in _steps("claude-review")]
    checkout = names.index("Check out the PR's own head commit")
    for review_pass, action in (("general", "General pass"), ("security", "Security pass")):
        place = _step("claude-review", f"Place the {review_pass} pass's patch in the checkout")
        recheck = f"Re-check the pull request before the {review_pass} pass"
        assert checkout < names.index(place["name"]) == names.index(recheck) - 1
        assert names.index(action) == names.index(recheck) + 1
        assert f"needs.claude-scope.outputs.{review_pass} == 'true'" in place["if"]
        assert (
            f'cp -- "$RUNNER_TEMP/claude-scope/prompts/{review_pass}.diff" pr/{cr.PATCH_PATH}'
            in place["run"]
        )
        assert "rm -rf -- pr/.claude-review-input" in place["run"]
    template = (ROOT / ".github/claude-review/prompt.md").read_text("utf-8")
    assert f"`{cr.PATCH_PATH}`" in template


def test_the_scope_uses_the_shared_anchor_lookup_and_the_claude_exclusions():
    """R3: one anchor lookup and one scope per pass."""
    anchor = _step("claude-scope", "Find the last reviewed heads")["run"]
    assert "for pass in general security; do" in anchor
    assert "find-review-anchor --profile claude" in anchor and '--pass "$pass"' in anchor
    run = _step("claude-scope", "Compute the reviewed paths")["run"]
    assert "--ci-delta --review-exclusions claude" in run and "--emit-review-paths" in run
    assert 'for pair in "scope:$GENERAL_ANCHOR" "security-scope:$SECURITY_ANCHOR"; do' in run
    env = _step("claude-scope", "Compute the reviewed paths")["env"]
    assert env["GENERAL_ANCHOR"] == "${{ steps.anchor.outputs.general_sha }}"
    assert env["SECURITY_ANCHOR"] == "${{ steps.anchor.outputs.security_sha }}"
    prompts = _step("claude-scope", "Build the reviewer prompts from the base SHA")["run"]
    assert '--security-scope "$RUNNER_TEMP/claude-scope/security-scope.json"' in prompts
    publish = _step("claude-publish", "Publish the review")["run"]
    assert '--security-scope "$RUNNER_TEMP/claude-scope/security-scope.json"' in publish


@pytest.mark.parametrize(
    ("present", "failed_fetches", "anchor_out", "fetches"),
    [(True, 0, "b" * 40, 0), (False, 0, "b" * 40, 1), (False, 2, "b" * 40, 3), (False, 3, "", 3)],
)
def test_the_anchor_fetch_is_retried_before_the_whole_pr_is_reviewed(
    tmp_path, present, failed_fetches, anchor_out, fetches
):
    """R3: like the Codex review (Codex R9), the anchor fetch is retried after 1 and 3 seconds;
    only when every attempt fails is there no anchor (the whole PR is reviewed)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    count = tmp_path / "fetches"
    (tmp_path / "temp").mkdir()
    tools = {
        "git": (
            f'if [ "$1" = cat-file ]; then exit {0 if present else 1}; fi\n'
            f'n=$(($(cat "{count}" 2>/dev/null || echo 0) + 1)); echo "$n" > "{count}"\n'
            f'[ "$n" -gt {failed_fetches} ]'
        ),
        "sleep": "exit 0",
        # find-review-anchor writes the anchor it found to its --github-output file: one for the
        # general pass, none for the security pass (so only the general one is fetched).
        "uv": (
            f'echo "$*" >> "{tmp_path}/lookups"\n'
            'out=""; pass=""; prev=""\n'
            'for a in "$@"; do\n'
            '  [ "$prev" = --github-output ] && out="$a"\n'
            '  [ "$prev" = --pass ] && pass="$a"\n'
            '  prev="$a"\n'
            "done\n"
            f'if [ "$pass" = general ]; then echo "sha={"b" * 40}" > "$out"; else : > "$out"; fi'
        ),
    }
    for name, body in tools.items():
        tool = bin_dir / name
        tool.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        tool.chmod(0o755)
    script = tmp_path / "anchor.sh"
    anchor_step = _step("claude-scope", "Find the last reviewed heads")
    script.write_text(anchor_step["run"], encoding="utf-8")
    output = tmp_path / "out"
    env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path / "temp"),
        "GITHUB_OUTPUT": str(output),
        "REPO": "owner/repo",
    }
    run = subprocess.run(["bash", "-e", str(script)], env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert output.read_text(encoding="utf-8") == f"general_sha={anchor_out}\nsecurity_sha=\n"
    assert (int(count.read_text("utf-8")) if count.exists() else 0) == fetches
    lookups = (tmp_path / "lookups").read_text("utf-8").splitlines()
    assert ["--pass general" in lookups[0], "--pass security" in lookups[1]] == [True, True]


def test_a_cancelled_run_publishes_nothing():
    cond = JOBS["claude-publish"]["if"]
    assert "!cancelled()" in cond and "always()" not in cond


def test_the_publish_job_is_the_anchor_profiles_producer():
    profile = ANCHOR_PROFILES["claude"]
    assert JOBS["claude-publish"]["name"] == profile.review_job
    upload = _step("claude-publish", "Upload the review result")
    assert upload["with"]["name"] == profile.result_artifact
    assert upload["if"] == "always()"
    checkout = _steps("claude-publish")[0]
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    assert "run_attempt" in _step("claude-publish", "Publish the review")["env"]["RUN_ATTEMPT"]


def test_nothing_to_review_makes_no_api_call():
    """R3: the review job runs only when at least one pass has something new to review."""
    cond = JOBS["claude-review"]["if"]
    assert "switched_off == 'false'" in cond
    assert (
        "(needs.claude-scope.outputs.general == 'true' || "
        "needs.claude-scope.outputs.security == 'true')"
    ) in cond
    assert _step("claude-review", "General pass")["if"].startswith(
        "needs.claude-scope.outputs.general == 'true' &&"
    )


_HEAD = "a" * 40


def _recheck(tmp_path, name, gh_stdout, gh_exit=0):
    """Runs a re-check step with a fake gh in place of /usr/bin/gh."""
    fake = tmp_path / "gh"
    fake.write_text(f"#!/bin/sh\nprintf '%s\\n' {shlex.quote(gh_stdout)}\nexit {gh_exit}\n")
    fake.chmod(0o755)
    # as_posix: the step uses the path unquoted, so bash would strip a Windows path's backslashes
    run = _step("claude-review", name)["run"].replace("/usr/bin/gh", fake.as_posix())
    out = tmp_path / "out"
    env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(out), "HEAD_SHA": _HEAD,
           "REPO": "o/r", "PR_NUMBER": "1"}  # fmt: skip
    subprocess.run(["bash", "-e", "-c", run], env=env, check=True, capture_output=True)
    return out.read_text("utf-8").strip()


@pytest.mark.parametrize(
    "name",
    ["Re-check the pull request before the general pass",
     "Re-check the pull request before the security pass"],
)  # fmt: skip
@pytest.mark.parametrize(
    ("gh_stdout", "gh_exit", "state"),
    [
        (f"false {_HEAD}", 0, "ok"),
        (f"true {_HEAD}", 0, "draft"),
        (f"false {'b' * 40}", 0, "head_moved"),
        ("", 1, "lookup_failed"),
        ("HTTP 502", 1, "lookup_failed"),
        ("false ", 0, "lookup_failed"),
    ],
)
def test_a_failed_lookup_is_never_reported_as_a_moved_head(
    tmp_path, name, gh_stdout, gh_exit, state
):
    assert _recheck(tmp_path, name, gh_stdout, gh_exit) == f"state={state}"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the collect step uses jq")
@pytest.mark.parametrize(
    ("general", "security", "need", "skipped", "outcomes"),
    [
        ("ok", "", "true:false", None, ["failure"]),
        ("ok", "lookup_failed", "true:true", "lookup_failed", ["failure"]),
        ("head_moved", "", "true:true", "head_moved", []),
        ("", "", "true:false", None, []),
        # R3: a pass with nothing new to review left no record and is not recorded as failed
        ("ok", "ok", "false:true", None, ["failure"]),
        ("ok", "", "false:false", None, []),
    ],
)
def test_the_collect_step_records_a_pass_that_left_no_record(
    tmp_path, general, security, need, skipped, outcomes
):
    run = _step("claude-review", "Collect the passes")["run"]
    need_general, need_security = need.split(":")
    env = {"PATH": os.environ["PATH"], "RUNNER_TEMP": str(tmp_path),
           "LIVE_GENERAL": general, "LIVE_SECURITY": security,
           "NEED_GENERAL": need_general, "NEED_SECURITY": need_security}  # fmt: skip
    subprocess.run(["bash", "-c", run], env=env, check=True, capture_output=True)
    raw = json.loads((tmp_path / "claude-review-raw.json").read_text("utf-8"))
    assert raw["skipped"] == skipped
    assert [p["outcome"] for p in raw["passes"]] == outcomes
    for record in raw["passes"]:
        with pytest.raises(cr.InvalidReview):
            cr.parse_pass(record, frozenset())
