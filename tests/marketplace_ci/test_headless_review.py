"""The test headless Claude review (scripts/marketplace_ci/headless_review.py and
.github/workflows/test-headless-claude-review-ci.yml). Fakes stand in for both SDKs: nothing here
calls the API. The security-relevant shape is pinned: the api route's tools read nothing outside
the checkout or under .git, the sdk route loads no settings, MCP servers or write tools, the action
route is the Claude delta review's own steps on its own key, each API key reaches only its route's
pass steps (and the action route's leak checks), and nothing is posted to the pull request."""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts.marketplace_ci import headless_review as hr
from scripts.marketplace_ci.__main__ import main
from scripts.marketplace_ci.claude_review import parse_pass

ROOT = Path(__file__).resolve().parents[2]
WF_PATH = ROOT / ".github/workflows/test-headless-claude-review-ci.yml"
TEXT = WF_PATH.read_text(encoding="utf-8")
WF = yaml.safe_load(TEXT)
JOBS = WF["jobs"]
CLAUDE_WF = yaml.safe_load((ROOT / ".github/workflows/claude-review-ci.yml").read_text("utf-8"))

VERDICT = {
    "verdict": "Changes Requested",
    "findings": [
        {"severity": "Major", "path": "a.py", "line": 2, "title": "t", "body": "b"},
    ],
}


# --- the api route's file tools -------------------------------------------------------------


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    root = tmp_path / "pr"
    (root / "pkg").mkdir(parents=True)
    (root / "a.py").write_text("one\ntwo secret_word\nthree\n", encoding="utf-8")
    (root / "pkg" / "b.py").write_text("secret_word here\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("secret_word in git\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret_word outside\n", encoding="utf-8")
    (tmp_path / "outdir").mkdir()
    (tmp_path / "outdir" / "c.py").write_text("secret_word in outdir\n", encoding="utf-8")
    os.symlink(outside, root / "link.txt")
    os.symlink(tmp_path / "outdir", root / "linkdir")
    os.symlink(root / "a.py", root / "inner_link.py")
    return root


def test_read_numbers_lines_and_pages(checkout: Path):
    files = hr.CheckoutFiles(checkout)
    assert files.read("a.py") == "     1\tone\n     2\ttwo secret_word\n     3\tthree"
    assert files.read("a.py", offset=2, limit=1) == "     2\ttwo secret_word\n... 1 more lines"
    assert files.read(str(checkout / "pkg" / "b.py")).endswith("secret_word here")


@pytest.mark.parametrize(
    "path", ["../outside.txt", "link.txt", "linkdir/c.py", ".git/config", "/etc/passwd",
             "/proc/self/environ", "pkg/../../outside.txt", ""],
)  # fmt: skip
def test_read_refuses_anything_outside_the_checkout_or_under_git(checkout: Path, path: str):
    text, is_error = hr.run_tool(hr.CheckoutFiles(checkout), "Read", {"file_path": path})
    assert is_error
    assert "secret_word" not in text


def test_a_symlink_that_stays_inside_is_read(checkout: Path):
    text, is_error = hr.run_tool(hr.CheckoutFiles(checkout), "Read", {"file_path": "inner_link.py"})
    assert not is_error and "two secret_word" in text


def test_grep_and_glob_never_reach_outside_or_into_git(checkout: Path):
    files = hr.CheckoutFiles(checkout)
    grep = files.grep("secret_word")
    assert grep.splitlines() == [
        "a.py:2:two secret_word",
        "inner_link.py:2:two secret_word",
        "pkg/b.py:1:secret_word here",
    ]
    glob = files.glob("*.py").splitlines()
    assert glob == ["a.py", "inner_link.py", "pkg/b.py"]
    assert files.grep("secret_word", path="pkg", glob="*.py") == "pkg/b.py:1:secret_word here"
    for tool, args in (
        ("Grep", {"pattern": "x", "path": ".."}),
        ("Glob", {"pattern": "*", "path": ".git"}),
    ):
        _, is_error = hr.run_tool(files, tool, args)
        assert is_error


def test_bad_tool_calls_are_error_results(checkout: Path):
    files = hr.CheckoutFiles(checkout)
    assert hr.run_tool(files, "Bash", {"command": "id"})[1]
    assert hr.run_tool(files, "Grep", {"pattern": "("})[1]
    assert hr.run_tool(files, "Read", "a.py")[1]


def test_api_schema_drops_only_the_constraints_the_api_refuses():
    schema = hr.api_schema()
    assert isinstance(schema, dict)
    text = json.dumps(schema)
    for key in ("maxItems", "maxLength", "minimum", "pattern"):
        assert f'"{key}"' not in text
    item = schema["properties"]["findings"]["items"]
    assert item["additionalProperties"] is False
    assert item["required"] == ["severity", "path", "line", "title", "body"]
    assert "maxItems" in json.dumps(hr.REVIEW_SCHEMA)  # the original is left alone


# --- the api route's loop -------------------------------------------------------------------


class StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__("Credit balance is too low sk-ant-should-never-be-kept")
        self.status_code = status_code


class ApiError(Exception):
    pass


def _usage(inp=1000, out=100, write=0, read=0):
    return SimpleNamespace(
        input_tokens=inp, output_tokens=out,
        cache_creation_input_tokens=write, cache_read_input_tokens=read,
    )  # fmt: skip


def _tool_turn(name="Read", args=None):
    block = SimpleNamespace(
        type="tool_use", id="tu_1", name=name, input=args or {"file_path": "a.py"}
    )
    return SimpleNamespace(stop_reason="tool_use", content=[block], usage=_usage())


def _final_turn(payload=VERDICT):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[
            SimpleNamespace(type="thinking"),
            SimpleNamespace(type="text", text=json.dumps(payload)),
        ],
        usage=_usage(),
    )


class FakeCreate:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _run(create, checkout, **kw):
    kw.setdefault("max_turns", 50)
    return hr.run_api_pass(
        create, hr.CheckoutFiles(checkout), status_error=StatusError, api_error=ApiError,
        prompt="review", model="claude-sonnet-5-5", **kw,
    )  # fmt: skip


def test_api_pass_runs_tools_and_returns_the_structured_output(checkout: Path):
    create = FakeCreate([_tool_turn(), _final_turn()])
    result = _run(create, checkout)
    assert result.result() == {
        "subtype": "success", "is_error": False, "num_turns": 2,
        "total_cost_usd": round(2 * (1000 * 2.0 + 100 * 10.0) / 1e6, 6), "api_error_status": None,
    }  # fmt: skip
    assert json.loads(result.structured_output) == VERDICT
    assert result.usage["input_tokens"] == 2000
    second = create.calls[1]["messages"]
    assert second[-1]["content"][0]["tool_use_id"] == "tu_1"
    assert "two secret_word" in second[-1]["content"][0]["content"]
    assert create.calls[0]["tools"] == hr.API_TOOLS
    assert create.calls[0]["output_config"]["format"]["schema"] == hr.api_schema()
    record = hr.pass_record("api", "general", "success", result, "sk-ant-key", "t0", "t1")
    verdict, findings = parse_pass(record, frozenset({"a.py"}))
    assert verdict == "Changes Requested" and findings[0]["severity"] == "Major"


def test_api_pass_stops_at_the_turn_cap(checkout: Path):
    result = _run(FakeCreate([_tool_turn(), _tool_turn()]), checkout, max_turns=2)
    assert (result.subtype, result.is_error, result.num_turns) == ("error_max_turns", True, 2)


def test_api_pass_stops_at_the_budget_and_the_token_cap(checkout: Path):
    result = _run(FakeCreate([_tool_turn()]), checkout, max_budget_usd=0.001)
    assert result.subtype == "error_max_budget_usd"
    result = _run(FakeCreate([_tool_turn()]), checkout, max_total_tokens=1000)
    assert result.subtype == "error_max_budget_usd"


def test_api_pass_keeps_only_the_status_of_an_api_error(checkout: Path):
    result = _run(FakeCreate([StatusError(400)]), checkout)
    record = hr.pass_record("api", "general", "success", result, "", "t0", "t1")
    assert record["result"]["api_error_status"] == 400
    assert record["result"]["subtype"] == "error_during_execution"
    assert "Credit balance" not in json.dumps(record)
    assert _run(FakeCreate([ApiError("x")]), checkout).api_error_status is None


def test_api_pass_treats_a_refusal_or_truncation_as_an_error(checkout: Path):
    for stop in ("refusal", "max_tokens", "pause_turn"):
        turn = _final_turn()
        turn.stop_reason = stop
        assert _run(FakeCreate([turn]), checkout).subtype == "error_during_execution"


def test_api_pass_refuses_a_model_it_cannot_price(checkout: Path):
    with pytest.raises(ValueError, match="cannot cap its cost"):
        hr.run_api_pass(
            FakeCreate([]), hr.CheckoutFiles(checkout), status_error=StatusError,
            api_error=ApiError, prompt="p", model="claude-unknown", max_turns=1,
        )  # fmt: skip


# --- the sdk route --------------------------------------------------------------------------


@dataclass
class FakeResult:
    subtype: str = "success"
    is_error: bool = False
    num_turns: int = 7
    total_cost_usd: float | None = 0.12
    api_error_status: int | None = None
    structured_output: object = None
    usage: object = None


def test_sdk_pass_options_and_result(tmp_path: Path):
    seen = {}

    def options_type(**kw):
        seen.update(kw)
        return kw

    async def query(*, prompt, options):
        seen["prompt"] = prompt
        yield "assistant message"
        yield FakeResult(structured_output=VERDICT, usage={"input_tokens": 5, "output_tokens": 6})

    result = asyncio.run(
        hr.run_sdk_pass(query, options_type, FakeResult, prompt="p", model="m", max_turns=25,
                        checkout=tmp_path)
    )  # fmt: skip
    assert seen["tools"] == seen["allowed_tools"] == ["Read", "Grep", "Glob"]
    assert seen["disallowed_tools"] == ["mcp__*"]
    assert seen["setting_sources"] == [] and seen["mcp_servers"] == {}
    assert seen["strict_mcp_config"] is True
    settings = json.loads(seen["settings"])
    assert settings["disableAllHooks"] is True
    assert settings["permissions"]["blockReadsOutsideWorkingDirectories"] is True
    assert "Read(.git/**)" in settings["permissions"]["deny"]
    assert (seen["max_turns"], seen["max_budget_usd"], seen["cwd"]) == (25, 1.0, str(tmp_path))
    assert seen["output_format"] == {"type": "json_schema", "schema": hr.REVIEW_SCHEMA}
    assert result.result()["num_turns"] == 7 and result.total_cost_usd == 0.12
    assert json.loads(result.structured_output) == VERDICT
    assert result.usage["output_tokens"] == 6


def test_sdk_pass_without_a_result_message_is_an_error(tmp_path: Path):
    async def query(*, prompt, options):
        yield "nothing else"

    result = asyncio.run(
        hr.run_sdk_pass(
            query, dict, FakeResult, prompt="p", model="m", max_turns=1, checkout=tmp_path
        )
    )
    assert result.subtype == "error_during_execution" and result.is_error


def test_a_record_holding_the_key_drops_the_output():
    result = hr.PassResult("success", False, 1, 0.1, structured_output='{"x": "sk-ant-key"}')
    record = hr.pass_record("sdk", "general", "success", result, "sk-ant-key", "t0", "t1")
    assert record["secret_found"] is True and record["structured_output"] == ""


def test_run_pass_records_only_the_exception_type(monkeypatch, tmp_path: Path, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("detail that must not be kept")

    monkeypatch.setattr(hr, "run_api_pass", boom)
    monkeypatch.setitem(__import__("sys").modules, "anthropic", SimpleNamespace(
        Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=None)),
        APIStatusError=StatusError, APIError=ApiError,
    ))  # fmt: skip
    record = hr.run_pass("api", "general", prompt="p", model="claude-sonnet-5-5", checkout=tmp_path)
    assert record["outcome"] == "failure" and record["result"] is None
    assert "detail" not in json.dumps(record) and "detail" not in capsys.readouterr().out


# --- the comparison -------------------------------------------------------------------------


def test_summary_compares_the_routes(tmp_path: Path):
    ok = hr.pass_record(
        "sdk", "general", "success",
        hr.PassResult("success", False, 3, 0.05, structured_output=json.dumps(VERDICT),
                      usage={"input_tokens": 10}),
        "", "2026-11-12T08:00:00Z", "2026-11-12T08:02:00Z",
    )  # fmt: skip
    failed = hr.pass_record(
        "api", "general", "success", hr.PassResult("error_during_execution", True, 0, 0.0, 400),
        "", "t0", "t1",
    )  # fmt: skip
    for route, record in (("sdk", ok), ("api", failed)):
        d = tmp_path / "raw" / f"headless-review-raw-{route}"
        d.mkdir(parents=True)
        (d / "headless-review-raw.json").write_text(
            json.dumps({"skipped": None, "passes": [record]}), encoding="utf-8"
        )
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps({"paths": [{"path": "a.py", "status": "M"}]}), encoding="utf-8")
    out = tmp_path / "summary.md"
    assert main(["headless-review-summary", "--raw-dir", str(tmp_path / "raw"), "--scope",
                 str(scope), "--model", "claude-sonnet-5-5", "--out", str(out)]) == 0  # fmt: skip
    text = out.read_text(encoding="utf-8")
    sdk_row = next(line for line in text.splitlines() if line.startswith("| sdk | general"))
    assert "| ok | Changes Requested | 0 Critical, 1 Major" in sdk_row and "0.0500" in sdk_row
    assert "2026-11-12T08:00:00Z to 2026-11-12T08:02:00Z" in sdk_row
    api_row = next(line for line in text.splitlines() if line.startswith("| api | general"))
    assert "invalid: the general pass stopped early" in api_row and "400" in api_row


def test_summary_names_a_route_that_did_not_run():
    text = hr.summarize({}, frozenset(), "m")
    for route in ("sdk", "api", "action"):
        assert f"| {route} | - | did not run |" in text


# --- the workflow ---------------------------------------------------------------------------


def _steps(job):
    return JOBS[job]["steps"]


def test_triggers_skips_and_concurrency_match_the_claude_review():
    on = WF.get("on", WF.get(True))
    assert set(on) == {"pull_request"}
    assert on == CLAUDE_WF.get("on", CLAUDE_WF.get(True))
    assert WF["concurrency"]["cancel-in-progress"] is True
    # The Claude review's skips, plus the opt-in variable.
    assert JOBS["headless-scope"]["if"] == (
        CLAUDE_WF["jobs"]["claude-scope"]["if"] + " && vars.ACTIVATE_CLAUDE_REVIEW_TEST == '1'"
    )


def test_every_later_job_skips_when_the_scope_job_is_skipped():
    review_if = JOBS["headless-review"]["if"]
    assert JOBS["headless-review"]["needs"] == "headless-scope"
    assert "needs.headless-scope.outputs.switched_off == 'false'" in review_if
    action_if = JOBS["headless-review-action"]["if"]
    assert JOBS["headless-review-action"]["needs"] == ["headless-scope", "headless-review"]
    assert action_if.startswith("!cancelled() &&")
    assert "needs.headless-scope.outputs.switched_off == 'false'" in action_if
    assert "needs.headless-scope.outputs.has_paths == 'true'" in action_if
    assert JOBS["headless-compare"]["if"] == (
        "${{ !cancelled() && needs.headless-scope.result != 'skipped' }}"
    )


def test_the_scope_job_restores_exactly_what_the_claude_review_restores():
    ours = {s.get("name"): s for s in _steps("headless-scope")}
    theirs = {s.get("name"): s for s in CLAUDE_WF["jobs"]["claude-scope"]["steps"]}
    for name in (
        "Restore kill-switch enforcement from the trusted base SHA (trust boundary)",
        "Restore the base SHA's copy of the scope-decision code and its dependency spec "
        "(trust boundary)",
        "Check the Claude review settings",
        "Build the reviewer prompts from the base SHA",
        "Compute the reviewed paths",
    ):
        assert ours[name] == theirs[name], name


def test_each_api_key_reaches_only_its_route_pass_steps():
    holders = [
        (job, step.get("name"))
        for job in JOBS
        for step in _steps(job)
        if "secrets" in json.dumps(step)
    ]
    assert holders == [
        ("headless-review", "General pass"),
        ("headless-review", "Security pass"),
        ("headless-review-action", "Check the action route's key"),
        ("headless-review-action", "General pass"),
        ("headless-review-action", "Record the general pass"),
        ("headless-review-action", "Security pass"),
        ("headless-review-action", "Record the security pass"),
    ]
    # The matrix picks the headless routes' secrets; the action route names its own, and the key
    # check sees only whether it is set.
    assert TEXT.count("secrets[matrix.key_secret]") == 2
    assert TEXT.count("secrets.ANTHROPIC_API_KEY_CODE") == 5
    assert "secrets.ANTHROPIC_API_KEY " not in TEXT and "secrets.ANTHROPIC_API_KEY }}" not in TEXT
    check = _action_step("Check the action route's key")
    assert check["env"] == {"KEY_SET": "${{ secrets.ANTHROPIC_API_KEY_CODE != '' }}"}
    for step in _steps("headless-review"):
        if "secrets" in json.dumps(step):
            assert step["working-directory"] == "trusted"
            assert step["env"]["ANTHROPIC_API_KEY"] == "${{ secrets[matrix.key_secret] }}"
            assert "headless-review-pass" in step["run"]
            assert '--checkout "$GITHUB_WORKSPACE/pr"' in step["run"]


@pytest.mark.parametrize("name", ["General pass", "Security pass"])
def test_a_pass_with_no_key_fails_before_running(tmp_path: Path, name: str):
    step = next(s for s in _steps("headless-review") if s.get("name") == name)
    env = {**os.environ, "ANTHROPIC_API_KEY": "", "ROUTE": "sdk", "RUNNER_TEMP": str(tmp_path)}
    done = subprocess.run(
        ["bash", "-c", step["run"]], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert done.returncode == 1
    assert "no API key for the sdk route (sdk: ANTHROPIC_API_KEY_SDK" in done.stdout
    assert not (tmp_path / "headless-raw").exists()


def test_nothing_is_posted_and_routes_run_one_at_a_time():
    for job in JOBS.values():
        assert "write" not in json.dumps(job.get("permissions", {}))
    assert WF["permissions"] == {"contents": "read"}
    strategy = JOBS["headless-review"]["strategy"]
    assert strategy["max-parallel"] == 1
    # Each route its own secret, and no fallback from the sdk key to the shared one.
    assert strategy["matrix"] == {
        "include": [
            {"route": "sdk", "key_secret": "ANTHROPIC_API_KEY_SDK"},
            {"route": "api", "key_secret": "ANTHROPIC_API_KEY"},
        ]
    }
    # claude-code-action runs only in the action route's job.
    for name, job in JOBS.items():
        if name != "headless-review-action":
            assert "claude-code-action" not in json.dumps(job), name


def test_the_key_holding_job_runs_base_code_beside_the_reviewed_tree():
    checkouts = [s for s in _steps("headless-review") if "actions/checkout@" in str(s.get("uses"))]
    paths = [(s["with"]["ref"], s["with"]["path"], s.get("if")) for s in checkouts]
    assert paths == [
        ("${{ github.event.pull_request.head.sha }}", "pr", None),
        ("${{ github.event.pull_request.base.sha }}", "trusted", None),
        ("${{ github.event.pull_request.head.sha }}", "trusted",
         "steps.bootstrap.outputs.use_head == 'true'"),
    ]  # fmt: skip
    install = next(
        s
        for s in _steps("headless-review")
        if s.get("name") == "Install the headless review dependencies"
    )
    assert "--only-group headless-review" in install["run"] and "--locked" in install["run"]


def test_every_action_is_pinned_by_sha():
    for job in JOBS.values():
        for step in job["steps"]:
            uses = step.get("uses")
            if uses and not uses.startswith("./"):
                ref = uses.split("@", 1)[1]
                assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), uses


# --- fixes from the security review ---------------------------------------------------------


def test_one_turn_cannot_send_more_than_the_turn_result_cap(checkout: Path, monkeypatch):
    big = "x" * 150_000
    monkeypatch.setattr(hr, "run_tool", lambda files, name, args: (big, False))
    blocks = [
        SimpleNamespace(type="tool_use", id=f"tu_{i}", name="Read", input={"file_path": "a.py"})
        for i in range(5)
    ]
    turn = SimpleNamespace(stop_reason="tool_use", content=blocks, usage=_usage())
    create = FakeCreate([turn, _final_turn()])
    _run(create, checkout)
    results = create.calls[1]["messages"][-1]["content"]
    assert sum(len(r["content"]) for r in results) <= hr.MAX_TURN_RESULT_CHARS + 200
    assert len(results) == 5 and results[-1]["is_error"] is True


def test_grep_searches_only_the_shown_part_of_a_line(checkout: Path):
    (checkout / "long.txt").write_text("a" * 5000 + "TAIL\n", encoding="utf-8")
    files = hr.CheckoutFiles(checkout)
    assert files.grep("TAIL") == "(no matches)"
    assert files.grep("a+", path="long.txt") == "long.txt:1:" + "a" * hr.MAX_LINE_CHARS


def test_an_overflowing_tool_argument_is_an_error_result(checkout: Path):
    _, is_error = hr.run_tool(hr.CheckoutFiles(checkout), "Read",
                              {"file_path": "a.py", "offset": float("inf")})  # fmt: skip
    assert is_error


def test_a_credential_shaped_string_is_redacted_in_the_record():
    token = "ghp_" + "A" * 36
    result = hr.PassResult("success", False, 1, 0.1, structured_output=json.dumps({"x": token}))
    record = hr.pass_record("api", "general", "success", result, "sk-ant-other", "t0", "t1")
    assert token not in record["structured_output"]
    assert json.loads(record["structured_output"])["x"] != token


def test_sdk_pass_silences_stderr_and_never_prompts(tmp_path: Path):
    seen = {}

    def options_type(**kw):
        seen.update(kw)
        return kw

    async def query(*, prompt, options):
        yield FakeResult(structured_output=VERDICT)

    asyncio.run(hr.run_sdk_pass(query, options_type, FakeResult, prompt="p", model="m",
                                max_turns=1, checkout=tmp_path))  # fmt: skip
    assert seen["permission_mode"] == "dontAsk"
    assert seen["stderr"]("API Error: 400 Credit balance is too low") is None


def _run_block(job: str, name: str) -> str:
    return next(s for s in _steps(job) if s.get("name") == name)["run"]


def test_the_symlink_step_removes_every_link(tmp_path: Path):
    pr = tmp_path / "pr"
    (pr / ".git").mkdir(parents=True)
    (pr / "d").mkdir()
    (pr / "a").write_text("x", encoding="utf-8")
    os.symlink("/proc/self/environ", pr / "d" / "x")
    os.symlink("../..", pr / "up")
    os.symlink("a", pr / ".git" / "keep")
    script = _run_block("headless-review", "Remove symlinks from the reviewed tree")
    done = subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert not (pr / "d" / "x").is_symlink() and not (pr / "up").is_symlink()
    assert (pr / "a").exists()
    assert "removed symlink: pr/up" in done.stdout


@pytest.mark.parametrize("job", ["headless-review", "headless-compare"])
@pytest.mark.parametrize(
    ("has_file", "base_ref", "rc", "use_head"),
    [(True, "other", 0, "false"), (False, "main", 0, "true"), (False, "other", 1, None)],
)
def test_the_bootstrap_fallback_runs_only_into_the_default_branch(
    tmp_path: Path, job, has_file, base_ref, rc, use_head
):
    step = next(s for s in _steps(job) if s.get("id") == "bootstrap")
    prefix = "trusted/" if job == "headless-review" else ""
    target = tmp_path / prefix / "scripts/marketplace_ci/headless_review.py"
    if has_file:
        target.parent.mkdir(parents=True)
        target.write_text("", encoding="utf-8")
    out = tmp_path / "out"
    env = {**os.environ, "BASE_REF": base_ref, "DEFAULT_BRANCH": "main", "GITHUB_OUTPUT": str(out)}
    done = subprocess.run(["bash", "-c", step["run"]], cwd=tmp_path, env=env, capture_output=True)
    assert done.returncode == rc
    if use_head is not None:
        assert out.read_text(encoding="utf-8") == f"use_head={use_head}\n"


def test_each_job_installs_what_its_code_imports():
    import tomllib

    groups = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["dependency-groups"]
    # pass_record redacts through claude_review -> review.py, which imports yaml.
    assert any(dep.startswith("PyYAML") for dep in groups["headless-review"])
    sync = [s["run"] for s in _steps("headless-compare") if "uv sync" in str(s.get("run"))]
    assert sync and "--group dev" in sync[0]


# --- fixes from the cross-model review ------------------------------------------------------


def test_every_api_request_asks_for_prompt_caching(checkout: Path):
    create = FakeCreate([_tool_turn(), _tool_turn(), _final_turn()])
    _run(create, checkout)
    assert len(create.calls) == 3
    assert all(call["cache_control"] == {"type": "ephemeral"} for call in create.calls)


def test_the_budget_stops_before_a_request_that_could_pass_it(checkout: Path):
    # The first request's worst case is the overhead plus the prompt as cache writes and the
    # full output; a budget just below it stops before anything is sent.
    first = hr.request_bound_usd("claude-sonnet-5-5", hr.PROMPT_OVERHEAD_TOKENS + 3)
    create = FakeCreate([_final_turn()])
    result = _run(create, checkout, max_budget_usd=first * 0.99)
    assert result.subtype == "error_max_budget_usd" and create.calls == []
    # A large carried context makes the second request's bound pass the budget.
    big = _tool_turn()
    big.usage = _usage(inp=300_000)
    create = FakeCreate([big, _final_turn()])
    result = _run(create, checkout)
    assert result.subtype == "error_max_budget_usd" and len(create.calls) == 1


def test_a_backtracking_pattern_is_stopped_at_the_deadline(checkout: Path, monkeypatch):
    (checkout / "evil.txt").write_text("a" * 40 + "b\n", encoding="utf-8")
    monkeypatch.setattr(hr, "GREP_TIMEOUT_SECONDS", 1.0)
    text, is_error = hr.run_tool(
        hr.CheckoutFiles(checkout), "Grep", {"pattern": "(a+)+$", "path": "evil.txt"}
    )
    assert is_error and "stopped after 1 s" in text


def test_the_grep_child_gets_no_environment(checkout: Path, monkeypatch):
    seen = {}
    real_run = hr.subprocess.run

    def spy(*args, **kwargs):
        seen["env"] = kwargs.get("env")
        return real_run(*args, **kwargs)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-reach-the-child")
    monkeypatch.setattr(hr.subprocess, "run", spy)
    assert hr.CheckoutFiles(checkout).grep("here", path="pkg") == "pkg/b.py:1:secret_word here"
    assert seen["env"] == {}


# --- fixes from the cross-model re-review ---------------------------------------------------


def test_a_final_answer_past_the_budget_is_not_a_success(checkout: Path):
    final = _final_turn()
    final.usage = _usage(inp=100_000)  # $0.20 at Sonnet 5.5 input prices
    result = _run(FakeCreate([final]), checkout, max_budget_usd=0.19)
    # The pre-request bound for the first request (overhead + prompt + full output) is below
    # $0.19, so the request is sent; its real usage then passes the budget.
    assert result.subtype == "error_max_budget_usd" and result.structured_output == ""
    final = _final_turn()
    final.usage = _usage(inp=2000)
    assert _run(FakeCreate([final]), checkout, max_total_tokens=1000).subtype == (
        "error_max_budget_usd"
    )


def test_summary_marks_an_api_budget_stop_as_the_conservative_guard():
    stopped = hr.PassResult("error_max_budget_usd", True, 9, 0.4)
    raws = {
        route: {"skipped": None, "passes": [hr.pass_record(route, "general", "success", stopped,
                                                           "", "t0", "t1")]}
        for route in ("api", "sdk")
    }  # fmt: skip
    rows = {
        line.split(" | ")[0]: line for line in hr.summarize(raws, frozenset(), "m").splitlines()
    }
    assert "(conservative api-route guard)" in rows["| api"]
    assert "conservative" not in rows["| sdk"]


# --- Haiku 5.5 pricing (CLAUDE_KIT_REVIEW_MODEL is claude-haiku-5-5) ------------------------


def test_haiku_is_priced_on_both_rate_cards():
    short = _usage(inp=1_000_000, out=0)
    assert hr.cost_usd("claude-haiku-5-5", _usage(inp=100_000, out=1_000_000)) == pytest.approx(
        (100_000 * 0.10 + 1_000_000 * 0.50) / 1e6
    )
    # Above 100K prompt tokens, cached ones included, the whole request uses the second card.
    long = _usage(inp=1_000, out=1_000, write=50_000, read=60_000)
    assert hr.cost_usd("claude-haiku-5-5", long) == pytest.approx(
        (1_000 * 0.50 + 1_000 * 2.50 + 50_000 * 0.625 + 60_000 * 0.05) / 1e6
    )
    assert hr.cost_usd("claude-haiku-5-5", short) == pytest.approx(1_000_000 * 0.50 / 1e6)
    assert hr.request_bound_usd("claude-haiku-5-5", 50_000) == pytest.approx(
        (50_000 * 0.125 + hr.MAX_OUTPUT_TOKENS * 0.50) / 1e6
    )
    assert hr.request_bound_usd("claude-haiku-5-5", 200_000) == pytest.approx(
        (200_000 * 0.625 + hr.MAX_OUTPUT_TOKENS * 2.50) / 1e6
    )


def test_the_api_route_runs_on_haiku(checkout: Path):
    create = FakeCreate([_tool_turn(), _final_turn()])
    result = hr.run_api_pass(
        create, hr.CheckoutFiles(checkout), status_error=StatusError, api_error=ApiError,
        prompt="review", model="claude-haiku-5-5", max_turns=50,
    )  # fmt: skip
    assert result.subtype == "success" and create.calls[0]["model"] == "claude-haiku-5-5"
    assert result.total_cost_usd == pytest.approx(2 * (1000 * 0.10 + 100 * 0.50) / 1e6)


# --- the action route -----------------------------------------------------------------------


def _action_step(name):
    return next(s for s in _steps("headless-review-action") if s.get("name") == name)


_MODEL_EXPR = "${{ needs.headless-scope.outputs.model }}"


@pytest.mark.parametrize("name", ["General pass", "Security pass"])
def test_the_action_route_has_the_sdk_routes_hardening(name: str):
    """The action route as the Claude delta review ran it before it moved to the sdk route: the
    same read-only tools, settings, caps and schema the sdk route uses, on its own key."""
    step = _action_step(name)
    assert step["uses"].startswith("anthropics/claude-code-action@")
    assert step["with"]["anthropic_api_key"] == "${{ secrets.ANTHROPIC_API_KEY_CODE }}"
    assert step["with"]["github_token"] == "${{ github.token }}"
    assert step["continue-on-error"] is True and "pass_minutes" in step["timeout-minutes"]
    args = shlex.split(step["with"]["claude_args"].replace(_MODEL_EXPR, "MODEL"))
    assert args.count("--strict-mcp-config") == 1
    args.remove("--strict-mcp-config")
    pairs = dict(zip(args[::2], args[1::2], strict=True))
    assert pairs["--model"] == "MODEL"
    assert pairs["--tools"] == pairs["--allowedTools"] == "Read,Grep,Glob"
    assert pairs["--disallowedTools"] == "mcp__*"
    # The action loads user, project and local settings by default; only user settings here.
    assert pairs["--setting-sources"] == "user"
    assert json.loads(pairs["--settings"]) == hr.SDK_SETTINGS
    assert json.loads(pairs["--json-schema"]) == hr.REVIEW_SCHEMA
    review_pass = step["id"]
    assert pairs["--max-turns"] == str(hr.MAX_TURNS[review_pass])
    assert float(pairs["--max-budget-usd"]) == hr.MAX_BUDGET_USD
    for forbidden in ("allowed_non_write_users", "show_full_output", "display_report"):
        assert forbidden not in step["with"]


def test_the_action_route_places_the_patch_in_its_checkout():
    names = [s.get("name") for s in _steps("headless-review-action")]
    run = _action_step("Place the reviewed patch in the checkout")["run"]
    assert (
        'cp -- "$RUNNER_TEMP/claude-scope/prompts/delta.diff" .claude-review-input/delta.diff'
        in run
    )
    assert "rm -rf -- .claude-review-input" in run
    assert (
        names.index("Check out the PR's own head commit")
        < names.index("Place the reviewed patch in the checkout")
        < names.index("General pass")
    )
    assert "openssl rand -hex 16" in _action_step("Read the reviewer prompts")["run"]


def test_the_action_route_checks_out_only_the_pr_head_and_runs_no_repository_code():
    steps = _steps("headless-review-action")
    checkouts = [s for s in steps if "actions/checkout@" in str(s.get("uses"))]
    assert [(s["with"]["ref"], s["with"].get("path")) for s in checkouts] == [
        ("${{ github.event.pull_request.head.sha }}", None)
    ]
    assert all(s["with"]["persist-credentials"] is False for s in checkouts)
    runs = " ".join(s.get("run", "") for s in steps)
    assert "uv " not in runs and "python" not in runs
    assert JOBS["headless-review-action"]["permissions"] == {
        "contents": "read", "pull-requests": "read"
    }  # fmt: skip


@pytest.mark.skipif(shutil.which("jq") is None, reason="the record step uses jq")
@pytest.mark.parametrize(
    ("structured", "leak"),
    [(json.dumps(VERDICT), False), ('{"x":"key=sk-ant-DUMMY-KEY-123"}', True)],
)
def test_the_action_record_step_keeps_the_claude_review_shape(tmp_path, structured, leak):
    run = _action_step("Record the general pass")["run"]
    (tmp_path / "claude-execution-output.json").write_text(
        json.dumps([{"type": "system"}, {"type": "result", "subtype": "success", "is_error": False,
                    "num_turns": 3, "total_cost_usd": 0.2, "result": "transcript text",
                    "usage": {"input_tokens": 7, "output_tokens": 5,
                              "cache_read_input_tokens": 11}}]),
        "utf-8",
    )  # fmt: skip
    env = {
        "PATH": os.environ["PATH"],
        "RUNNER_TEMP": str(tmp_path),
        "PASS": "general",
        "OUTCOME": "success",
        "STRUCTURED": structured,
        "API_KEY": "sk-ant-DUMMY-KEY-123",
        "STARTED_AT": "2026-11-12T08:00:00Z",
    }
    subprocess.run(["bash", "-c", run], env=env, check=True, capture_output=True)
    record = json.loads((tmp_path / "headless-raw" / "general.json").read_text("utf-8"))
    assert record["route"] == "action" and record["pass"] == "general"
    assert record["secret_found"] is leak
    assert record["structured_output"] == ("" if leak else structured)
    assert record["result"] == {"subtype": "success", "is_error": False, "num_turns": 3,
                                "total_cost_usd": 0.2, "api_error_status": None}  # fmt: skip
    assert record["usage"] == {"input_tokens": 7, "output_tokens": 5,
                               "cache_creation_input_tokens": 0,
                               "cache_read_input_tokens": 11}  # fmt: skip
    assert record["started_at"] == "2026-11-12T08:00:00Z" and record["finished_at"].endswith("Z")
    assert "transcript text" not in json.dumps(record)
    assert not (tmp_path / "claude-execution-output.json").exists()
    if not leak:
        verdict, findings = parse_pass(record, frozenset({"a.py"}))
        assert verdict == "Changes Requested" and len(findings) == 1


@pytest.mark.skipif(shutil.which("jq") is None, reason="the record step uses jq")
def test_the_action_record_step_without_a_transcript_records_no_result(tmp_path):
    run = _action_step("Record the security pass")["run"]
    env = {"PATH": os.environ["PATH"], "RUNNER_TEMP": str(tmp_path), "PASS": "security",
           "OUTCOME": "failure", "STRUCTURED": "", "API_KEY": "k", "STARTED_AT": "t0"}  # fmt: skip
    subprocess.run(["bash", "-c", run], env=env, check=True, capture_output=True)
    record = json.loads((tmp_path / "headless-raw" / "security.json").read_text("utf-8"))
    assert record["result"] is None and record["usage"] == {} and record["outcome"] == "failure"


@pytest.mark.parametrize(("key_set", "code"), [("true", 0), ("false", 1)])
def test_the_action_route_fails_early_without_its_key(tmp_path, key_set, code):
    run = _action_step("Check the action route's key")["run"]
    done = subprocess.run(
        ["bash", "-c", run], env={"PATH": os.environ["PATH"], "KEY_SET": key_set},
        capture_output=True, text=True,
    )  # fmt: skip
    assert done.returncode == code
    if code:
        assert "ANTHROPIC_API_KEY_CODE" in done.stdout


def test_the_summary_shows_the_action_route(tmp_path: Path):
    record = {"route": "action", "pass": "general", "outcome": "success",
              "result": {"subtype": "success", "is_error": False, "num_turns": 4,
                         "total_cost_usd": 0.07, "api_error_status": None},
              "secret_found": False, "structured_output": json.dumps(VERDICT),
              "usage": {"input_tokens": 3}, "started_at": "s", "finished_at": "f"}  # fmt: skip
    text = hr.summarize({"action": {"skipped": None, "passes": [record]}}, frozenset({"a.py"}), "m")
    row = next(line for line in text.splitlines() if line.startswith("| action | general"))
    assert "| ok | Changes Requested |" in row and "0.0700" in row and "3/0/0/0" in row
    assert "| sdk | - | did not run |" in text


def test_run_pass_refuses_the_action_route(tmp_path: Path):
    with pytest.raises(ValueError, match="unknown route"):
        hr.run_pass("action", "general", prompt="p", model="m", checkout=tmp_path)


@pytest.mark.skipif(shutil.which("jq") is None, reason="the record step uses jq")
def test_the_action_record_step_keeps_only_numeric_token_counts(tmp_path):
    run = _action_step("Record the general pass")["run"]
    (tmp_path / "claude-execution-output.json").write_text(
        json.dumps([{"type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
                     "total_cost_usd": 0.01,
                     "usage": {"input_tokens": "| injected |", "output_tokens": 2}}]),
        "utf-8",
    )  # fmt: skip
    env = {"PATH": os.environ["PATH"], "RUNNER_TEMP": str(tmp_path), "PASS": "general",
           "OUTCOME": "success", "STRUCTURED": "", "API_KEY": "k", "STARTED_AT": "t0"}  # fmt: skip
    subprocess.run(["bash", "-c", run], env=env, check=True, capture_output=True)
    record = json.loads((tmp_path / "headless-raw" / "general.json").read_text("utf-8"))
    assert record["usage"] == {"input_tokens": 0, "output_tokens": 2,
                               "cache_creation_input_tokens": 0,
                               "cache_read_input_tokens": 0}  # fmt: skip


def test_the_sdk_route_keeps_the_sdks_own_log_text_out_of_the_job_log(
    monkeypatch, tmp_path: Path, capsys, caplog
):
    import logging
    import sys

    def fake_run(fn):
        # What the SDK does on a reader failure: log the error's text.
        logging.getLogger("claude_agent_sdk._internal.query").error(
            "Fatal error in message reader: secret detail"
        )
        raise RuntimeError("secret detail")

    monkeypatch.setitem(sys.modules, "anyio", SimpleNamespace(run=fake_run))
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", SimpleNamespace(
        ClaudeAgentOptions=dict, ResultMessage=FakeResult, query=None,
    ))  # fmt: skip
    monkeypatch.setattr(logging.getLogger("claude_agent_sdk"), "level", logging.NOTSET)
    caplog.set_level(logging.DEBUG)
    record = hr.run_pass("sdk", "general", prompt="p", model="m", checkout=tmp_path)
    assert record["outcome"] == "failure"
    # A record is only made when the logger's level lets it through, so none reaches a handler.
    assert not [r for r in caplog.records if r.name.startswith("claude_agent_sdk")]
    captured = capsys.readouterr()
    assert "secret detail" not in captured.out + captured.err
    assert "RuntimeError" in captured.out


def test_every_recheck_and_collect_step_matches_the_claude_review():
    """The test's re-checks report a failed lookup as the Claude delta review does, never as a
    moved head, and its collect steps carry that state as a skip."""
    prod = next(
        s for s in CLAUDE_WF["jobs"]["claude-review"]["steps"]
        if s.get("name") == "Re-check the pull request before the general pass"
    )["run"]  # fmt: skip
    rechecks = [
        s["run"] for job in ("headless-review", "headless-review-action")
        for s in _steps(job) if str(s.get("name", "")).startswith("Re-check the pull request")
    ]  # fmt: skip
    assert len(rechecks) == 4
    for run in rechecks:
        assert run.startswith(prod)
    for job in ("headless-review", "headless-review-action"):
        collect = next(s for s in _steps(job) if s.get("name") == "Collect the passes")
        assert "draft|head_moved|lookup_failed)" in collect["run"]
