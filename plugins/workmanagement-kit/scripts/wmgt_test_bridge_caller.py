#!/usr/bin/env python3
"""Fixture-based regression test for wmgt_bridge_caller.py. Run:
    python scripts/wmgt_test_bridge_caller.py

Builds a temporary fake checkout (a .git marker, a copy of the script and its agents
under plugins/workmanagement-kit, optionally a stub bridge-invoke.mjs), runs the script
from it as a subprocess, and asserts on exit code + JSON output shape. The copy matters:
--repo-root never selects the bridge, only the script's own checkout or the registry
does. Every run replaces _home() with a test folder, so the real installed_plugins.json
is never read.

Scratch-file leak detection points the subprocess's own tempfile.mkdtemp()
at a per-case, test-controlled directory via the TMP/TEMP/TMPDIR environment
variables (Python's tempfile module reads these to pick its default temp
base) -- wmgt_bridge_caller.py's scratch directory otherwise lives in the real OS
temp location, which a test can't predict or glob safely.

Added per Devin's PR #278 round-2 review ("Bridge caller lacks regression
coverage") -- also regression-covers: a leaked instruction file when
bridge-invoke.mjs is missing (round 2, BUG_0002); the round-1 fix for
relative --target-paths resolving against the wrong cwd; and the full-review
fix moving the scratch instruction file outside the repository entirely
(round 2, full review -- a broad --target-paths value like the repo root
itself used to always contain the old in-repo scratch dir, rejecting every
such dispatch); and the round-2 CodeRabbit fix for an invalid --agent choice
or a missing required option bypassing the typed-failure contract entirely
via argparse's own direct sys.exit(2).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "wmgt_bridge_caller.py"
AGENTS_DIR = SCRIPT.parent.parent / "agents"
REGISTRY_KEY = "codex-kit@andres-cc-marketplace"
BRIDGE = Path("skills/codex-review-bridge/scripts/bridge-invoke.mjs")

# Runs argv[1] as __main__ would, with the account's home replaced by argv[2].
DRIVER = """
import importlib.util, pathlib, sys
script, home = sys.argv[1], pathlib.Path(sys.argv[2])
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("caller", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._home = lambda: home
sys.argv = [script, *sys.argv[3:]]
module.main()
"""

STUB_BRIDGE_SUCCESS = """#!/usr/bin/env node
console.log(JSON.stringify({
  contract_version: "1",
  dispatch: {id: "test", reviewer: "test", backend: "codex", target_paths: []},
  provenance: {
    provider: "test", model: "test", cli_version: "test", execution_profile: "read-only"
  },
  findings: [],
  verdict: "pass",
  inspection_limits: []
}));
"""

STUB_BRIDGE_STDERR_FAILURE = """#!/usr/bin/env node
console.error(JSON.stringify(
  {ok: false, category: "non_zero_exit", detail: "stub failure on stderr"}
));
process.exit(1);
"""


def run(args, cwd=None, tmp_env=None, script=None, home=None, extra_env=None):
    """tmp_env, if given, is a Path -- set as TMP/TEMP/TMPDIR so the
    subprocess's own tempfile.mkdtemp() calls land there instead of the
    real OS temp directory, so a test can glob for scratch-dir leaks."""
    # A host that sets this itself would hide a missing one in the child.
    unset = "NODEFAULTCURRENTDIRECTORYINEXEPATH"
    env = {k: v for k, v in os.environ.items() if k.upper() != unset}
    if tmp_env is not None:
        env["TMP"] = str(tmp_env)
        env["TEMP"] = str(tmp_env)
        env["TMPDIR"] = str(tmp_env)
    env.update(extra_env or {})
    if script is None and "--repo-root" in args:
        script = plugin_copy(Path(args[args.index("--repo-root") + 1]))
    script = script or SCRIPT
    home = home or Path(tempfile.gettempdir()) / "wmgt-test-no-such-home"
    result = subprocess.run(
        [sys.executable, "-c", DRIVER, str(script), str(home), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def make_fake_repo(tmp_path, bridge_stub=None):
    """A minimal fake repo root: .git marker + a real target evidence file.
    bridge_stub, if given, is written as plugins/codex-kit/skills/
    codex-review-bridge/scripts/bridge-invoke.mjs (executable)."""
    root = tmp_path / "fake-repo"
    (root / ".git").mkdir(parents=True)
    copy_plugin(root / "plugins" / "workmanagement-kit")
    target = root / "evidence.md"
    target.write_text("evidence content", encoding="utf-8")
    if bridge_stub is not None:
        write_bridge(root / "plugins" / "codex-kit", bridge_stub)
    return root


def write_bridge(kit, stub_text):
    (kit / BRIDGE).parent.mkdir(parents=True)
    (kit / BRIDGE).write_text(stub_text, encoding="utf-8")
    return kit


def copy_plugin(dest):
    """This plugin's script and agents at dest; returns the script's path."""
    (dest / "scripts").mkdir(parents=True)
    (dest / "agents").mkdir()
    shutil.copy(SCRIPT, dest / "scripts")
    for name in ("work-transition-reviewer.md", "work-intake-classifier.md"):
        shutil.copy(AGENTS_DIR / name, dest / "agents")
    return dest / "scripts" / SCRIPT.name


def plugin_copy(root):
    return root / "plugins" / "workmanagement-kit" / "scripts" / SCRIPT.name


def make_home(base, *install_paths, raw=None):
    """A home whose installed_plugins.json registers codex-kit at install_paths."""
    folder = base / "home" / ".claude" / "plugins"
    folder.mkdir(parents=True)
    entries = [{"scope": "user", "installPath": str(p)} for p in install_paths]
    text = raw if raw is not None else json.dumps({"plugins": {REGISTRY_KEY: entries}})
    (folder / "installed_plugins.json").write_text(text, encoding="utf-8")
    return base / "home"


def stub(verdict):
    return STUB_BRIDGE_SUCCESS.replace('"pass"', json.dumps(verdict))


def locator_cases(base, failures):
    """Issue #279: where the bridge that gets executed may come from."""
    total = 0

    def check(name, script, cwd, verdict=None, detail="", extra=(), home=None, env=None):
        nonlocal total
        total += 1
        argv = ["--agent", "work-intake-classifier", "--target-paths", "evidence.md"]
        argv += ["--dispatch-id", "loc", "--execution-profile", "read-only", *extra]
        code, out, err = run(argv, cwd=cwd, script=script, home=home, extra_env=env)
        payload = json.loads(out) if out.strip() else {}
        if verdict is not None:
            good = code == 0 and payload.get("verdict") == verdict
        else:
            good = code == 1 and payload.get("ok") is False
            good = good and detail in str(payload.get("detail"))
        if not good:
            failures.append(f"[{name}] unexpected result: code={code} out={out!r} err={err!r}")

    def checkout(name, bridge="sibling"):
        """(root, the script inside it)"""
        (base / name).mkdir()
        root = make_fake_repo(base / name, stub(bridge) if bridge else None)
        return root, plugin_copy(root)

    root, script = checkout("wins")
    home = make_home(base / "wins", write_bridge(base / "wins" / "kit", stub("installed")))
    check("registry wins over the sibling", script, root, verdict="installed", home=home)

    root, script = checkout("no-entry")
    home = make_home(base / "no-entry")
    check("no entry falls back to the sibling", script, root, verdict="sibling", home=home)

    root, _ = checkout("mirror")
    script = copy_plugin(root / ".claude")
    check("the .claude mirror uses the same sibling", script, root, verdict="sibling")

    # An installed plugin: the cache has no .git, the project is the working directory's
    # repository, and that project's own plugins/codex-kit must never be executed.
    def installed(name):
        project, _ = checkout(name)
        return project, copy_plugin(base / name / "cache" / "workmanagement-kit" / "1.0.0")

    project, script = installed("standalone")
    kit = write_bridge(base / "standalone" / "cache" / "codex-kit" / "1.0.0", stub("installed"))
    home = make_home(base / "standalone", kit)
    check("standalone install", script, project, verdict="installed", home=home)

    # What the child is really given: the root, the targets, isolation and cmd.exe's lookup.
    project, script = installed("echo")
    (project / "sub").mkdir()
    echo = "console.log(JSON.stringify({verdict: process.argv.slice(2).join(' ') + ' ' +"
    echo += " process.env.NoDefaultCurrentDirectoryInExePath}))"
    home = make_home(base / "echo", write_bridge(base / "echo" / "kit", echo))
    for where in (project, project / "sub"):
        total += 1
        argv = ["--agent", "work-intake-classifier", "--target-paths", "evidence.md"]
        argv += ["--dispatch-id", "echo", "--execution-profile", "read-only"]
        _, out, err = run(argv, cwd=where, script=script, home=home)
        got = json.loads(out).get("verdict", "") if out.strip() else ""
        wanted = [f"--cwd {project.as_posix()} ", "--target-paths evidence.md "]
        if not all(w in got for w in [*wanted, "--isolate-project true 1"]):
            failures.append(f"[child arguments from {where.name}] {out!r} {err!r}")

    root, script = checkout("pointer")
    (root / ".git").rmdir()
    (root / ".git").write_text("gitdir: /no/such/dir\n", encoding="utf-8")
    check("an unreadable git pointer", script, root, detail="could not read the git directory")

    project, script = installed("missing")
    (project / "evidence.md").unlink()
    home = make_home(base / "missing", write_bridge(base / "missing" / "kit", stub("installed")))
    check("a missing target", script, project, detail="does not exist", home=home)

    project, script = installed("alone")
    check("no codex-kit installed", script, project, detail="codex-kit is not installed")

    project, script = installed("hostile")
    check(
        "--repo-root never selects the bridge",
        script,
        project,
        detail="codex-kit is not installed",
        extra=("--repo-root", str(project)),
    )

    root, script = checkout("in-repo")
    home = make_home(base / "in-repo", root / "plugins" / "codex-kit")
    check("an installed root in the repository", script, root, detail="lies inside", home=home)

    root, script = checkout("worktree")
    other = base / "worktree" / "other"
    kit = write_bridge(other / "plugins" / "codex-kit", stub("other"))
    entry = root / ".git" / "worktrees" / "other"
    entry.mkdir(parents=True)
    (entry / "gitdir").write_text(f"{other / '.git'}\n", encoding="utf-8")
    (other / ".git").write_text(f"gitdir: {entry}\n", encoding="utf-8")
    home = make_home(base / "worktree", kit)
    check("an installed root in a worktree", script, root, detail="lies inside", home=home)

    # An entry whose gitdir cannot be read: refused, not left out of the forbidden roots.
    root, script = checkout("unreadable-entry")
    (root / ".git" / "worktrees" / "bad" / "gitdir").mkdir(parents=True)
    check("an unreadable worktree entry", script, root, detail="could not read the worktree entry")

    # An entry with no gitdir is not a worktree, for git either: skipped.
    root, script = checkout("leftover-entry")
    (root / ".git" / "worktrees" / "leftover").mkdir(parents=True)
    (root / ".git" / "worktrees" / "notes.bak").write_text("x", encoding="utf-8")
    check("a leftover entry and a stray file", script, root, verdict="sibling")

    root, script = checkout("narrow")
    elsewhere, _ = checkout("elsewhere")
    home = make_home(base / "narrow", root / "plugins" / "codex-kit")
    check(
        "--repo-root cannot narrow the refusal",
        script,
        root,
        detail="lies inside",
        extra=("--repo-root", str(elsewhere)),
        home=home,
    )

    root, script = checkout("ambiguous")
    kits = [write_bridge(base / "ambiguous" / n, stub(n)) for n in ("a", "b")]
    home = make_home(base / "ambiguous", *kits)
    check("two roots are refused, no fallback", script, root, detail="found 2", home=home)

    root, script = checkout("broken")
    home = make_home(base / "broken", raw="{")
    check("a broken registry, no fallback", script, root, detail="could not be read", home=home)

    root, script = checkout("relative")
    home = make_home(base / "relative", "plugins/codex-kit")
    check("a relative installPath", script, root, detail="not absolute", home=home)

    root, script = checkout("planted")
    bin_dir = root / "bin"
    bin_dir.mkdir()
    shutil.copy(sys.executable, bin_dir / ("node.exe" if os.name == "nt" else "node"))
    path = str(bin_dir) + os.pathsep + os.environ["PATH"]
    check("a node inside the repository", script, root, detail="node on PATH", env={"PATH": path})

    root, script = checkout("preload", bridge=None)
    write_bridge(
        root / "plugins" / "codex-kit",
        "console.log(JSON.stringify({verdict: ['NODE_OPTIONS', 'GIT_DIR']"
        ".filter(k => k in process.env).join()}))",
    )
    env = {"NODE_OPTIONS": "--no-warnings", "GIT_DIR": "x"}
    check("NODE_* and GIT_* are dropped", script, root, verdict="", env=env)

    # The real _home(): no variable a repository's settings could set may move it.
    code = (
        "import sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]); "
        "import wmgt_bridge_caller as m; print(m._home())"
    )
    homes = []
    for value in (None, str(base)):
        env = dict(os.environ)
        if value:
            env.update(HOME=value, USERPROFILE=value, CLAUDE_CONFIG_DIR=value)
        argv = [sys.executable, "-c", code, str(SCRIPT.parent)]
        homes.append(subprocess.run(argv, capture_output=True, text=True, env=env).stdout.strip())
    total += 1
    if not homes[0] or homes[0] != homes[1]:
        failures.append(f"[environment moves the home] {homes}")
    return total


def make_tmp_env(tmp_path, name):
    tmp_env = tmp_path / name
    tmp_env.mkdir()
    return tmp_env


def scratch_leaks(tmp_env):
    """Any workmanagement-kit-bridge-* directory left under tmp_env is a
    leak -- a successful cleanup removes both the instruction file and its
    containing mkdtemp() directory."""
    return list(tmp_env.glob("workmanagement-kit-bridge-*"))


def main():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1. Empty target_paths -> clean typed failure, not a crash.
        root = make_fake_repo(tmp_path / "case1")
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                "",
                "--dispatch-id",
                "t1",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or payload.get("ok") is not False:
            failures.append(
                f"[empty target_paths] expected clean ok:false/exit 1, got code={code} out={out!r}"
            )
        elif "target_paths" not in payload.get("detail", ""):
            failures.append(f"[empty target_paths] detail doesn't mention target_paths: {payload}")

        # 2. danger-full-access is rejected locally (defense in depth).
        root = make_fake_repo(tmp_path / "case2")
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                str(root / "evidence.md"),
                "--dispatch-id",
                "t2",
                "--execution-profile",
                "danger-full-access",
                "--repo-root",
                str(root),
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or "danger-full-access" not in payload.get("detail", ""):
            failures.append(f"[danger-full-access] expected rejection, got code={code} out={out!r}")

        # 3. Invalid dispatch_id is rejected before any path is touched.
        root = make_fake_repo(tmp_path / "case3")
        tmp_env = make_tmp_env(tmp_path, "case3-tmp")
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                str(root / "evidence.md"),
                "--dispatch-id",
                "../../evil",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
            ],
            tmp_env=tmp_env,
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or "does not match" not in payload.get("detail", ""):
            failures.append(
                f"[bad dispatch_id] expected clean rejection, got code={code} out={out!r}"
            )
        if scratch_leaks(tmp_env):
            failures.append("[bad dispatch_id] should never have written any scratch dir")

        # 4. --cwd diverging from --repo-root is rejected.
        root = make_fake_repo(tmp_path / "case4")
        other_dir = tmp_path / "case4-other"
        other_dir.mkdir()
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                str(root / "evidence.md"),
                "--dispatch-id",
                "t4",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
                "--cwd",
                str(other_dir),
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or "--cwd" not in payload.get("detail", ""):
            failures.append(f"[cwd != root] expected rejection, got code={code} out={out!r}")

        # 5. Regression (BUG_0002, Devin round 2): a missing bridge-invoke.mjs
        # raises FileNotFoundError AFTER the instruction file is written --
        # confirm it's still cleaned up, not leaked.
        root = make_fake_repo(tmp_path / "case5")  # no bridge_stub -> missing
        tmp_env = make_tmp_env(tmp_path, "case5-tmp")
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                str(root / "evidence.md"),
                "--dispatch-id",
                "t5",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
            ],
            tmp_env=tmp_env,
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or payload.get("ok") is not False:
            failures.append(
                f"[missing bridge script] expected clean ok:false, got code={code} out={out!r}"
            )
        leaked = scratch_leaks(tmp_env)
        if leaked:
            failures.append(f"[missing bridge script] instruction dir leaked: {leaked}")

        # 6. Regression (Codex full review, round 2): a broad --target-paths
        # value (the repo root itself) used to always contain the old
        # in-repo scratch dir, rejecting every such dispatch. The scratch
        # dir now lives outside the repo entirely, so this must succeed.
        root = make_fake_repo(tmp_path / "case6", bridge_stub=STUB_BRIDGE_SUCCESS)
        tmp_env = make_tmp_env(tmp_path, "case6-tmp")
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                str(root),  # the repo root itself -- the broadest possible scope
                "--dispatch-id",
                "t6",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
            ],
            tmp_env=tmp_env,
        )
        payload = json.loads(out) if out.strip() else None
        if code != 0 or not payload or payload.get("verdict") != "pass":
            failures.append(
                f"[repo-root target scope] expected success, got code={code} out={out!r}"
            )
        if scratch_leaks(tmp_env):
            failures.append("[repo-root target scope] instruction dir not cleaned up after success")

        # 7. Happy path with a stub bridge: relative --target-paths resolves
        # against root even when invoked from an unrelated cwd (regression
        # for the round-1 fix: paths used to resolve against the process's
        # actual cwd instead of --repo-root). Also confirms cleanup after
        # a successful dispatch.
        root = make_fake_repo(tmp_path / "case7", bridge_stub=STUB_BRIDGE_SUCCESS)
        unrelated_cwd = tmp_path / "case7-unrelated-cwd"
        unrelated_cwd.mkdir()
        tmp_env = make_tmp_env(tmp_path, "case7-tmp")
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                "evidence.md",  # relative -- must resolve against root, not cwd
                "--dispatch-id",
                "t7",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
            ],
            cwd=str(unrelated_cwd),
            tmp_env=tmp_env,
        )
        payload = json.loads(out) if out.strip() else None
        if code != 0 or not payload or payload.get("verdict") != "pass":
            failures.append(
                f"[relative target from unrelated cwd] expected success, "
                f"got code={code} out={out!r}"
            )
        if scratch_leaks(tmp_env):
            failures.append(
                "[relative target from unrelated cwd] instruction dir not cleaned up after success"
            )

        # 8. Regression (Devin/Codex round 1, Finding E): a typed failure the
        # bridge writes to stderr (not stdout) is parsed and its real
        # category surfaces -- not the generic bridge_caller_invocation_error.
        root = make_fake_repo(tmp_path / "case8", bridge_stub=STUB_BRIDGE_STDERR_FAILURE)
        tmp_env = make_tmp_env(tmp_path, "case8-tmp")
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                str(root / "evidence.md"),
                "--dispatch-id",
                "t8",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
            ],
            tmp_env=tmp_env,
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or payload.get("category") != "non_zero_exit":
            failures.append(
                f"[stderr typed failure] expected category non_zero_exit, "
                f"got code={code} out={out!r}"
            )
        if scratch_leaks(tmp_env):
            failures.append("[stderr typed failure] instruction dir not cleaned up after failure")

        # 9. Regression (CodeRabbit round 2): an invalid --agent choice used
        # to bypass the typed-failure contract entirely (raw argparse usage
        # text on stderr, bare exit(2), no JSON on stdout at all).
        code, out, err = run(
            [
                "--agent",
                "nonexistent-agent",
                "--target-paths",
                "x",
                "--dispatch-id",
                "t9",
                "--execution-profile",
                "read-only",
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or "invalid choice" not in payload.get("detail", ""):
            failures.append(
                f"[invalid --agent] expected clean typed failure, "
                f"got code={code} out={out!r} err={err!r}"
            )

        # 10. Regression (CodeRabbit round 2): a missing required option hit
        # the same bypass as case 9 above.
        code, out, err = run(["--agent", "work-transition-reviewer", "--target-paths", "x"])
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or "required" not in payload.get("detail", ""):
            failures.append(
                f"[missing required option] expected clean typed failure, "
                f"got code={code} out={out!r} err={err!r}"
            )

    with tempfile.TemporaryDirectory() as tmp:
        total = 10 + locator_cases(Path(tmp).resolve(), failures)

    if failures:
        print(f"FAIL: {len(failures)} case(s) failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"PASS: all {total} fixture cases behaved as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
