"""git-kit's git-review-codex-kit.py runs only an installed codex-kit, never the repo's (#697)."""

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-review-codex-kit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("git_review_codex_kit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _codex_kit(root: Path, marker: str = "installed") -> Path:
    bridge = root / mod.BRIDGE
    bridge.parent.mkdir(parents=True)
    bridge.write_text(
        f"console.log({json.dumps(marker)}, process.argv.slice(2).join(' '), "
        "process.env.NODE_OPTIONS, process.env.GIT_INDEX_FILE);\nprocess.exit(7);\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A repository as the working directory, and a fake account home."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    home = tmp_path / "home"
    (home / ".claude/plugins").mkdir(parents=True)
    monkeypatch.setattr(mod, "_home", lambda: home)
    monkeypatch.chdir(repo)

    def register(*paths, key=mod.REGISTRY_KEY):
        entries = [{"installPath": str(p)} for p in paths]
        registry = home / ".claude/plugins/installed_plugins.json"
        registry.write_text(json.dumps({"plugins": {key: entries}}), encoding="utf-8")

    return repo, tmp_path, register


def test_the_installed_copy_is_found(env):
    _repo, tmp, register = env
    root = _codex_kit(tmp / "cache/codex-kit/1")
    register(root, root)  # the same root in two install scopes is one root
    assert mod.locate()[0] == root.resolve()


@pytest.mark.skipif(os.name == "nt", reason="uses a shell script as the planted program")
def test_a_git_or_node_from_the_repository_is_never_run(env, monkeypatch):
    repo, tmp, register = env
    register(_codex_kit(tmp / "cache"))
    for name in ("git", "node"):
        planted = repo / name
        planted.write_text("#!/bin/sh\ntouch ran\n", encoding="utf-8")
        planted.chmod(0o755)
    real = os.environ["PATH"]
    monkeypatch.setenv("PATH", os.pathsep.join(["", ".", real]))  # relative entries are skipped
    mod.locate()
    monkeypatch.setenv("PATH", os.pathsep.join([str(repo), real]))
    with pytest.raises(FileNotFoundError, match="git on PATH lies inside"):
        mod.locate()
    with pytest.raises(FileNotFoundError, match="node on PATH lies inside"):
        mod.common.tool("node", mod.common.checkout_root(repo))
    assert not (repo / "ran").exists()


@pytest.mark.parametrize("registered", ["none", "two", "relative", "gone", "other-marketplace"])
def test_no_single_installed_copy_is_refused(env, registered):
    _repo, tmp, register = env
    a, b = _codex_kit(tmp / "a"), _codex_kit(tmp / "b")
    paths = {"none": [], "two": [a, b], "relative": ["a"], "gone": [tmp / "c"]}
    key = "codex-kit@elsewhere" if registered == "other-marketplace" else mod.REGISTRY_KEY
    register(*paths.get(registered, [a]), key=key)
    with pytest.raises(mod.Unavailable):
        mod.locate()


@pytest.mark.parametrize("text", ["", "[]", "{}", '{"plugins": []}', '{"plugins": {"%s": [1]}}'])
def test_a_bad_registry_is_refused(env, text):
    _repo, tmp, _register = env
    registry = tmp / "home/.claude/plugins/installed_plugins.json"
    registry.write_text(text.replace("%s", mod.REGISTRY_KEY), encoding="utf-8")
    with pytest.raises(mod.Unavailable):
        mod.locate()


def test_a_copy_inside_the_reviewed_repository_is_refused(env):
    repo, _tmp, register = env
    register(_codex_kit(repo / "plugins/codex-kit"))
    with pytest.raises(mod.Unavailable, match="inside the repository"):
        mod.locate()


def test_a_copy_inside_another_worktree_is_refused(env):
    repo, tmp, register = env
    ident = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(
        ["git", *ident, "commit", "-q", "--allow-empty", "-m", "i"], cwd=repo, check=True
    )
    subprocess.run(["git", "worktree", "add", "-q", str(tmp / "wt")], cwd=repo, check=True)
    register(_codex_kit(tmp / "wt/plugins/codex-kit"))
    with pytest.raises(mod.Unavailable, match="inside the repository"):
        mod.locate()


@pytest.mark.needs_symlinks
def test_a_link_back_into_the_repository_is_refused(env):
    repo, tmp, register = env
    _codex_kit(repo / "plugins/codex-kit")
    link = tmp / "link"
    link.symlink_to(repo / "plugins/codex-kit", target_is_directory=True)
    register(link)
    with pytest.raises(mod.Unavailable, match="inside the repository"):
        mod.locate()
    installed = _codex_kit(tmp / "installed")
    (installed / mod.BRIDGE).unlink()
    (installed / mod.BRIDGE).symlink_to(repo / "plugins/codex-kit" / mod.BRIDGE)
    register(installed)
    with pytest.raises(mod.Unavailable, match="inside the repository"):
        mod.locate()


def test_outside_a_git_repository_is_refused(env, monkeypatch):
    _repo, tmp, register = env
    register(_codex_kit(tmp / "a"))
    (tmp / "plain").mkdir()
    monkeypatch.chdir(tmp / "plain")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp))
    with pytest.raises(mod.Unavailable, match="worktrees"):
        mod.locate()


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_bridge_runs_the_installed_copy_not_the_planted_one(env, monkeypatch, capfd):
    repo, tmp, register = env
    _codex_kit(repo / "plugins/codex-kit", "planted")
    register(_codex_kit(tmp / "cache"))
    monkeypatch.setenv("NODE_OPTIONS", "--require=/nonexistent.cjs")
    monkeypatch.setenv("GIT_INDEX_FILE", "/x")
    assert mod.main(["bridge", "--dispatch-id", "a b"]) == 7
    assert capfd.readouterr().out.strip() == "installed --dispatch-id a b undefined undefined"


def test_bridge_without_an_installed_copy_never_falls_back_to_the_repository(env, capfd):
    repo, _tmp, register = env
    _codex_kit(repo / "plugins/codex-kit", "planted")
    register()
    assert mod.main(["bridge"]) == 3
    out, err = capfd.readouterr()
    assert out == "" and json.loads(err)["category"] == "cli_unavailable"
    assert mod.main(["locate"]) == 3
    assert json.loads(capfd.readouterr().out)["ok"] is False


@pytest.mark.parametrize("argv", [[], ["run"], ["locate", "x"]])
def test_usage_errors(argv):
    assert mod.main(argv) == 2


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX password database")
def test_the_home_variable_cannot_pick_the_registry(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert _load_module()._home() != tmp_path


@pytest.mark.skipif(os.name == "nt" or shutil.which("node") is None, reason="needs node and POSIX")
def test_the_bridge_path_has_no_entry_from_the_repository(env, monkeypatch, capfd):
    repo, tmp, register = env
    root = _codex_kit(tmp / "cache")
    (root / mod.BRIDGE).write_text("console.log(process.env.PATH);\n", encoding="utf-8")
    register(root)
    (repo / "bin").mkdir()
    outside = tmp / "outside"
    outside.mkdir()
    (repo / "codex").write_text("#!/bin/sh\n", encoding="utf-8")
    (outside / "codex").symlink_to(repo / "codex")
    real = os.environ["PATH"]
    entries = ["", ".", "node_modules/.bin", str(repo / "bin"), str(outside), real]
    monkeypatch.setenv("PATH", os.pathsep.join(entries))
    assert mod.main(["bridge"]) == 0
    assert capfd.readouterr().out.strip() == mod.common.safe_path([repo])
    kept = mod.common.safe_path([repo]).split(os.pathsep)
    assert str(outside) not in kept and str(repo / "bin") not in kept and "." not in kept


@pytest.mark.skipif(os.name == "nt", reason="uses a shell script as the planted program")
def test_a_git_in_the_main_checkout_is_refused_from_a_linked_worktree(env, monkeypatch):
    repo, tmp, register = env
    ident = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    argv = ["git", *ident, "commit", "-q", "--allow-empty", "-m", "i"]
    subprocess.run(argv, cwd=repo, check=True)
    subprocess.run(["git", "worktree", "add", "-q", str(tmp / "wt")], cwd=repo, check=True)
    (repo / "git").write_text("#!/bin/sh\ntouch ran\n", encoding="utf-8")
    (repo / "git").chmod(0o755)
    monkeypatch.chdir(tmp / "wt")
    monkeypatch.setenv("PATH", os.pathsep.join([str(repo), os.environ["PATH"]]))
    with pytest.raises(FileNotFoundError, match="inside the repository"):
        mod.common.tool("git", mod.common.checkout_root(tmp / "wt"))
    register(_codex_kit(tmp / "cache"))
    with pytest.raises(FileNotFoundError):
        mod.locate()


def test_an_unreadable_path_entry_is_skipped(env, monkeypatch):
    repo, tmp, _register = env
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp / "gone"), os.environ["PATH"]]))
    assert mod.common.tool("git", [repo])
