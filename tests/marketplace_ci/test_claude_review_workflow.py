"""Wiring of .github/workflows/claude-review-ci.yml, the advisory Claude delta review
(docs/ci-claude-review-user-requirements.md, "R<n>"). The security-relevant shape is pinned here
because nothing else notices it drifting: the API key reaches one job, that job runs no
repository code, and Claude Code gets read-only tools with the repository's hooks switched off."""

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
from scripts.marketplace_ci.review import ANCHOR_PROFILES

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / ".github/workflows/claude-review-ci.yml").read_text(encoding="utf-8")
WF = yaml.safe_load(TEXT)
JOBS = WF["jobs"]
CODEX = yaml.safe_load((ROOT / ".github/workflows/marketplace-ci.yml").read_text("utf-8"))
ACTION = "anthropics/claude-code-action@"


def _steps(job):
    return JOBS[job]["steps"]


def _step(job, name):
    found = [s for s in _steps(job) if s.get("name") == name]
    assert len(found) == 1, name
    return found[0]


def _action_steps():
    return [s for s in _steps("claude-review") if str(s.get("uses", "")).startswith(ACTION)]


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


def test_the_api_key_reaches_only_the_review_passes_and_their_leak_checks():
    allowed = {
        "General pass",
        "Security pass",
        "Record the general pass",
        "Record the security pass",
    }
    assert TEXT.count("secrets.") == len(allowed)
    for job, spec in JOBS.items():
        for step in spec["steps"]:
            mentions = "secrets." in json.dumps(step)
            assert mentions == (job == "claude-review" and step.get("name") in allowed), step.get(
                "name"
            )
    assert "secrets" not in json.dumps(WF.get("env", {}))


def test_output_holding_the_api_key_is_dropped_before_any_file_has_it():
    """Security review M1: the key reaches jq through its environment, never argv."""
    for name in ("Record the general pass", "Record the security pass"):
        step = _step("claude-review", name)
        assert step["env"]["API_KEY"] == "${{ secrets.ANTHROPIC_API_KEY }}"
        assert "contains($ENV.API_KEY)" in step["run"]
        assert '"$API_KEY"' not in step["run"] and "$STRUCTURED" not in step["run"]


def test_the_job_with_the_key_runs_no_repository_code():
    for step in _steps("claude-review"):
        run = step.get("run", "")
        assert "uv " not in run and "python" not in run and "pip " not in run, step.get("name")
        uses = step.get("uses", "")
        assert not uses.startswith("./"), step.get("name")
    assert "id-token" not in JOBS["claude-review"]["permissions"]


def test_every_job_has_least_privilege_and_a_timeout():
    assert WF["permissions"] == {"contents": "read"}
    assert JOBS["claude-scope"]["permissions"] == {"contents": "read", "actions": "read"}
    assert JOBS["claude-review"]["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert JOBS["claude-publish"]["permissions"] == {"contents": "read", "pull-requests": "write"}
    for spec in JOBS.values():
        assert isinstance(spec["timeout-minutes"], int)
    assert JOBS["claude-review"]["timeout-minutes"] == cr.REVIEW_JOB_TIMEOUT_MINUTES


def test_every_action_is_pinned_by_commit_sha():
    for spec in JOBS.values():
        for step in spec["steps"]:
            uses = step.get("uses", "")
            if uses and not uses.startswith("./"):
                assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", uses), uses
    assert "# ratchet:anthropics/claude-code-action@v1.0.271" in TEXT


_MODEL_EXPR = "${{ needs.claude-scope.outputs.model }}"


def _claude_args(step):
    """The CLI arguments, with the (validated) model expression standing as one word."""
    return shlex.split(step["with"]["claude_args"].replace(_MODEL_EXPR, "MODEL"))


def test_claude_gets_read_only_tools_and_no_repository_hooks():
    """R5: the repository's .claude/settings.json registers hooks that run its own scripts."""
    assert len(_action_steps()) == 2
    for step in _action_steps():
        args = _claude_args(step)
        # no project .mcp.json server starts: the action sets enableAllProjectMcpServers in the
        # user settings this run loads
        assert args.count("--strict-mcp-config") == 1
        args.remove("--strict-mcp-config")
        pairs = dict(zip(args[::2], args[1::2], strict=True))
        assert pairs["--tools"] == "Read,Grep,Glob"
        assert pairs["--allowedTools"] == "Read,Grep,Glob"
        assert pairs["--disallowedTools"] == "mcp__*"
        assert pairs["--setting-sources"] == "user"
        settings = json.loads(pairs["--settings"])
        assert settings["disableAllHooks"] is True
        # security review M1: no read outside the checkout (/proc/*/environ holds the key)
        assert settings["permissions"]["blockReadsOutsideWorkingDirectories"] is True
        assert {"Read(//proc/**)", "Read(.git/**)"} <= set(settings["permissions"]["deny"])
        # R9: per-pass caps
        assert (pairs["--max-turns"], pairs["--max-budget-usd"]) == ("25", "1.00")
        assert pairs["--model"] == "MODEL"
        assert step["with"]["github_token"] == "${{ github.token }}"
        assert step["continue-on-error"] is True
        assert "pass_minutes" in step["timeout-minutes"]
        for forbidden in ("allowed_non_write_users", "show_full_output", "display_report"):
            assert forbidden not in step["with"]


def test_the_output_schema_matches_the_publisher():
    for step in _action_steps():
        args = _claude_args(step)
        schema = json.loads(args[args.index("--json-schema") + 1])
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


def test_only_the_result_entry_of_the_transcript_is_kept():
    for name in ("Record the general pass", "Record the security pass"):
        run = _step("claude-review", name)["run"]
        assert 'select(.type == "result")' in run and 'rm -f "$exec_file"' in run
    assert "claude-execution-output.json" not in json.dumps(
        [s for s in _steps("claude-review") if "upload-artifact" in s.get("uses", "")]
    )


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
        "Find the last reviewed head",
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


def test_the_scope_uses_the_shared_anchor_lookup_and_the_claude_exclusions():
    assert (
        "find-review-anchor --profile claude"
        in _step("claude-scope", "Find the last reviewed head")["run"]
    )
    run = _step("claude-scope", "Compute the reviewed paths")["run"]
    assert "--ci-delta --review-exclusions claude" in run and "--emit-review-paths" in run


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
    cond = JOBS["claude-review"]["if"]
    assert "has_paths == 'true'" in cond and "switched_off == 'false'" in cond


@pytest.mark.skipif(shutil.which("jq") is None, reason="the record step uses jq")
@pytest.mark.parametrize(
    ("structured", "leak"),
    [('{"verdict":"LGTM","findings":[]}', False), ('{"x":"key=sk-ant-DUMMY-KEY-123"}', True)],
)
def test_the_record_step_drops_output_that_holds_the_key(tmp_path, structured, leak):
    run = _step("claude-review", "Record the general pass")["run"]
    (tmp_path / "claude-execution-output.json").write_text(
        json.dumps([{"type": "system"}, {"type": "result", "subtype": "success", "is_error": False,
                    "num_turns": 3, "total_cost_usd": 0.2, "result": "transcript text"}]),
        "utf-8",
    )  # fmt: skip
    env = {
        "PATH": os.environ["PATH"],
        "RUNNER_TEMP": str(tmp_path),
        "PASS": "general",
        "OUTCOME": "success",
        "STRUCTURED": structured,
        "API_KEY": "sk-ant-DUMMY-KEY-123",
    }
    subprocess.run(["bash", "-c", run], env=env, check=True, capture_output=True)
    record = json.loads((tmp_path / "claude-raw" / "general.json").read_text("utf-8"))
    assert record["secret_found"] is leak
    assert record["structured_output"] == ("" if leak else structured)
    assert record["result"] == {"subtype": "success", "is_error": False, "num_turns": 3,
                                "total_cost_usd": 0.2}  # fmt: skip
    assert not (tmp_path / "claude-execution-output.json").exists()
