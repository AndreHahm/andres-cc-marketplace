"""Shared fixtures and factories for scripts.marketplace_ci tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci.git_state import ChangedPath
from scripts.marketplace_ci.registry import Registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class GitRepoHelper:
    """Thin wrapper around a real, temporary Git repository used by tests."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, rel_path: str, content: str) -> Path:
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def stage(self, rel_path: str, content: str) -> Path:
        path = self.write(rel_path, content)
        subprocess.run(["git", "add", rel_path], cwd=self.root, check=True, capture_output=True)
        return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An isolated repo root, seeded with any committed plugin fixtures on disk."""
    fixture_plugins = FIXTURES_DIR / "plugins"
    if fixture_plugins.is_dir():
        shutil.copytree(fixture_plugins, tmp_path / "plugins")
    return tmp_path


@pytest.fixture
def git_repo(repo: Path) -> GitRepoHelper:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return GitRepoHelper(repo)


@pytest.fixture
def hook_repo(git_repo: GitRepoHelper) -> GitRepoHelper:
    return git_repo


@pytest.fixture
def registry_for():
    def _factory(*plugin_mirror_names: str) -> Registry:
        return Registry(version=1, plugin_mirrors=tuple(plugin_mirror_names), skills=(), agents=())

    return _factory


@pytest.fixture
def change():
    def _factory(path: str, status: str = "M") -> ChangedPath:
        if status == "A":
            return ChangedPath(status="A", old_path=None, new_path=path)
        if status == "D":
            return ChangedPath(status="D", old_path=path, new_path=None)
        return ChangedPath(status=status, old_path=path, new_path=path)

    return _factory


@pytest.fixture
def dependency_index():
    """Placeholder factory; Task 9's review-scope work gives this a real structure."""

    def _factory() -> dict:
        return {}

    return _factory


@pytest.fixture
def label_event():
    """Placeholder factory; Task 11's bypass-attestation work gives this a real structure."""

    def _factory(actor: str, sha: str) -> dict:
        return {"actor": actor, "sha": sha}

    return _factory


@pytest.fixture
def attestation():
    """Placeholder factory; Task 11's bypass-attestation work gives this a real structure."""

    def _factory(actor: str, sha: str, reason: str) -> dict:
        return {"actor": actor, "sha": sha, "reason": reason}

    return _factory


@pytest.fixture
def completed():
    def _factory(
        returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )

    return _factory
