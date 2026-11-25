"""The cross-model-review locator for the installed reviewadapters-kit (issue #541, Part B).

Runs the script against scratch plugin caches and scratch repositories. POSIX only: the checks
rely on file ownership and mode bits.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "git-kit"
    / "scripts"
    / "git-review-locate-rva.py"
)

pytestmark = pytest.mark.skipif(os.name != "posix", reason="ownership and mode checks are POSIX")
pwd = pytest.importorskip("pwd")


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _rva(root):
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "rva-dispatch.mjs").write_text("// fake\n")
    (root / "assets").mkdir()
    (root / "assets" / "rva-devin-config.json").write_text("{}\n")
    (root / "reviewadapters-kit.settings.json").write_text("{}\n")
    return root


def _manifest(layout, *versions, raw=None):
    """Write Claude Code's installed_plugins.json three levels above the cache's version folders."""
    path = layout["tmp"] / "installed_plugins.json"
    sibling = layout["cache"] / "reviewadapters-kit"
    entries = [{"scope": "user", "installPath": str(sibling / v), "version": v} for v in versions]
    path.write_text(
        raw
        if raw is not None
        else json.dumps({"version": 2, "plugins": {"reviewadapters-kit@mkt": entries}})
    )
    return path


def _program(folder, name, body=None):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    # the locator accepts only a native program as node
    native = name == "node" and body is None
    path.write_text("\x7fELF fake\n" if native else f"#!/bin/sh\n{body or 'exit 0'}\n")
    path.chmod(0o755)
    return path


def _install(scripts):
    """Copy the script and the module it loads by path, as an installed copy has both."""
    for source in (SCRIPT, SCRIPT.with_name("git_review_common.py")):
        if not (scripts / source.name).exists():
            shutil.copyfile(source, scripts / source.name)
    return scripts / SCRIPT.name


@pytest.fixture
def layout(tmp_path, monkeypatch):
    _program(tmp_path / "bin", "node")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    cache = tmp_path / "cache" / "mkt"
    git_kit = cache / "git-kit" / "1.0.0"
    git_kit.mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(
        repo,
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "i",
    )
    (repo / ".claude").mkdir()
    return {"cache": cache, "git_kit": git_kit, "repo": repo, "tmp": tmp_path}


def _run(layout, plugin_root=None):
    """Run a copy of the script placed in `plugin_root/scripts/`, as an installed copy runs."""
    scripts = (plugin_root or layout["git_kit"]) / "scripts"
    scripts.mkdir(exist_ok=True)
    copy = _install(scripts)
    result = subprocess.run(
        [sys.executable, str(copy), "--repo", str(layout["repo"])],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, json.loads(result.stdout)


def _config(layout, value, mode=0o600):
    path = layout["repo"] / ".claude" / "git-kit.local.json"
    path.write_text(json.dumps({"cross_model_review_rva_root": value}))
    path.chmod(mode)
    return path


def test_sibling_found(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    code, out = _run(layout)
    assert code == 0
    assert out["source"] == "sibling"
    assert out["dispatcher"] == str(root.resolve() / "scripts" / "rva-dispatch.mjs")
    assert out["node"] == str(layout["tmp"] / "bin" / "node")


@pytest.mark.parametrize("name", ["git", "node"])
@pytest.mark.parametrize("linked", [False, True])
def test_program_inside_repo_refused_and_never_run(layout, monkeypatch, name, linked):
    """A checkout's own bin/ on PATH, directly or through a link, supplies no program (PR #879)."""
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    marker = layout["tmp"] / "ran"
    program = _program(layout["repo"] / "bin", name, f"touch '{marker}'")
    folder = program.parent
    if linked:
        folder = layout["tmp"] / "linked"
        folder.mkdir()
        (folder / name).symlink_to(program)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    code, out = _run(layout)
    assert code == 3
    assert not out["ok"]
    assert not marker.exists()


def test_node_inside_another_worktree_refused(layout, monkeypatch):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    other_tree = layout["tmp"] / "other-tree"
    _git(layout["repo"], "worktree", "add", "-q", "--detach", str(other_tree))
    folder = _program(other_tree / "bin", "node").parent
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    code, out = _run(layout)
    assert code == 3
    assert any("the node on PATH lies inside" in r for r in out["reasons"])


def test_node_with_unsafe_characters_refused(layout, monkeypatch):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    folder = _program(layout["tmp"] / "bin $(id)", "node").parent
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    code, out = _run(layout)
    assert code == 3
    assert any("(node) has characters outside" in r for r in out["reasons"])


def _refused(layout, text):
    code, out = _run(layout)
    assert code == 3
    assert any(text in r for r in out["reasons"]), out


def test_node_writable_by_others_refused(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (layout["tmp"] / "bin" / "node").chmod(0o757)
    _refused(layout, "(node) is writable by others")


@pytest.mark.parametrize("sticky", [False, True])
def test_node_in_folder_writable_by_others(layout, sticky):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (layout["tmp"] / "bin").chmod(0o1777 if sticky else 0o777)
    if sticky:
        code, _ = _run(layout)
        assert code == 0
    else:
        _refused(layout, "(above node) is writable by others")


def test_node_behind_link_in_folder_writable_by_others_refused(layout):
    """The folder that holds an intermediate link counts, not only the link's two ends."""
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    real = _program(layout["tmp"] / "real", "node")
    middle = layout["tmp"] / "middle"
    middle.mkdir()
    (middle / "node").symlink_to(real)
    first = layout["tmp"] / "bin" / "node"
    first.unlink()
    first.symlink_to("../middle/node")
    code, _ = _run(layout)
    assert code == 0
    middle.chmod(0o777)
    _refused(layout, "(above node) is writable by others")


@pytest.mark.parametrize("part", ["program", "link", "folder"])
def test_node_of_another_account_refused(layout, monkeypatch, part):
    locator = _module()
    real = _program(layout["tmp"] / "real", "node")
    link = layout["tmp"] / "bin" / "node"
    link.unlink()
    link.symlink_to(real)
    assert locator.program_problem(link) is None
    foreign = {"program": real, "link": link, "folder": real.parent}[part]
    original = Path.lstat

    def lstat(self):
        st = original(self)
        if self == foreign:
            return os.stat_result((*st[:4], os.getuid() + 1, *st[5:]))
        return st

    monkeypatch.setattr(Path, "lstat", lstat)
    assert "not owned by the current user or root" in locator.program_problem(link)


@pytest.mark.parametrize("part", ["program", "folder"])
def test_group_writable_node_needs_the_private_group(layout, monkeypatch, part):
    locator = _module()
    node = layout["tmp"] / "bin" / "node"
    (node if part == "program" else node.parent).chmod(0o775)
    monkeypatch.setattr(locator, "may_have_extended_acl", lambda path: False)
    monkeypatch.setattr(locator, "private_group_gid", lambda: os.getgid())
    assert locator.program_problem(node) is None
    monkeypatch.setattr(locator, "private_group_gid", lambda: None)
    assert "writable by others" in locator.program_problem(node)


@pytest.mark.parametrize("head", ["#!/bin/sh\n", ""])
def test_node_script_shim_refused(layout, head):
    """env can run a script without `#!` through /bin/sh, so it is refused too."""
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (layout["tmp"] / "bin" / "node").write_text(f"{head}exec asdf exec node\n")
    _refused(layout, "(node) is not a native program")


@pytest.mark.parametrize("magic", ["cffaedfe", "cafebabe"])
def test_mach_o_node_accepted(layout, magic):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (layout["tmp"] / "bin" / "node").write_bytes(bytes.fromhex(magic) + b"x")
    code, out = _run(layout)
    assert code == 0, out


@pytest.mark.parametrize("place", ["repo", "other-tree", "moved-tree"])
def test_node_link_through_checkout_refused(layout, place):
    """The branch could point a link kept in a checkout at another program outside it."""
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    real = _program(layout["tmp"] / "real", "node")
    tree = layout["tmp"] / place
    if place != "repo":
        added = layout["tmp"] / "added-tree" if place == "moved-tree" else tree
        _git(layout["repo"], "worktree", "add", "-q", "--detach", str(added))
        added.rename(tree)
    (tree / "tools").mkdir()
    (tree / "tools" / "node").symlink_to(real)
    link = layout["tmp"] / "bin" / "node"
    link.unlink()
    link.symlink_to(tree / "tools" / "node")
    _refused(layout, "tools (node) lies inside the repository")


def test_node_link_to_another_program_refused(layout):
    """mise and Volta link `node` to their own program."""
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    shim = layout["tmp"] / "bin" / "node"
    shim.rename(layout["tmp"] / "volta-shim")
    shim.symlink_to(layout["tmp"] / "volta-shim")
    _refused(layout, "volta-shim, which looks like a version manager's shim")


def test_printed_node_is_resolved(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    real = _program(layout["tmp"] / "real", "node")
    link = layout["tmp"] / "bin" / "node"
    link.unlink()
    link.symlink_to(real)
    _, out = _run(layout)
    assert out["node"] == str(real)


def test_resolved_node_with_unsafe_characters_refused(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    real = _program(layout["tmp"] / "node@22", "node")
    link = layout["tmp"] / "bin" / "node"
    link.unlink()
    link.symlink_to(real)
    _refused(layout, "(node) has characters outside")


def test_git_replaceable_by_others_refused(layout):
    """The locator runs git, so another account must not be able to replace it."""
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    marker = layout["tmp"] / "ran"
    _program(layout["tmp"] / "bin", "git", f"touch '{marker}'").chmod(0o757)
    _refused(layout, "(git) is writable by others")
    assert not marker.exists()


@pytest.mark.parametrize("place", ["repo", "other-tree", "moved-tree"])
def test_git_link_through_checkout_refused(layout, place):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    tree = layout["tmp"] / place
    if place != "repo":
        added = layout["tmp"] / "added-tree" if place == "moved-tree" else tree
        _git(layout["repo"], "worktree", "add", "-q", "--detach", str(added))
        added.rename(tree)
    (tree / "tools").mkdir()
    (tree / "tools" / "git").symlink_to(shutil.which("git"))
    (layout["tmp"] / "bin" / "git").symlink_to(tree / "tools" / "git")
    _refused(layout, "(git) lies inside the repository")


def test_no_git_refused(layout, monkeypatch):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    monkeypatch.setenv("PATH", str(layout["tmp"] / "bin"))
    _refused(layout, "git was not found on PATH")


@pytest.mark.parametrize("changed", ["node", "dispatcher"])
@pytest.mark.parametrize("how", ["inode", "size", "mtime"])
def test_identity_changes_with_the_file(layout, changed, how):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    target = {
        "node": layout["tmp"] / "bin" / "node",
        "dispatcher": root / "scripts" / "rva-dispatch.mjs",
    }[changed]
    before = _run(layout)[1]
    assert _run(layout)[1]["identity"] == before["identity"]
    st = target.stat()
    if how == "inode":
        replacement = layout["tmp"] / "new"
        shutil.copy2(target, replacement)
        replacement.replace(target)
    elif how == "size":
        with target.open("ab") as handle:
            handle.write(b"x")
        os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns))
    else:
        os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    after = _run(layout)[1]
    assert (after["node"], after["dispatcher"]) == (before["node"], before["dispatcher"])
    assert after["identity"] != before["identity"]


def test_node_link_with_two_leading_slashes(layout):
    real = _program(layout["tmp"] / "real", "node")
    link = layout["tmp"] / "bin" / "node"
    link.unlink()
    link.symlink_to(f"/{real}")
    assert _module().program_problem(link) is None


def test_node_link_loop_and_folder_refused(layout):
    locator = _module()
    loop = layout["tmp"] / "loop"
    loop.symlink_to(loop)
    assert "too many links" in locator.program_problem(loop)
    assert "not a regular file" in locator.program_problem(layout["tmp"] / "bin")


def test_relative_path_entry_skipped(layout, monkeypatch):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    _program(layout["repo"] / "bin", "node")
    monkeypatch.setenv("PATH", f"bin{os.pathsep}{os.environ['PATH']}")
    monkeypatch.chdir(layout["repo"])
    code, out = _run(layout)
    assert code == 0
    assert out["node"] == str(layout["tmp"] / "bin" / "node")


def test_two_sibling_versions_fall_back_to_config(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    _rva(layout["cache"] / "reviewadapters-kit" / "0.2.0")
    other = _rva(layout["tmp"] / "elsewhere")
    _config(layout, str(other))
    code, out = _run(layout)
    assert code == 0
    assert out["source"] == "config"
    assert any("expected one installed" in n for n in out["notes"])


def test_nothing_found(layout):
    code, out = _run(layout)
    assert code == 3
    assert not out["ok"]
    assert len(out["reasons"]) == 2


def test_deeply_nested_config_refused(layout):
    """A nested document under the size limit makes json.loads recurse too deep (PR #804 review)."""
    path = layout["repo"] / ".claude" / "git-kit.local.json"
    path.write_text("[" * 100_000 + "]" * 100_000)
    path.chmod(0o600)
    code, out = _run(layout)
    assert code == 3
    assert any("git-kit.local.json is not valid JSON" in r for r in out["reasons"])


def test_config_inside_repo_refused(layout):
    inside = _rva(layout["repo"] / "plugins" / "reviewadapters-kit")
    _config(layout, str(inside))
    code, out = _run(layout)
    assert code == 3
    assert any("inside the repository" in r for r in out["reasons"])


def test_config_symlink_into_repo_refused(layout):
    inside = _rva(layout["repo"] / "vendored")
    link = layout["tmp"] / "link"
    link.symlink_to(inside)
    _config(layout, str(link))
    code, out = _run(layout)
    assert code == 3
    assert any("inside the repository" in r for r in out["reasons"])


def test_relative_config_path_refused(layout):
    _config(layout, "relative/rva")
    code, out = _run(layout)
    assert code == 3
    assert any("not an absolute path" in r for r in out["reasons"])


def test_tracked_config_refused(layout):
    other = _rva(layout["tmp"] / "elsewhere")
    _config(layout, str(other))
    _git(layout["repo"], "add", "-f", ".claude/git-kit.local.json")
    code, out = _run(layout)
    assert code == 3
    assert any("tracked by git" in r for r in out["reasons"])


def test_case_variant_tracked_refused(layout):
    other = _rva(layout["tmp"] / "elsewhere")
    variant = layout["repo"] / ".claude" / "Git-Kit.local.json"
    variant.write_text("{}")
    _git(layout["repo"], "add", "-f", ".claude/Git-Kit.local.json")
    variant.unlink()
    _config(layout, str(other))
    code, out = _run(layout)
    assert code == 3
    assert any("tracked by git" in r for r in out["reasons"])


def test_world_writable_config_refused(layout):
    other = _rva(layout["tmp"] / "elsewhere")
    _config(layout, str(other), mode=0o666)
    code, out = _run(layout)
    assert code == 3
    assert any("writable by others" in r for r in out["reasons"])


def test_symlinked_config_refused(layout):
    other = _rva(layout["tmp"] / "elsewhere")
    real = layout["tmp"] / "real.json"
    real.write_text(json.dumps({"cross_model_review_rva_root": str(other)}))
    (layout["repo"] / ".claude" / "git-kit.local.json").symlink_to(real)
    code, out = _run(layout)
    assert code == 3
    assert any("symbolic link" in r for r in out["reasons"])


def _module():
    spec = importlib.util.spec_from_file_location("git_review_locate_rva", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_group_writable_dispatcher_refused_without_private_group(layout, monkeypatch):
    locator = _module()
    monkeypatch.setattr(locator, "private_group_gid", lambda: None)
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    for path in (root, root / "scripts"):
        path.chmod(0o755)
    (root / "scripts" / "rva-dispatch.mjs").chmod(0o664)
    assert "writable by others" in locator.check_root(root, layout["repo"].resolve())[1]


def test_group_writable_accepted_for_private_group(layout, monkeypatch):
    locator = _module()
    monkeypatch.setattr(locator, "private_group_gid", lambda: os.getgid())
    monkeypatch.setattr(locator, "may_have_extended_acl", lambda path: False)
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (root / "scripts" / "rva-dispatch.mjs").chmod(0o664)
    assert locator.check_root(root, layout["repo"].resolve())[1] is None


def test_group_writable_refused_with_extended_acl(layout, monkeypatch):
    locator = _module()
    monkeypatch.setattr(locator, "private_group_gid", lambda: os.getgid())
    monkeypatch.setattr(locator, "may_have_extended_acl", lambda path: True)
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (root / "scripts" / "rva-dispatch.mjs").chmod(0o664)
    assert "writable by others" in locator.check_root(root, layout["repo"].resolve())[1]


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="the exception is Linux only")
@pytest.mark.parametrize(
    ("passwd_extra", "group_lines", "private"),
    [
        ("", ["{user}:x:{gid}:"], True),
        ("", ["{user}:x:{gid}:someone"], False),
        ("", ["other:x:{gid}:"], False),
        ("", ["{user}:x:{gid}:", "dup:x:{gid}:"], False),
        ("other:x:9999:{gid}::/:/bin/sh\n", ["{user}:x:{gid}:"], False),
        ("", [], False),
    ],
)
def test_private_group_gid(tmp_path, passwd_extra, group_lines, private):
    locator = _module()
    user = pwd.getpwuid(os.getuid()).pw_name
    gid = os.getgid()
    passwd = tmp_path / "passwd"
    passwd.write_text(f"{user}:x:{os.getuid()}:{gid}::/:/bin/sh\n" + passwd_extra.format(gid=gid))
    group = tmp_path / "group"
    group.write_text("".join(line.format(user=user, gid=gid) + "\n" for line in group_lines))
    expected = gid if private else None
    assert locator.private_group_gid(str(passwd), str(group)) == expected


def test_symlinked_dispatcher_refused(layout):
    root = layout["cache"] / "reviewadapters-kit" / "0.1.0"
    (root / "scripts").mkdir(parents=True)
    target = layout["tmp"] / "evil.mjs"
    target.write_text("// evil\n")
    (root / "scripts" / "rva-dispatch.mjs").symlink_to(target)
    code, out = _run(layout)
    assert code == 3
    assert any("symbolic link" in r for r in out["reasons"])


def test_missing_dispatcher_refused(layout):
    (layout["cache"] / "reviewadapters-kit" / "0.1.0" / "scripts").mkdir(parents=True)
    code, out = _run(layout)
    assert code == 3
    assert any("is missing" in r for r in out["reasons"])


def test_plugin_root_outside_cache_skips_sibling(layout):
    mirror = layout["tmp"] / "checkout" / ".claude"
    mirror.mkdir(parents=True)
    _rva(layout["tmp"] / "checkout" / "reviewadapters-kit")
    code, out = _run(layout, plugin_root=mirror)
    assert code == 3
    assert any("does not run from a plugin cache" in r for r in out["reasons"])


def test_relative_repo_is_usage_error(layout):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", "repo"],
        capture_output=True,
        text=True,
        check=False,
        cwd=layout["tmp"],
    )
    assert result.returncode == 2


def test_symlinked_sibling_module_refused(layout):
    """Node imports the dispatcher's siblings, so a symlinked one is refused (review finding M1)."""
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    target = layout["repo"] / "rva-config.mjs"
    target.write_text("// branch code\n")
    (root / "scripts" / "rva-config.mjs").symlink_to(target)
    code, out = _run(layout)
    assert code == 3
    assert any("rva-config.mjs is a symbolic link" in r for r in out["reasons"])


def test_world_writable_sibling_module_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    module = root / "scripts" / "rva-run.mjs"
    module.write_text("// x\n")
    module.chmod(0o666)
    code, out = _run(layout)
    assert code == 3
    assert any("rva-run.mjs is writable by others" in r for r in out["reasons"])


@pytest.mark.parametrize("top", ["scripts", "assets"])
@pytest.mark.parametrize("kind", ["plain", "writable", "symlink", "hard link", "folder"])
def test_nested_entry_is_checked(layout, top, kind):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    nested = root / top / "a" / "b"
    nested.mkdir(parents=True)
    entry = nested / "x.mjs"
    entry.write_text("// x\n")
    if kind == "writable":
        entry.chmod(0o666)
    elif kind == "symlink":
        (nested / "y.mjs").symlink_to(entry)
    elif kind == "hard link":
        os.link(entry, layout["tmp"] / "other.mjs")
    elif kind == "folder":
        nested.chmod(0o777)
    if kind == "plain":
        code, out = _run(layout)
        assert code == 0, out
    else:
        _refused(layout, str(nested))


def test_hard_linked_dispatcher_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    os.link(root / "scripts" / "rva-dispatch.mjs", layout["tmp"] / "other-link.mjs")
    code, out = _run(layout)
    assert code == 3
    assert any("more than one hard link" in r for r in out["reasons"])


def test_writable_ancestor_without_sticky_refused(layout):
    """Another account could swap the root after the check (review finding M2)."""
    shared = layout["tmp"] / "shared"
    other = _rva(shared / "rva")
    shared.chmod(0o777)
    _config(layout, str(other))
    try:
        code, out = _run(layout)
    finally:
        shared.chmod(0o755)
    assert code == 3
    assert any("above the root) is writable by others" in r for r in out["reasons"])


def test_writable_ancestor_with_sticky_accepted(layout):
    shared = layout["tmp"] / "sticky"
    other = _rva(shared / "rva")
    shared.chmod(0o1777)
    _config(layout, str(other))
    try:
        code, out = _run(layout)
    finally:
        shared.chmod(0o755)
    assert code == 0
    assert out["source"] == "config"


def test_root_inside_another_worktree_refused(layout):
    other_tree = layout["tmp"] / "other-tree"
    _git(layout["repo"], "worktree", "add", "-q", "--detach", str(other_tree))
    inside = _rva(other_tree / "plugins" / "reviewadapters-kit")
    _config(layout, str(inside))
    code, out = _run(layout)
    assert code == 3
    assert any("one of its worktrees" in r for r in out["reasons"])


def test_root_inside_moved_worktree_refused(layout):
    added, moved = layout["tmp"] / "added-tree", layout["tmp"] / "moved-tree"
    _git(layout["repo"], "worktree", "add", "-q", "--detach", str(added))
    added.rename(moved)
    _config(layout, str(_rva(moved / "rva")))
    _refused(layout, "lies inside the repository under review or one of its worktrees")


def test_unsafe_characters_refused(layout):
    other = _rva(layout["tmp"] / "rva $(id)")
    _config(layout, str(other))
    code, out = _run(layout)
    assert code == 3
    assert any("characters outside" in r for r in out["reasons"])


def test_inherited_git_dir_ignored(layout):
    """A GIT_DIR from the caller must not redirect the tracked check (review finding m6)."""
    other = _rva(layout["tmp"] / "elsewhere")
    _config(layout, str(other))
    _git(layout["repo"], "add", "-f", ".claude/git-kit.local.json")
    decoy = layout["tmp"] / "decoy"
    decoy.mkdir()
    _git(decoy, "init", "-q")
    scripts = layout["git_kit"] / "scripts"
    scripts.mkdir(exist_ok=True)
    _install(scripts)
    env = {
        **os.environ,
        "GIT_DIR": str(decoy / ".git"),
        "GIT_INDEX_FILE": str(decoy / ".git" / "index"),
    }
    result = subprocess.run(
        [sys.executable, str(scripts / SCRIPT.name), "--repo", str(layout["repo"])],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 3
    assert "tracked by git" in result.stdout


def test_printed_path_is_the_checked_real_path(layout):
    other = _rva(layout["tmp"] / "real-rva")
    link = layout["tmp"] / "via-link"
    link.symlink_to(other)
    _config(layout, str(link))
    code, out = _run(layout)
    assert code == 0
    assert out["root"] == str(other.resolve())


def test_symlinked_devin_config_refused(layout):
    """Devin's adapter copies assets/ unchecked, so a link into the checkout is refused."""
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    target = layout["repo"] / "devin-config.json"
    target.write_text('{"permissions": {}}\n')
    config = root / "assets" / "rva-devin-config.json"
    config.unlink()
    config.symlink_to(target)
    code, out = _run(layout)
    assert code == 3
    assert any("rva-devin-config.json is a symbolic link" in r for r in out["reasons"])


def test_world_writable_devin_config_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (root / "assets" / "rva-devin-config.json").chmod(0o666)
    code, out = _run(layout)
    assert code == 3
    assert any("rva-devin-config.json is writable by others" in r for r in out["reasons"])


def test_symlinked_assets_dir_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    shutil.rmtree(root / "assets")
    elsewhere = layout["repo"] / "assets"
    elsewhere.mkdir()
    (root / "assets").symlink_to(elsewhere)
    code, out = _run(layout)
    assert code == 3
    assert any("assets is a symbolic link" in r for r in out["reasons"])


def test_missing_assets_dir_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    shutil.rmtree(root / "assets")
    code, out = _run(layout)
    assert code == 3
    assert any("assets is missing" in r for r in out["reasons"])


def test_manifest_picks_the_listed_version(layout):
    """With installed_plugins.json present, a stale unlisted folder neither blocks nor wins."""
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    listed = _rva(layout["cache"] / "reviewadapters-kit" / "0.2.0")
    _manifest(layout, "0.2.0")
    code, out = _run(layout)
    assert code == 0
    assert out["source"] == "sibling"
    assert out["dispatcher"] == str(listed.resolve() / "scripts" / "rva-dispatch.mjs")


def test_manifest_without_the_version_refuses_sibling(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    _manifest(layout)
    code, out = _run(layout)
    assert code == 3
    assert any("listed as installed, found: none" in r for r in out["reasons"])


def test_unreadable_manifest_refuses_sibling(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    _manifest(layout, raw="{not json")
    code, out = _run(layout)
    assert code == 3
    assert any("installed_plugins.json could not be read" in r for r in out["reasons"])


def test_world_writable_settings_refused(layout):
    """loadConfig reads the vendors' default models from the root (PR #804 security review)."""
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (root / "reviewadapters-kit.settings.json").chmod(0o666)
    code, out = _run(layout)
    assert code == 3
    assert any("settings.json is writable by others" in r for r in out["reasons"])


def test_symlinked_settings_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    settings = root / "reviewadapters-kit.settings.json"
    target = layout["repo"] / "settings.json"
    target.write_text('{"vendors": {"pi": {"model": "elsewhere/model"}}}\n')
    settings.unlink()
    settings.symlink_to(target)
    code, out = _run(layout)
    assert code == 3
    assert any("settings.json is a symbolic link" in r for r in out["reasons"])


def test_missing_settings_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (root / "reviewadapters-kit.settings.json").unlink()
    code, out = _run(layout)
    assert code == 3
    assert any("settings.json could not be checked" in r for r in out["reasons"])


def test_dispatcher_directory_refused(layout):
    root = _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    (root / "scripts" / "rva-dispatch.mjs").unlink()
    (root / "scripts" / "rva-dispatch.mjs").mkdir()
    code, out = _run(layout)
    assert code == 3
    assert any("rva-dispatch.mjs is not a regular file" in r for r in out["reasons"])


def test_world_writable_manifest_refuses_sibling(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    _manifest(layout, "0.1.0").chmod(0o666)
    code, out = _run(layout)
    assert code == 3
    assert any("installed_plugins.json is writable by others" in r for r in out["reasons"])


def test_symlinked_manifest_refuses_sibling(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    real = _manifest(layout, "0.1.0")
    moved = real.with_name("elsewhere.json")
    real.rename(moved)
    real.symlink_to(moved)
    code, out = _run(layout)
    assert code == 3
    assert any("installed_plugins.json could not be opened" in r for r in out["reasons"])


def test_deeply_nested_manifest_refuses_sibling(layout):
    _rva(layout["cache"] / "reviewadapters-kit" / "0.1.0")
    _manifest(layout, raw="[" * 100_000 + "]" * 100_000)
    code, out = _run(layout)
    assert code == 3
    assert any("installed_plugins.json could not be read" in r for r in out["reasons"])
