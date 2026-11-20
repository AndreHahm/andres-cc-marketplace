"""The codex-review step that checks Codex does not apply the checkout's .codex/config.toml (#793).

The step's script runs as Actions runs it, against a real git repository, with a fake `codex` on
PATH. The fake resolves one feature, `memories`, the way Codex 0.170.0 was observed to: from a
project config only when its directory is trusted in `$CODEX_HOME/config.toml`, else the default
(false). `FAKE_CODEX_TRUST_ALL=1` makes it trust every directory, as if the job trusted the
checkout. It logs each config it applies, so a test can show the PR's own copy is never trusted.
"""

import os
import subprocess
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "marketplace-ci.yml"
STEP = "Check Codex does not apply the repository's own config"

FAKE_CODEX = r"""#!/bin/bash
[ "$1 $2" = "features list" ] || exit 2
memories=false
cfg="$PWD/.codex/config.toml"
if [ -f "$cfg" ]; then
  trusted=false
  if [ "${FAKE_CODEX_TRUST_ALL:-}" = 1 ]; then trusted=true; fi
  if grep -qF "[projects.\"$PWD\"]" "$CODEX_HOME/config.toml" 2>/dev/null; then trusted=true; fi
  if [ "$trusted" = true ]; then
    echo "$cfg" >> "$FAKE_CODEX_LOG"
    grep -q '^memories = true' "$cfg" && memories=true
  fi
fi
echo "WARNING: a line Codex prints that is not part of the table"
printf 'hooks                stable  true\n'
printf 'memories             stable  %s\n' "$memories"
"""

APPLIED = "[features]\nmemories = true\n"
DEFAULTS_ONLY = "[features]\nmemories = false\n"


def _step_script() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").split("\n")
    start = next(
        i for i, line in enumerate(lines) if line.strip().startswith("- name:") and STEP in line
    )
    run = next(i for i in range(start, start + 12) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body: list[str] = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    return "\n".join(body)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def run_step(git_repo, tmp_path):
    root = git_repo.root
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "codex"
    fake.write_text(FAKE_CODEX, encoding="utf-8")
    fake.chmod(0o755)
    log = tmp_path / "applied.log"
    log.touch()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()

    def _run(base_config: str | None, pr_config: str | None, **env: str):
        git_repo.write("README.md", "x\n")
        if base_config is not None:
            git_repo.write(".codex/config.toml", base_config)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "base")
        base_sha = _git(root, "rev-parse", "HEAD")
        config = root / ".codex" / "config.toml"
        if pr_config is None:
            config.unlink(missing_ok=True)
        else:
            config.parent.mkdir(exist_ok=True)
            config.write_text(pr_config, encoding="utf-8")
        script = tmp_path / "step.sh"
        script.write_text(_step_script(), encoding="utf-8")
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
            cwd=root,
            env={
                **os.environ,
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                "CODEX_HOME": str(codex_home),
                "RUNNER_TEMP": str(runner_temp),
                "BASE_SHA": base_sha,
                "FAKE_CODEX_LOG": str(log),
                **env,
            },
            capture_output=True,
            text=True,
            check=False,
        )
        return result, log.read_text(encoding="utf-8").splitlines()

    return _run


def test_an_unapplied_config_passes_and_the_control_shows_it_is_detectable(run_step):
    result, applied = run_step(APPLIED, APPLIED)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "changes 1 feature(s)" in result.stdout
    assert applied and all("codex-control." in path for path in applied)


def test_an_applied_config_fails_before_any_control(run_step):
    result, _ = run_step(APPLIED, APPLIED, FAKE_CODEX_TRUST_ALL="1")
    assert result.returncode == 1
    assert "applied the repository's .codex/config.toml" in result.stdout


def test_the_control_trusts_the_base_config_never_the_prs(run_step, git_repo):
    """A PR that neutralises its config does not weaken the control: the control reads the base."""
    result, applied = run_step(APPLIED, DEFAULTS_ONLY)
    assert result.returncode == 0, result.stdout + result.stderr
    checkout_config = str(git_repo.root / ".codex" / "config.toml")
    assert checkout_config not in applied


def test_a_base_config_that_changes_no_feature_fails_the_control(run_step):
    result, _ = run_step(DEFAULTS_ONLY, DEFAULTS_ONLY)
    assert result.returncode == 1
    assert "changes no feature even when trusted" in result.stdout


def test_a_base_without_a_config_runs_only_the_comparison(run_step):
    result, applied = run_step(None, None)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "base branch has no .codex/config.toml" in result.stdout
    assert applied == []


def test_a_base_config_that_is_not_a_regular_file_fails(run_step, git_repo):
    target = git_repo.root / "elsewhere.toml"
    target.write_text(APPLIED, encoding="utf-8")
    (git_repo.root / ".codex").mkdir()
    (git_repo.root / ".codex" / "config.toml").symlink_to(target)
    result, _ = run_step(None, APPLIED)
    assert result.returncode == 1
    assert "not a regular file (mode 120000)" in result.stdout
