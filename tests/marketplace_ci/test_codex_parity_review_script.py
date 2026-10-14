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
          CODEX_KIT_REVIEW_TIMEOUT_MS: ${{ vars.CODEX_KIT_REVIEW_TIMEOUT_MS || '600000' }}
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


def test_windows_timeout_kills_the_tree_and_does_not_wait_forever(monkeypatch):
    # A descendant that keeps the pipes open must not turn the post-kill drain into a hang.
    import types

    module = _load_module()
    calls = []

    class FakeProc:
        pid = 4242

        def communicate(self, timeout: float | None = None):
            calls.append(("communicate", timeout))
            raise subprocess.TimeoutExpired("uv", timeout or 0)

        def kill(self):
            calls.append(("kill",))

    monkeypatch.setattr(module, "os", types.SimpleNamespace(name="nt"))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: FakeProc())
    monkeypatch.setattr(module, "_run", lambda argv, **k: calls.append(tuple(argv)))
    assert module._run_in_group(["uv"], env={}, timeout=1) is None
    assert ("taskkill", "/F", "/T", "/PID", "4242") in calls
    assert ("kill",) in calls
    drains = [c for c in calls if c[0] == "communicate"]
    assert len(drains) == 2 and drains[1][1] is not None  # the second drain is bounded


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
    timeout_var: str = "",
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
        # The selector names the variable asked for; answer the timeout one separately.
        'case "$*" in *CODEX_KIT_REVIEW_TIMEOUT_MS*)\n'
        f'  [ -n "{timeout_var}" ] && echo "{timeout_var}"; exit 0;;\nesac\n'
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
def test_origin_main_is_fetched_before_the_base_is_taken(repo, tmp_path, default_refspec):
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


def test_instruction_files_are_redirected_beside_the_output_not_into_the_checkout(repo, tmp_path):
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 0
    assert f"--instructions-dir {tmp_path}/out-instructions" in args
    assert not (repo / ".codex-review-instructions").exists()


def test_a_symlink_output_is_refused_and_its_target_survives(repo, tmp_path):
    target = tmp_path / "precious.json"
    target.write_text(
        '{"mode": "delta", "blocking": false, "owner": "someone else"}', encoding="utf-8"
    )
    (tmp_path / "out.json").symlink_to(target)
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 2
    # Match the wrapper's own words: the printed path also contains this test's name (and so the
    # word "symlink"), which would make a bare substring check pass for the wrong reason.
    assert "--output is a symlink" in result.stdout
    assert "already exists" not in result.stdout
    assert target.exists()
    assert (tmp_path / "out.json").is_symlink()
    assert args == ""


def test_the_instructions_path_never_equals_an_extensionless_output(repo, tmp_path):
    # An --output already named "*-instructions" must not collide with the derived directory.
    result, args, _ = _run(repo, tmp_path, output_name="review-instructions")
    assert result.returncode == 0
    assert f"--instructions-dir {tmp_path}/review-instructions-instructions" in args
    assert f"--output {tmp_path}/review-instructions" in args


@pytest.mark.parametrize("kind", ["dir", "symlink", "dangling_symlink"])
def test_a_pre_existing_instructions_path_is_refused_and_left_untouched(repo, tmp_path, kind):
    instructions = tmp_path / "out-instructions"
    victim = tmp_path / "victim"
    victim.mkdir()
    if kind == "dir":
        instructions.mkdir()
    elif kind == "symlink":
        instructions.symlink_to(victim, target_is_directory=True)
    else:
        instructions.symlink_to(tmp_path / "missing")
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 2
    assert "already exists" in result.stdout
    assert args == ""
    assert instructions.is_symlink() or instructions.is_dir()
    assert list(victim.iterdir()) == []


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


def test_parse_ci_settings_reads_the_real_workflow():
    # The wrapper depends on two step names in the real workflow; a rename must fail here, not
    # silently turn every run into "could not read the timeout and Codex pin".
    root = Path(__file__).resolve().parents[2]
    text = (root / ".github/workflows/marketplace-ci.yml").read_text("utf-8")
    settings = _load_module().parse_ci_settings(text)
    assert settings is not None
    timeout_ms, pin = settings
    assert timeout_ms.isdigit()
    assert pin.count(".") == 2


def test_a_missing_output_directory_is_refused_before_dispatching(repo, tmp_path):
    result, args, _ = _run(repo, tmp_path, output_name="not-created/out.json")
    assert result.returncode == 2
    assert "missing or not writable" in result.stdout
    assert args == ""  # nothing was dispatched, so no expensive run was wasted


def test_an_output_directory_that_is_a_file_is_refused(repo, tmp_path):
    (tmp_path / "plain-file").write_text("x", encoding="utf-8")
    result, args, _ = _run(repo, tmp_path, output_name="plain-file/out.json")
    assert result.returncode == 2
    assert args == ""


def test_base_sha_is_the_origin_main_tip_not_the_merge_base(repo, tmp_path):
    # CI passes base.sha (main's tip); the entry point reads reviewer TOMLs from exactly that SHA.
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
    fork_point = git("rev-parse", "HEAD")
    _commit_files(repo, {"main-moved.txt": "x"})
    tip = git("rev-parse", "HEAD")
    git("push", "-q", "origin", "HEAD:refs/heads/main")
    git("reset", "-q", "--hard", fork_point)
    git("update-ref", "refs/remotes/origin/main", fork_point)  # stale local ref
    _commit_files(repo, {"branch-work.txt": "y"})  # the branch diverges from the new main tip
    assert git("merge-base", tip, "HEAD") == fork_point != tip
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 0
    assert f"--base-sha {tip}" in args
    assert fork_point not in args


@pytest.mark.parametrize(
    "tier1_source",
    ["TIER1_FILES = frozenset({1, 'a'})\n", "TIER1_FILES = frozenset({[1]})\n"],
    ids=["mixed-types", "unhashable-element"],
)
def test_a_malformed_tier1_list_only_warns(repo, tmp_path, tier1_source):
    _commit_files(repo, {"scripts/marketplace_ci/trust_boundary.py": tier1_source})
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=repo, check=True)
    result, args, _ = _run(repo, tmp_path)
    assert result.returncode == 0
    assert "could not check whether review-dispatch files changed" in result.stdout
    assert args  # the run still happened


@pytest.mark.parametrize("root", ["plugins/git-kit", ".claude"])
def test_the_script_and_its_mirror_are_executable(root):
    # create-pr's grants name this script by path; plugin-rulebook R37 wants it committed as 100755.
    copy = SCRIPT.parents[3] / root / "scripts" / SCRIPT.name
    assert os.access(copy, os.X_OK), f"{copy} is not executable"


def test_parse_ci_settings_reads_the_fallback_from_the_variable_expression():
    # The workflow takes the repository variable and falls back to a literal; the wrapper
    # needs that literal, and must keep working when only the literal form is present.
    module = _load_module()
    assert "vars.CODEX_KIT_REVIEW_TIMEOUT_MS ||" in WORKFLOW
    assert module.parse_ci_settings(WORKFLOW) == ("600000", "0.147.0")
    legacy = WORKFLOW.replace("${{ vars.CODEX_KIT_REVIEW_TIMEOUT_MS || '600000' }}", '"600000"')
    assert module.parse_ci_settings(legacy) == ("600000", "0.147.0")


def test_the_timeout_repository_variable_overrides_the_workflow_fallback(repo, tmp_path):
    result, _, uv_env = _run(repo, tmp_path, timeout_var="720000")
    assert result.returncode == 0
    assert "CODEX_KIT_REVIEW_TIMEOUT_MS=720000" in uv_env
    assert "CODEX_KIT_REVIEW_TIMEOUT_MS=600000" not in uv_env
    assert "720000" in result.stdout


def test_an_unset_timeout_variable_falls_back_to_the_workflow_literal(repo, tmp_path):
    result, _, uv_env = _run(repo, tmp_path, timeout_var="")
    assert result.returncode == 0
    assert "CODEX_KIT_REVIEW_TIMEOUT_MS=600000" in uv_env


@pytest.mark.parametrize("value", ["abc", "0", "-5", "720000;rm", "7 2", "1" * 12])
def test_a_malformed_timeout_variable_falls_back_instead_of_being_passed_on(repo, tmp_path, value):
    result, _, uv_env = _run(repo, tmp_path, timeout_var=value)
    assert result.returncode == 0
    assert "CODEX_KIT_REVIEW_TIMEOUT_MS=600000" in uv_env
    assert f"CODEX_KIT_REVIEW_TIMEOUT_MS={value}" not in uv_env


def test_the_real_workflow_takes_the_timeout_from_the_repository_variable():
    root = Path(__file__).resolve().parents[2]
    text = (root / ".github/workflows/marketplace-ci.yml").read_text("utf-8")
    assert (
        "CODEX_KIT_REVIEW_TIMEOUT_MS: ${{ vars.CODEX_KIT_REVIEW_TIMEOUT_MS || '600000' }}" in text
    )
    assert 'CODEX_KIT_REVIEW_TIMEOUT_MS: "600000"' not in text
