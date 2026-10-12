"""git-kit's git-codex-parity-review.py mirrors CI's settings and never reports an unearned pass.

Stub `gh`, `codex` and `uv` executables on PATH stand in for the real tools, so these tests need
neither network access nor a Codex account (issue #540).
"""

import importlib.util
import json
import os
import shutil
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


def _result(blocking: bool = False, **overrides) -> str:
    """A completed run-codex-review result, as `_handle_run_codex_review` writes it."""
    payload = {
        "mode": "delta",
        "reviewed_paths": [],
        "reviewers": ["security-reviewer"],
        "reviewer_attempts": {},
        "structural_findings": [],
        "diff_scoped": True,
        "findings": [],
        "blocking": blocking,
    }
    return json.dumps({**payload, **overrides})


def _run(
    repo: Path,
    tmp_path: Path,
    *,
    uv_rc: int = 0,
    codex: str | None = "codex-cli 0.147.0",
    model: str = "gpt-x",
    result_json: str | None = "auto",
    uv_prelude: str = "",
    output_name: str = "out.json",
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "uv.json"
    # The stub plays run-codex-review: it writes the result file (last argument) unless told not to.
    payload = _result(uv_rc == 1) if result_json == "auto" else result_json
    write_result = (
        f"for a; do last=$a; done\nprintf '%s' '{payload}' > \"$last\"\n" if payload else ""
    )
    _stub(
        bin_dir,
        "uv",
        f'echo "$@ " > "{log}.args"\nenv > "{log}.env"\n{uv_prelude}{write_result}exit {uv_rc}',
    )
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
        [sys.executable, str(SCRIPT), "--output", str(tmp_path / output_name)],
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


def test_missing_result_file_is_never_a_clean_pass(repo, tmp_path):
    result, _, _ = _run(repo, tmp_path, result_json=None)
    assert result.returncode == 2
    assert "no valid result" in result.stdout


def test_malformed_or_non_boolean_result_is_could_not_run(repo, tmp_path):
    for bad in (
        "not json",
        "[]",
        '{"mode": "delta", "blocking": "no"}',
        "{}",
        '{"blocking": false}',
    ):
        result, _, _ = _run(repo, tmp_path, result_json=bad)
        assert result.returncode == 2, bad


def test_result_contradicting_the_exit_code_is_could_not_run(repo, tmp_path):
    clean_but_blocking, _, _ = _run(
        repo, tmp_path, uv_rc=0, result_json='{"mode": "delta", "blocking": true}'
    )
    assert clean_but_blocking.returncode == 2
    blocking_but_clean, _, _ = _run(
        repo, tmp_path, uv_rc=1, result_json='{"mode": "delta", "blocking": false}'
    )
    assert blocking_but_clean.returncode == 2


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


@pytest.mark.parametrize("default_refspec", [True, False], ids=["default-refspec", "no-refspec"])
def test_origin_main_is_fetched_before_the_merge_base(repo, tmp_path, default_refspec):
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
    if not default_refspec:
        git(
            "config", "--unset-all", "remote.origin.fetch"
        )  # a plain `fetch origin main` then skips the ref
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


def test_helper_calls_time_out_instead_of_hanging(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "_HELPER_TIMEOUT_SECONDS", 0.3)
    assert module._run(["sleep", "5"]) is None


def test_fetch_runs_with_credential_prompts_disabled(repo, tmp_path):
    real_git = shutil.which("git")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "fetch-env.log"
    _stub(
        bin_dir,
        "git",
        f'[ "$1" = fetch ] && {{ echo "$GIT_TERMINAL_PROMPT" > "{log}"; exit 0; }}\n'
        f'exec "{real_git}" "$@"',
    )
    result, _, _ = _run(repo, tmp_path)
    assert result.returncode == 0
    assert log.read_text(encoding="utf-8").strip() == "0"


TRUST_BOUNDARY_SRC = (
    "TIER1_FILES = frozenset(\n    {\n        'pyproject.toml',\n"
    "        'scripts/marketplace_ci/review.py',\n    }\n)\n"
)


def _commit_files(repo: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _make_base(repo: Path) -> None:
    _commit_files(repo, {"scripts/marketplace_ci/trust_boundary.py": TRUST_BOUNDARY_SRC})
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=repo, check=True)


def test_tier1_change_warns_but_still_runs(repo, tmp_path):
    _make_base(repo)
    _commit_files(repo, {"pyproject.toml": "x\n", "README.md": "y\n"})
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 0
    assert "review-dispatch-critical files (pyproject.toml)" in result.stdout
    assert args  # the run still happened


def test_no_tier1_change_means_no_warning(repo, tmp_path):
    _make_base(repo)
    _commit_files(repo, {"README.md": "y\n"})
    result, _, _ = _run(repo, tmp_path)
    assert "review-dispatch-critical" not in result.stdout
    assert "could not check" not in result.stdout


def test_tier1_list_comes_from_the_base_copy_not_the_branch(repo, tmp_path):
    _make_base(repo)
    # The branch empties TIER1_FILES and changes a Tier-1 file; the base list must still win.
    _commit_files(
        repo,
        {
            "scripts/marketplace_ci/trust_boundary.py": "TIER1_FILES = frozenset({'zzz'})\n",
            "pyproject.toml": "x\n",
        },
    )
    result, _, _ = _run(repo, tmp_path)
    assert "(pyproject.toml)" in result.stdout


def test_unreadable_base_trust_boundary_warns(repo, tmp_path):
    result, _, _ = _run(repo, tmp_path)  # the fixture's base has no trust_boundary.py
    assert result.returncode == 0
    assert "could not check whether review-dispatch files changed" in result.stdout


def test_an_output_path_that_is_a_directory_is_refused(repo, tmp_path):
    (tmp_path / "out.json").mkdir()
    result, _, _ = _run(repo, tmp_path)
    assert result.returncode == 2
    assert (tmp_path / "out.json").is_dir()


SCRATCH_STUB = "mkdir -p .codex-review-instructions && echo x > .codex-review-instructions/a.txt\n"


def test_scratch_dir_created_by_the_run_is_removed(repo, tmp_path):
    result, _, _ = _run(repo, tmp_path, uv_prelude=SCRATCH_STUB)
    assert result.returncode == 0
    assert not (repo / ".codex-review-instructions").exists()


def test_a_pre_existing_scratch_dir_is_left_alone(repo, tmp_path):
    (repo / ".codex-review-instructions").mkdir()
    (repo / ".codex-review-instructions" / "mine.txt").write_text("x", encoding="utf-8")
    result, _, _ = _run(repo, tmp_path, uv_prelude=SCRATCH_STUB)
    assert result.returncode == 0
    assert (repo / ".codex-review-instructions" / "mine.txt").exists()


def test_a_symlink_output_is_refused_and_its_target_survives(repo, tmp_path):
    target = tmp_path / "precious.json"
    target.write_text(
        '{"mode": "delta", "blocking": false, "owner": "someone else"}', encoding="utf-8"
    )
    (tmp_path / "out.json").symlink_to(target)
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 2
    assert "symlink" in result.stdout
    assert target.exists()
    assert (tmp_path / "out.json").is_symlink()
    assert args == ""


def test_the_scratch_dir_name_matches_the_ci_entry_point_and_gitignore():
    # The wrapper's cleanup and the .gitignore entry duplicate a default in review.py; a rename
    # there must fail here instead of silently bringing the stray directory back.
    root = Path(__file__).resolve().parents[2]
    name = str(_load_module().INSTRUCTIONS_DIR)
    assert f'repo / "{name}"' in (root / "scripts/marketplace_ci/review.py").read_text("utf-8")
    assert f"{name}/" in (root / ".gitignore").read_text("utf-8").splitlines()


@pytest.mark.parametrize("model", ["a/b", "a:b", "m" * 65])
def test_a_model_the_bridge_would_reject_falls_back_instead_of_failing(repo, tmp_path, model):
    result, _, uv_env = _run(repo, tmp_path, model=model)
    assert result.returncode == 0
    assert "unset or unreadable" in result.stdout
    assert "CODEX_KIT_REVIEW_MODEL" not in uv_env


def test_a_model_the_bridge_accepts_is_passed_on(repo, tmp_path):
    _, _, uv_env = _run(repo, tmp_path, model="gpt-6.1_luna-2")
    assert "CODEX_KIT_REVIEW_MODEL=gpt-6.1_luna-2" in uv_env


def test_the_model_pattern_matches_the_bridges_own():
    root = Path(__file__).resolve().parents[2]
    bridge = root / "plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs"
    pattern = _load_module()._MODEL_RE.pattern
    assert pattern in bridge.read_text("utf-8")  # a change on either side must fail here


@pytest.mark.parametrize(
    "content",
    ["keep me", _result(False), '{"blocking": true, "error": "x"}', '{"blocking": false, "o": 1}'],
    ids=["text", "previous-result", "failure-payload", "unrelated-json"],
)
def test_any_pre_existing_output_is_refused_and_left_untouched(repo, tmp_path, content):
    existing = tmp_path / "out.json"
    existing.write_text(content, encoding="utf-8")
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 2
    assert "already exists" in result.stdout
    assert existing.read_text(encoding="utf-8") == content
    assert args == ""  # refused before dispatching anything


def test_a_retry_after_a_failed_run_uses_a_fresh_output_path(repo, tmp_path):
    failed, _, _ = _run(
        repo, tmp_path, uv_rc=2, result_json='{"blocking": true, "error": "could not resolve base"}'
    )
    assert failed.returncode == 2
    retry, args, _ = _run(repo, tmp_path, output_name="out-2.json")
    assert retry.returncode == 0
    assert args  # the retry actually dispatched
    assert (tmp_path / "out.json").exists()  # the earlier file was never touched


def test_a_completed_run_that_only_wrote_an_error_payload_is_could_not_run(repo, tmp_path):
    result, _, _ = _run(repo, tmp_path, result_json='{"blocking": false, "error": "x"}')
    assert result.returncode == 2


def test_the_required_result_keys_are_still_written_by_the_entry_point():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts/marketplace_ci/__main__.py").read_text("utf-8")
    module = _load_module()
    for key in ("mode", "blocking", *module._RESULT_LIST_KEYS):
        assert f'"{key}":' in source, key
