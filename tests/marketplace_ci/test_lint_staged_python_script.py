"""git-kit's git-lint-staged-python.sh must never auto-format or type-check generated mirrors.

In a marketplace-CI repo (`.claude/marketplace-sync.json` present), `.claude/`, `.agents/` and
`.codex/` hold generated copies of canonical sources. Reformatting one in place silently breaks
byte-parity with its source, and `check-all --staged` does not catch it when the source itself is
not staged (issue #446 follow-up). A stub `uv` on PATH records which files the script hands to
ruff/ty, so these tests need neither network access nor ruff.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-lint-staged-python.sh"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="bash script exercised through a POSIX PATH stub"
)


def _stage(repo: Path, rel_path: str, text: str = "x = 1\n") -> None:
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-f", rel_path], cwd=repo, check=True, capture_output=True)


def _run_script(repo: Path, tmp_path: Path) -> tuple[subprocess.CompletedProcess, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "uv-calls.log"
    stub = bin_dir / "uv"
    stub.write_text('#!/bin/sh\necho "$@" >> "$UV_LOG"\nexit 0\n', encoding="utf-8")
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "UV_LOG": str(log)}
    result = subprocess.run(
        ["bash", str(SCRIPT)], cwd=repo, env=env, capture_output=True, text=True, check=False
    )
    return result, log.read_text(encoding="utf-8") if log.exists() else ""


@pytest.fixture
def work_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    # This repo's own .gitignore carries the same negations: some machines' global gitignore
    # excludes these directory names everywhere, which would make the script's plain `git add`
    # fail here for a reason unrelated to what these tests check.
    (repo / ".gitignore").write_text("!.claude/\n!.agents/\n!.codex/\n", encoding="utf-8")
    return repo


def test_generated_mirrors_are_not_handed_to_ruff_or_ty_in_a_marketplace_repo(work_repo, tmp_path):
    (work_repo / ".claude").mkdir()
    (work_repo / ".claude" / "marketplace-sync.json").write_text("{}", encoding="utf-8")
    _stage(work_repo, "scripts/real.py")
    _stage(work_repo, ".claude/scripts/mirrored.py")
    _stage(work_repo, ".agents/skills/demo/exported.py")
    _stage(work_repo, ".codex/exported.py")

    result, calls = _run_script(work_repo, tmp_path)

    assert result.returncode == 0
    assert "scripts/real.py" in calls
    assert "mirrored.py" not in calls
    assert "exported.py" not in calls


def test_only_mirrors_staged_means_no_tool_is_invoked(work_repo, tmp_path):
    (work_repo / ".claude").mkdir()
    (work_repo / ".claude" / "marketplace-sync.json").write_text("{}", encoding="utf-8")
    _stage(work_repo, ".claude/scripts/mirrored.py")

    result, calls = _run_script(work_repo, tmp_path)

    assert result.returncode == 0
    assert calls == ""


def test_claude_python_is_still_checked_in_a_repo_without_a_marketplace_registry(
    work_repo, tmp_path
):
    # git-kit is repo-agnostic: outside a marketplace-CI repo, .claude/ may hold hand-authored
    # Python, so the exclusion must stay conditional on the registry file.
    _stage(work_repo, ".claude/hooks/hand_written.py")
    _stage(work_repo, "scripts/real.py")

    result, calls = _run_script(work_repo, tmp_path)

    assert result.returncode == 0
    assert "hand_written.py" in calls
    assert "scripts/real.py" in calls
