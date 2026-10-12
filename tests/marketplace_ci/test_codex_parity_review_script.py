"""git-kit's git-codex-parity-review.py mirrors CI's settings and never reports an unearned pass.

Stub `gh`, `codex` and `uv` executables on PATH stand in for the real tools, so these tests need
neither network access nor a Codex account (issue #540).
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-codex-parity-review.py"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="stub executables are POSIX shell scripts"
)

WORKFLOW = """\
      # decoy: npm install -g @openai/codex@9.9.9 and CODEX_KIT_REVIEW_TIMEOUT_MS: "1"
      - name: Install Codex CLI (pinned version, never floating latest)
        run: npm install -g @openai/codex@0.147.0

      - name: Dispatch reviewers directly, validate output, aggregate findings
        env:
          CODEX_KIT_REVIEW_MODEL: ${{ vars.CODEX_KIT_REVIEW_MODEL }}
          CODEX_KIT_REVIEW_TIMEOUT_MS: "600000"
        run: uv run python -m scripts.marketplace_ci run-codex-review

      - name: Upload review result
        run: echo "npm install -g @openai/codex@8.8.8"
"""


def _load_module():
    spec = importlib.util.spec_from_file_location("git_codex_parity_review", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_ci_settings_reads_timeout_and_pin():
    assert _load_module().parse_ci_settings(WORKFLOW) == ("600000", "0.147.0")


def test_parse_ci_settings_ignores_matches_outside_the_named_steps():
    # The decoy comment before the steps and the later step's text must not be picked up.
    assert _load_module().parse_ci_settings(WORKFLOW) == ("600000", "0.147.0")


def test_parse_ci_settings_returns_none_when_either_is_missing():
    module = _load_module()
    assert module.parse_ci_settings("CODEX_KIT_REVIEW_TIMEOUT_MS: 1\n") is None
    assert module.parse_ci_settings("npm install -g @openai/codex@1.2.3\n") is None
    no_pin = WORKFLOW.replace("npm install -g @openai/codex@0.147.0", "true")
    assert module.parse_ci_settings(no_pin) is None


def test_run_in_group_kills_the_whole_process_tree_on_timeout(tmp_path):
    pidfile = tmp_path / "child.pid"
    cmd = f"sleep 30 & echo $! > {pidfile}; wait"
    result = _load_module()._run_in_group(["sh", "-c", cmd], env=dict(os.environ), timeout=1)
    assert result is None
    child = int(pidfile.read_text())
    time.sleep(0.3)
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / "scripts/marketplace_ci").mkdir(parents=True)
    (repo / ".github/workflows/marketplace-ci.yml").write_text(WORKFLOW, encoding="utf-8")
    (repo / "scripts/marketplace_ci/__main__.py").write_text("", encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", *cmd], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=repo, check=True)
    return repo


def _run(
    repo: Path,
    tmp_path: Path,
    *,
    uv_rc: int = 0,
    codex: str | None = "codex-cli 0.147.0",
    model: str = "gpt-x",
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "uv.json"
    _stub(bin_dir, "uv", f'echo "$@ " > "{log}.args"\nenv > "{log}.env"\nexit {uv_rc}')
    # Mirrors gh 2.45.0: `variable list --json` exists, `variable get` does not.
    _stub(
        bin_dir,
        "gh",
        f'echo "$@" > "{log}.gh"\n'
        '[ "$2" = "list" ] || { echo "unknown command" >&2; exit 1; }\n'
        f'[ -n "{model}" ] && echo "{model}"\nexit 0',
    )
    # codex=None stands in for a Codex CLI that fails to run (a real one may be on PATH here).
    _stub(bin_dir, "codex", "exit 127" if codex is None else f'echo "{codex}"')
    env: dict[str, str] = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env.pop("CODEX_KIT_REVIEW_MODEL", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path / "out.json")],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    args = Path(f"{log}.args")
    uv_env = Path(f"{log}.env")
    return (
        result,
        args.read_text() if args.exists() else "",
        (uv_env.read_text() if uv_env.exists() else ""),
    )


def test_clean_run_uses_ci_settings(repo, tmp_path):
    result, args, uv_env = _run(repo, tmp_path)
    assert result.returncode == 0
    assert "run-codex-review --base-sha" in args
    assert "CODEX_KIT_REVIEW_TIMEOUT_MS=600000" in uv_env
    assert "CODEX_KIT_REVIEW_MODEL=gpt-x" in uv_env


def test_blocking_findings_exit_1(repo, tmp_path):
    result, _, _ = _run(repo, tmp_path, uv_rc=1)
    assert result.returncode == 1


def test_infrastructure_failure_is_never_a_pass(repo, tmp_path):
    for rc in (2, 3, 127):
        result, _, _ = _run(repo, tmp_path, uv_rc=rc)
        assert result.returncode == 2, rc


def test_missing_codex_cannot_run(repo, tmp_path):
    result, args, _ = _run(repo, tmp_path, codex=None)
    assert result.returncode == 2
    assert args == ""


def test_version_skew_warns_but_still_runs(repo, tmp_path):
    result, args, _ = _run(repo, tmp_path, codex="codex-cli 0.150.0")
    assert result.returncode == 0
    assert "0.150.0 differs from CI's pin 0.147.0" in result.stdout
    assert args


def test_unreadable_model_falls_back_with_a_warning(repo, tmp_path):
    result, _, uv_env = _run(repo, tmp_path, model="")
    assert result.returncode == 0
    assert "unset or unreadable" in result.stdout
    assert "CODEX_KIT_REVIEW_MODEL" not in uv_env


def test_malformed_model_value_is_not_passed_on(repo, tmp_path):
    result, _, uv_env = _run(repo, tmp_path, model="gpt x;rm")
    assert "CODEX_KIT_REVIEW_MODEL" not in uv_env
    assert "unset or unreadable" in result.stdout


def test_no_marketplace_ci_is_not_applicable(tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path / "o.json")],
        cwd=bare,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3


def test_stale_output_file_is_removed_before_the_run(repo, tmp_path):
    out = tmp_path / "out.json"
    out.write_text(json.dumps({"blocking": False}), encoding="utf-8")
    _run(repo, tmp_path)
    assert not out.exists()


def test_runs_from_a_subdirectory_of_the_checkout(repo, tmp_path):
    sub = repo / "plugins" / "x"
    sub.mkdir(parents=True)
    result, args, _ = _run(sub, tmp_path)
    assert result.returncode == 0
    assert "run-codex-review" in args


def test_variable_lookup_targets_the_origin_repository(repo, tmp_path):
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:acme/widgets.git"],
        cwd=repo,
        check=True,
    )
    _run(repo, tmp_path)
    assert "--repo acme/widgets" in (tmp_path / "uv.json.gh").read_text(encoding="utf-8")


def test_output_inside_the_checkout_is_refused(repo, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in (("uv", "exit 0"), ("gh", "exit 1"), ("codex", "echo codex-cli 0.147.0")):
        _stub(bin_dir, name, body)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(repo / "out.json")],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "inside the checkout" in result.stdout


def test_base_is_printed_and_a_missing_origin_only_warns(repo, tmp_path):
    result, _, _ = _run(repo, tmp_path)
    assert result.returncode == 0
    assert "could not fetch origin/main" in result.stdout
    assert "PARITY: base " in result.stdout


def test_origin_main_is_fetched_before_the_merge_base(repo, tmp_path):
    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return done.stdout.strip()

    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    git("remote", "add", "origin", str(bare))
    git("push", "-q", "origin", "HEAD:refs/heads/main")
    stale = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", stale)
    git("commit", "-q", "--allow-empty", "-m", "newer")
    git("push", "-q", "origin", "HEAD:refs/heads/main")
    newer = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", stale)  # make the local ref stale again
    result, _, _ = _run(repo, tmp_path)
    assert result.returncode == 0
    assert "could not fetch" not in result.stdout
    assert git("rev-parse", "origin/main") == newer
