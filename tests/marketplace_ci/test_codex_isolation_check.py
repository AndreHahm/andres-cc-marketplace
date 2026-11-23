"""The codex-review step that checks the project-isolation overrides work (issue #862).

The step's script runs as Actions runs it, with a fake `codex` on PATH that renders the canary
files the way Codex 0.170.0 was observed to: each override drops its part. The FAKE_* variables
make one override fail, or the default rendering lose a canary."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "marketplace-ci.yml"
CODEX_EXEC = ROOT / "plugins" / "codex-kit" / "scripts" / "lib" / "codex-exec.mjs"
STEP = "Check the overrides keep AGENTS.md and skills out of the model input"

FAKE_CODEX = r"""#!/bin/bash
[ "$1 $2" = "debug prompt-input" ] || exit 2
args="$*"
if [[ "$args" == *-c* ]]; then call=isolated; else call=default; fi
[ "${FAKE_FAIL:-}" = "$call" ] && exit 7
[ "${FAKE_EMPTY:-}" = "$call" ] && exit 0
echo "${!#}"
if [[ "$args" != *project_doc_max_bytes=0* || "${FAKE_LEAK:-}" = doc ]]; then
  [ "${FAKE_LOSE:-}" = doc ] || cat AGENTS.md
fi
if [[ "$args" != *skills.include_instructions=false* || "${FAKE_LEAK:-}" = skill ]]; then
  [ "${FAKE_LOSE:-}" = skill ] || cat .agents/skills/*/SKILL.md
fi
exit 0
"""


def _step_script() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").split("\n")
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {STEP}")
    run = next(i for i in range(start, start + 4) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body: list[str] = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    return "\n".join(body)


@pytest.fixture
def run_step(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "codex"
    fake.write_text(FAKE_CODEX, encoding="utf-8")
    fake.chmod(0o755)
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    script = tmp_path / "step.sh"
    script.write_text(_step_script(), encoding="utf-8")

    def _run(**env: str):
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
            cwd=tmp_path,
            env={
                **os.environ,
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                "RUNNER_TEMP": str(runner_temp),
                **env,
            },
            capture_output=True,
            text=True,
            check=False,
        )

    return _run


def test_working_overrides_pass(run_step):
    result = run_step()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "neither a project AGENTS.md nor the project skill list" in result.stdout


@pytest.mark.parametrize(
    "leak,canary", [("doc", "AGENTS-DOC-CANARY"), ("skill", "SKILL-LIST-CANARY")]
)
def test_an_override_that_stops_working_fails(run_step, leak, canary):
    result = run_step(FAKE_LEAK=leak)
    assert result.returncode == 1
    assert f"{canary} reaches the model input despite the overrides" in result.stdout


@pytest.mark.parametrize("lose", ["doc", "skill"])
def test_a_control_that_shows_nothing_fails(run_step, lose):
    result = run_step(FAKE_LOSE=lose)
    assert result.returncode == 1
    assert "is missing without the overrides too" in result.stdout


@pytest.mark.parametrize(
    "call,message", [("isolated", "rendered no prompt"), ("default", "is missing without")]
)
def test_an_empty_rendering_fails(run_step, call, message):
    result = run_step(FAKE_EMPTY=call)
    assert result.returncode == 1 and message in result.stdout


def test_a_scan_that_cannot_read_the_rendering_fails(run_step, tmp_path):
    """PR #865: grep's error status read as "canary absent"."""
    fake = tmp_path / "bin" / "grep"
    fake.write_text(
        '#!/bin/bash\n[[ "$*" == *CANARY*isolated* ]] && exit 2\n'
        'PATH=/usr/bin:/bin exec grep "$@"\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    result = run_step()
    assert result.returncode == 1
    assert "could not scan the isolated model input" in result.stdout


@pytest.mark.parametrize("call", ["default", "isolated"])
def test_a_failing_command_fails(run_step, call):
    assert run_step(FAKE_FAIL=call).returncode == 7


def test_the_step_uses_exactly_the_overrides_the_bridge_passes():
    source = CODEX_EXEC.read_text(encoding="utf-8")
    found = re.search(r"PROJECT_ISOLATION_ARGS = Object\.freeze\(\[(.*?)\]\)", source)
    assert found
    args = " ".join(re.findall(r'"([^"]+)"', found[1]))
    assert f"codex debug prompt-input {args} hello" in _step_script()


def test_the_step_holds_no_secret_and_reads_no_pr_content():
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text[text.index(f"- name: {STEP}") :].split("\n      - name:")[0]
    assert "secrets." not in step and "env:" not in step and "${{" not in step
    calls = [line for line in step.split("\n") if "codex debug" in line and "echo" not in line]
    assert len(calls) == 2
    assert all('(cd "$canary_dir" && codex debug' in line for line in calls)
