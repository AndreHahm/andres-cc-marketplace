"""Wiring of reviewer-ab.yml (issue #862): what starts it, what may reach the API key, and that its
Codex setup is the one `codex-review` uses."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from scripts.reviewer_eval import ab

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
AB = yaml.safe_load((WORKFLOWS / "reviewer-ab.yml").read_text(encoding="utf-8"))
CI = yaml.safe_load((WORKFLOWS / "marketplace-ci.yml").read_text(encoding="utf-8"))
ON = AB[True]  # YAML 1.1 reads the key `on` as a boolean
KEY = "secrets.OPENAI_API_KEY"


def _steps(workflow: dict, job: str) -> list[dict]:
    return workflow["jobs"][job]["steps"]


def _named(steps: list[dict], name: str) -> dict:
    (step,) = [s for s in steps if s.get("name", "").startswith(name)]
    return step


def test_only_a_manual_dispatch_starts_it():
    assert list(ON) == ["workflow_dispatch"]


def test_the_default_is_a_plan_without_calls():
    assert str(ON["workflow_dispatch"]["inputs"]["approved_calls"]["default"]) == "0"


def test_the_job_conditions_are_exactly_these():
    """Compared whole: `always() || ...` would make `needs: plan` non-binding, and a re-run of `run`
    would spend the same approval again."""
    assert AB["jobs"]["plan"]["if"] == "github.ref == 'refs/heads/main'"
    assert AB["jobs"]["run"]["if"] == (
        "github.ref == 'refs/heads/main' && inputs.approved_calls != '0' && github.run_attempt == 1"
    )


def test_permissions_are_read_only_and_the_run_job_gets_only_contents():
    assert AB["permissions"] == {"contents": "read"}
    assert AB["jobs"]["plan"]["permissions"] == {"contents": "read", "actions": "read"}
    assert AB["jobs"]["run"]["permissions"] == {"contents": "read"}


def test_the_key_reaches_only_the_run_step():
    assert str(AB).count(KEY) == 1  # nowhere else: no job or workflow env, no other step
    holders = [s["name"] for s in _steps(AB, "run") if KEY in str(s)]
    assert holders == ["Run the approved calls"]


def test_the_run_job_waits_for_the_plan_and_its_provenance_checks():
    assert AB["jobs"]["run"]["needs"] == "plan"
    assert _named(_steps(AB, "plan"), "Check where the commits come from")


def test_inputs_reach_scripts_only_through_the_environment():
    for job in ("plan", "run"):
        for step in _steps(AB, job):
            assert "${{" not in step.get("run", ""), step.get("name")


def test_no_checkout_keeps_credentials():
    for job in ("plan", "run"):
        for step in _steps(AB, job):
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False


@pytest.mark.parametrize(
    "name",
    [
        "Install Codex CLI",
        "Allow Codex's bwrap sandbox on the hosted runner",
        "Check Codex does not apply the repository's own config",
        "Check the overrides keep AGENTS.md and skills out of the model input",
    ],
)
def test_the_codex_setup_is_the_same_script_as_codex_review(name):
    ours = _named(_steps(AB, "run"), name)["run"]
    ours = ours.replace("npm install -g --ignore-scripts ", "npm install -g ")
    assert ours == _named(_steps(CI, "codex-review"), name)["run"]


def test_the_checks_come_before_the_run_and_the_config_check_runs_in_the_head():
    names = [s.get("name", "") for s in _steps(AB, "run")]
    order = [
        "Allow Codex's bwrap sandbox on the hosted runner",
        "Check Codex does not apply the repository's own config",
        "Check the overrides keep AGENTS.md and skills out of the model input",
        "Check the reviewers' sandbox cannot see the key",
        "Check Codex lists no MCP server from the reviewed head",
        "Run the approved calls",
    ]
    assert [n for n in names if n in order] == order
    check = _named(_steps(AB, "run"), "Check Codex does not apply")
    assert check["working-directory"] == "${{ runner.temp }}/head"


def test_the_model_and_timeout_are_the_ones_codex_review_uses():
    ours = _named(_steps(AB, "run"), "Run the approved calls")["env"]
    theirs = _named(_steps(CI, "codex-review"), "Dispatch reviewers directly")["env"]
    for name in ("CODEX_KIT_REVIEW_MODEL", "CODEX_KIT_REVIEW_TIMEOUT_MS"):
        assert ours[name] == theirs[name]


def test_actions_are_pinned_to_a_commit():
    for job in ("plan", "run"):
        for step in _steps(AB, job):
            uses = step.get("uses", "")
            if uses and not uses.startswith("./"):
                assert re.search(r"@[0-9a-f]{40}$", uses), uses


def test_results_are_kept_even_after_a_failed_run():
    assert _named(_steps(AB, "run"), "Keep the results")["if"] == "always()"


def test_no_step_can_be_ignored_or_run_from_the_head():
    """`python -m scripts...` run from the head would execute the head's own code."""
    for job in ("plan", "run"):
        for step in [AB["jobs"][job], *_steps(AB, job)]:
            assert "continue-on-error" not in step
    located = [s["name"] for s in _steps(AB, "run") if "working-directory" in s]
    assert located == ["Check Codex does not apply the repository's own config"]
    assert not [s for s in _steps(AB, "plan") if "working-directory" in s]
    for node in (AB, *AB["jobs"].values()):
        assert "defaults" not in node


def test_the_main_checkout_names_no_other_ref():
    for job in ("plan", "run"):
        (checkout,) = [s for s in _steps(AB, job) if "actions/checkout@" in s.get("uses", "")]
        assert "ref" not in checkout["with"]


def test_the_kill_switch_comes_second_in_both_jobs():
    for job in ("plan", "run"):
        assert _steps(AB, job)[1]["uses"] == "./.github/actions/workflow-killswitch"


def test_the_run_step_passes_the_approved_number():
    assert '--approved-calls "$APPROVED_CALLS"' in _named(_steps(AB, "run"), "Run the app")["run"]


SHA = "a" * 40
GOOD = {"HEAD_SHA": SHA, "RANGE_BASE": SHA, "OLD_ARM": SHA, "NEW_ARM": SHA}
GOOD |= {"REPEATS": "3", "APPROVED_CALLS": "0"}


def _bash(script: str, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    full = {"PATH": os.environ["PATH"], "HOME": str(cwd), **env}
    return subprocess.run(
        ["bash", "-c", script], env=full, cwd=cwd, capture_output=True, text=True, check=False
    )


def test_the_input_check_passes_good_inputs(tmp_path):
    assert (
        _bash(_named(_steps(AB, "plan"), "Check the inputs")["run"], GOOD, tmp_path).returncode == 0
    )


@pytest.mark.parametrize("name", list(GOOD))
@pytest.mark.parametrize("value", ["", "main", "-1", "00", "3 ", "3\n4", "A" * 40, SHA + "\n"])
def test_the_input_check_refuses_bad_inputs(tmp_path, name, value):
    script = _named(_steps(AB, "plan"), "Check the inputs")["run"]
    assert _bash(script, {**GOOD, name: value}, tmp_path).returncode != 0


@pytest.fixture
def origin(tmp_path):
    """A clone whose origin has one branch; `stray` is a commit it holds that is on no branch."""

    def git(*args, cwd):
        base = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        base += ["-c", "commit.gpgsign=false"]
        return subprocess.run(
            [*base, *args], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout.strip()

    source = tmp_path / "source"
    source.mkdir()
    git("init", "-q", "-b", "main", cwd=source)
    git("commit", "-q", "--allow-empty", "-m", "one", cwd=source)
    clone = tmp_path / "clone"
    git("clone", "-q", str(source), str(clone), cwd=tmp_path)
    on_branch = git("rev-parse", "HEAD", cwd=clone)
    git("commit", "-q", "--allow-empty", "-m", "stray", cwd=clone)
    return clone, on_branch, git("rev-parse", "HEAD", cwd=clone)


def _provenance(tmp_path, clone, runs, *, old, new, rc=0):
    """Runs the step with a stub `gh` that applies the step's own jq filter to `runs`."""
    stub = tmp_path / "bin"
    stub.mkdir()
    (tmp_path / "runs.json").write_text(json.dumps({"workflow_runs": runs}), encoding="utf-8")
    gh = stub / "gh"
    gh.write_text(
        f'#!/usr/bin/env bash\n[ {rc} -eq 0 ] || exit {rc}\njq "$4" "{tmp_path}/runs.json"\n',
        encoding="utf-8",
    )
    gh.chmod(0o755)
    env = {**GOOD, "OLD_ARM": old, "NEW_ARM": new, "REPO": "o/r", "GH_TOKEN": "x"}
    env["PATH"] = f"{stub}:{os.environ['PATH']}"
    return _bash(_named(_steps(AB, "plan"), "Check where the commits")["run"], env, clone)


def _run_of(repo: str | None, sha: str = SHA) -> dict:
    return {"head_sha": sha, "head_repository": repo and {"full_name": repo}}


def test_the_provenance_check_passes_this_repositorys_head_and_arms(tmp_path, origin):
    clone, good, _ = origin
    result = _provenance(tmp_path, clone, [_run_of("o/r")], old=good, new=good)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "runs",
    [[], [_run_of("fork/r")], [_run_of(None)], [_run_of("o/r", "b" * 40)]],
    ids=["no-run", "fork", "deleted-fork", "another-head"],
)
def test_the_provenance_check_refuses_a_head_that_is_not_this_repositorys(tmp_path, origin, runs):
    clone, good, _ = origin
    assert _provenance(tmp_path, clone, runs, old=good, new=good).returncode != 0


def test_the_provenance_check_fails_closed_on_an_api_error(tmp_path, origin):
    clone, good, _ = origin
    assert _provenance(tmp_path, clone, [], old=good, new=good, rc=1).returncode != 0


@pytest.mark.parametrize("arm", ["old", "new"])
@pytest.mark.parametrize("kind", ["stray", "unknown"])
def test_the_provenance_check_refuses_an_arm_on_no_branch(tmp_path, origin, arm, kind):
    clone, good, stray = origin
    arms = {"old": good, "new": good, arm: stray if kind == "stray" else "c" * 40}
    assert _provenance(tmp_path, clone, [_run_of("o/r")], **arms).returncode != 0


@pytest.mark.parametrize(
    ("approved", "ok"), [("0", True), ("24", True), ("23", False), ("1", False)]
)
def test_the_plan_step_refuses_any_other_approved_number(tmp_path, approved, ok):
    stub = tmp_path / "uv"
    stub.write_text("#!/usr/bin/env bash\necho '{\"planned_calls\": 24}'\n", encoding="utf-8")
    stub.chmod(0o755)
    env = {**GOOD, "APPROVED_CALLS": approved, "RUNNER_TEMP": str(tmp_path)}
    env |= {"PATH": f"{tmp_path}:{os.environ['PATH']}"}
    env["GITHUB_STEP_SUMMARY"] = str(tmp_path / "summary")
    result = _bash(_named(_steps(AB, "plan"), "Plan the calls")["run"], env, tmp_path)
    assert (result.returncode == 0) is ok


def test_nothing_logs_codex_in():
    """A login writes a file that a read-only sandbox can read."""
    for job in ("plan", "run"):
        for step in _steps(AB, job):
            assert "codex login" not in step.get("run", ""), step.get("name")
    assert "CODEX_API_KEY" in _named(_steps(AB, "run"), "Run the approved calls")["env"]


GOOD_PROBE = "control=ab-control\nvar=absent\nself=read\nproc=hidden"


@pytest.mark.parametrize(
    ("answer", "login_file", "ok"),
    [
        (GOOD_PROBE, False, True),
        (GOOD_PROBE, True, False),
        (GOOD_PROBE.replace("var=absent", "var=ab-canary-value"), False, False),
        (GOOD_PROBE.replace("proc=hidden", "proc=seen"), False, False),
        (GOOD_PROBE.replace("control=ab-control", "control=absent"), False, False),
        (GOOD_PROBE.replace("self=read\n", ""), False, False),
        ("", False, False),
    ],
    ids=["hidden", "login-file", "variable", "proc", "no-control", "no-proc", "no-output"],
)
def test_the_key_check_fails_unless_the_canary_is_hidden(tmp_path, answer, login_file, ok):
    stub = tmp_path / "bin"
    stub.mkdir()
    (tmp_path / "answer").write_text(answer + "\n", encoding="utf-8")
    codex = stub / "codex"
    codex.write_text(f'#!/usr/bin/env bash\ncat "{tmp_path}/answer"\n', encoding="utf-8")
    codex.chmod(0o755)
    if login_file:
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "auth.json").write_text("{}", encoding="utf-8")
    script = _named(_steps(AB, "run"), "Check the reviewers' sandbox")["run"]
    result = _bash(script, {"PATH": f"{stub}:{os.environ['PATH']}"}, tmp_path)
    assert (result.returncode == 0) is ok, result.stdout


def test_the_key_check_writes_the_policy_before_it_probes(tmp_path):
    stub = tmp_path / "bin"
    stub.mkdir()
    codex = stub / "codex"
    (tmp_path / "answer").write_text(GOOD_PROBE + "\n", encoding="utf-8")
    codex.write_text(
        f'#!/usr/bin/env bash\ncp "$HOME/.codex/config.toml" "{tmp_path}/seen.toml"\n'
        f'cat "{tmp_path}/answer"\n',
        encoding="utf-8",
    )
    codex.chmod(0o755)
    script = _named(_steps(AB, "run"), "Check the reviewers' sandbox")["run"]
    result = _bash(script, {"PATH": f"{stub}:{os.environ['PATH']}"}, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    policy = tomllib.loads((tmp_path / "seen.toml").read_text(encoding="utf-8"))
    excluded = policy["shell_environment_policy"]["exclude"]
    assert set(excluded) == {"CODEX_API_KEY", "OPENAI_API_KEY"}


def test_the_key_check_refuses_a_codex_config_that_already_exists(tmp_path):
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "config.toml").write_text("", encoding="utf-8")
    script = _named(_steps(AB, "run"), "Check the reviewers' sandbox")["run"]
    result = _bash(script, {"PATH": os.environ["PATH"]}, tmp_path)
    assert result.returncode != 0
    assert "already exists" in result.stdout


def test_the_key_check_fails_when_codex_does(tmp_path):
    stub = tmp_path / "codex"
    stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    stub.chmod(0o755)
    script = _named(_steps(AB, "run"), "Check the reviewers' sandbox")["run"]
    result = _bash(script, {"PATH": f"{tmp_path}:{os.environ['PATH']}"}, tmp_path)
    assert result.returncode != 0


def test_the_job_outlasts_the_longest_run_a_plan_allows():
    assert AB["jobs"]["run"]["timeout-minutes"] * 60 >= ab.MAX_RUN_SECONDS + 20 * 60
    ours = _named(_steps(AB, "plan"), "Plan the calls")["env"]
    theirs = _named(_steps(AB, "run"), "Run the approved calls")["env"]
    for name in ("CODEX_KIT_REVIEW_MODEL", "CODEX_KIT_REVIEW_TIMEOUT_MS"):
        assert ours[name] == theirs[name]


def test_no_install_step_runs_package_scripts():
    for job in ("plan", "run"):
        for step in _steps(AB, job):
            run = step.get("run", "")
            assert "uv sync" not in run or "--no-build" in run
            assert "npm install" not in run or "--ignore-scripts" in run


def test_the_key_check_always_runs_and_under_the_default_environment():
    assert set(_named(_steps(AB, "run"), "Check the reviewers' sandbox")) == {"name", "run"}


def test_the_probe_itself_finds_the_key_when_nothing_hides_it(tmp_path):
    """The stub runs the real probe unsandboxed: one that cannot see the canary would pass here."""
    stub = tmp_path / "bin"
    stub.mkdir()
    codex = stub / "codex"
    codex.write_text(
        f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "{tmp_path}/argv"\nexec sh -c "${{@: -1}}"\n',
        encoding="utf-8",
    )
    codex.chmod(0o755)
    script = _named(_steps(AB, "run"), "Check the reviewers' sandbox")["run"]
    result = _bash(script, {"PATH": f"{stub}:{os.environ['PATH']}"}, tmp_path)
    assert result.returncode != 0
    for line in ("control=ab-control", "var=ab-canary-value", "self=read", "proc=seen"):
        assert line in result.stdout.splitlines()
    argv = (tmp_path / "argv").read_text(encoding="utf-8").splitlines()
    assert argv[:3] == ["sandbox", "-c", 'sandbox_mode="read-only"']


def _mcp_check(tmp_path, *, trusted="ab-control", untrusted="", head="", raw=None, fail=None):
    """Runs the step with a stub `codex` that lists servers by directory and CODEX_HOME. With `raw`,
    the head's answer is that text as it is; the `fail` answer comes with a non-zero exit."""
    stub = tmp_path / "bin"
    stub.mkdir()
    (tmp_path / "head").mkdir()

    def listed(name):
        return json.dumps([{"name": name}] if name else [])

    (tmp_path / "trusted.json").write_text(listed(trusted), encoding="utf-8")
    (tmp_path / "untrusted.json").write_text(listed(untrusted), encoding="utf-8")
    (tmp_path / "head.json").write_text(listed(head) if raw is None else raw, encoding="utf-8")
    codex = stub / "codex"
    rc = {name: int(name == fail) for name in ("head", "untrusted")}
    codex.write_text(
        "#!/usr/bin/env bash\n"
        '[ "$*" = "mcp list --json" ] || exit 9\n'
        f'if [ "$PWD" = "{tmp_path}/head" ]; then\n'
        f'cat "{tmp_path}/head.json"; exit {rc["head"]}; fi\n'
        "grep -q mcp_servers .codex/config.toml || exit 8\n"
        'if [ -z "${CODEX_HOME:-}" ]; then\n'
        f'cat "{tmp_path}/untrusted.json"; exit {rc["untrusted"]}; fi\n'
        'grep -qF "[projects.\\"$PWD\\"]" "$CODEX_HOME/config.toml" || exit 7\n'
        f'cat "{tmp_path}/trusted.json"\n',
        encoding="utf-8",
    )
    codex.chmod(0o755)
    env = {"PATH": f"{stub}:{os.environ['PATH']}", "RUNNER_TEMP": str(tmp_path)}
    return _bash(_named(_steps(AB, "run"), "Check Codex lists no MCP")["run"], env, tmp_path)


def test_the_mcp_check_passes_when_only_the_trusted_control_lists_a_server(tmp_path):
    result = _mcp_check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "answers",
    [
        {"trusted": ""},
        {"untrusted": "ab-control"},
        {"head": "evil"},
        {"raw": ""},
        {"raw": "no"},
        {"raw": "{}"},
        {"raw": '[{"name": ""}]'},
        {"raw": "[{}]"},
        {"fail": "head"},
        {"fail": "untrusted"},
    ],
    ids=lambda a: "-".join(f"{k}:{v}" for k, v in a.items()),
)
def test_the_mcp_check_fails_otherwise(tmp_path, answers):
    assert _mcp_check(tmp_path, **answers).returncode != 0


def test_the_mcp_check_always_runs_without_the_key():
    assert set(_named(_steps(AB, "run"), "Check Codex lists no MCP")) == {"name", "run"}
