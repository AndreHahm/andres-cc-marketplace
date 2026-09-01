#!/usr/bin/env python3
"""Fixture-based regression test for bridge_caller.py. Run:
    python scripts/test_bridge_caller.py

Builds a temporary fake repo root (a .git marker, optionally a stub
bridge-invoke.mjs), runs bridge_caller.py as a subprocess against it via
--repo-root, and asserts on exit code + JSON output shape. Real agent files
(work-transition-reviewer.md/work-intake-classifier.md) are always read from
this plugin's own real agents/ directory -- bridge_caller.py resolves them
via its own __file__ location, not --repo-root, so no fake copy is needed.

Scratch-file leak detection points the subprocess's own tempfile.mkdtemp()
at a per-case, test-controlled directory via the TMP/TEMP/TMPDIR environment
variables (Python's tempfile module reads these to pick its default temp
base) -- bridge_caller.py's scratch directory otherwise lives in the real OS
temp location, which a test can't predict or glob safely.

Added per Devin's PR #278 round-2 review ("Bridge caller lacks regression
coverage") -- also regression-covers: a leaked instruction file when
bridge-invoke.mjs is missing (round 2, BUG_0002); the round-1 fix for
relative --target-paths resolving against the wrong cwd; and the full-review
fix moving the scratch instruction file outside the repository entirely
(round 2, full review -- a broad --target-paths value like the repo root
itself used to always contain the old in-repo scratch dir, rejecting every
such dispatch).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "bridge_caller.py"

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


def run(args, cwd=None, tmp_env=None):
    """tmp_env, if given, is a Path -- set as TMP/TEMP/TMPDIR so the
    subprocess's own tempfile.mkdtemp() calls land there instead of the
    real OS temp directory, so a test can glob for scratch-dir leaks."""
    env = dict(os.environ)
    if tmp_env is not None:
        env["TMP"] = str(tmp_env)
        env["TEMP"] = str(tmp_env)
        env["TMPDIR"] = str(tmp_env)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
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
    target = root / "evidence.md"
    target.write_text("evidence content", encoding="utf-8")
    if bridge_stub is not None:
        bridge_dir = root / "plugins" / "codex-kit" / "skills" / "codex-review-bridge" / "scripts"
        bridge_dir.mkdir(parents=True)
        bridge_script = bridge_dir / "bridge-invoke.mjs"
        bridge_script.write_text(bridge_stub, encoding="utf-8")
    return root


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

    if failures:
        print(f"FAIL: {len(failures)} case(s) failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("PASS: all 8 fixture cases behaved as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
