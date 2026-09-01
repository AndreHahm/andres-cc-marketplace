#!/usr/bin/env python3
"""Fixture-based regression test for bridge_caller.py. Run:
    python scripts/test_bridge_caller.py

Builds a temporary fake repo root (a .git marker, optionally a stub
bridge-invoke.mjs), runs bridge_caller.py as a subprocess against it via
--repo-root, and asserts on exit code + JSON output shape. Real agent files
(work-transition-reviewer.md/work-intake-classifier.md) are always read from
this plugin's own real agents/ directory -- bridge_caller.py resolves them
via its own __file__ location, not --repo-root, so no fake copy is needed.

Added per Devin's PR #278 round-2 review ("Bridge caller lacks regression
coverage") -- also regression-covers the two bugs found in the same round:
a leaked instruction file when bridge-invoke.mjs is missing (BUG_0002), and
the earlier round-1 fix for relative --target-paths resolving against the
wrong cwd.
"""

import json
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


def run(args, cwd=None):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
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


def scratch_files(root):
    scratch_dir = root / ".temp" / "workmanagement-kit-bridge"
    if not scratch_dir.is_dir():
        return []
    return list(scratch_dir.iterdir())


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
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or "does not match" not in payload.get("detail", ""):
            failures.append(
                f"[bad dispatch_id] expected clean rejection, got code={code} out={out!r}"
            )
        if scratch_files(root):
            failures.append("[bad dispatch_id] should never have written any scratch file")

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
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or payload.get("ok") is not False:
            failures.append(
                f"[missing bridge script] expected clean ok:false, got code={code} out={out!r}"
            )
        leaked = scratch_files(root)
        if leaked:
            failures.append(f"[missing bridge script] instruction file leaked: {leaked}")

        # 6. Instruction file nested in/equal to a target path is rejected.
        root = make_fake_repo(tmp_path / "case6")
        nested_target = root / ".temp" / "workmanagement-kit-bridge"
        code, out, err = run(
            [
                "--agent",
                "work-transition-reviewer",
                "--target-paths",
                str(nested_target),
                "--dispatch-id",
                "t6",
                "--execution-profile",
                "read-only",
                "--repo-root",
                str(root),
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if (
            code != 1
            or not payload
            or "nested in/equal to target path" not in payload.get("detail", "")
        ):
            failures.append(
                f"[nested instruction file] expected containment rejection, "
                f"got code={code} out={out!r}"
            )

        # 7. Happy path with a stub bridge: relative --target-paths resolves
        # against root even when invoked from an unrelated cwd (regression
        # for the round-1 fix: paths used to resolve against the process's
        # actual cwd instead of --repo-root). Also confirms cleanup after
        # a successful dispatch.
        root = make_fake_repo(tmp_path / "case7", bridge_stub=STUB_BRIDGE_SUCCESS)
        unrelated_cwd = tmp_path / "case7-unrelated-cwd"
        unrelated_cwd.mkdir()
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
        )
        payload = json.loads(out) if out.strip() else None
        if code != 0 or not payload or payload.get("verdict") != "pass":
            failures.append(
                f"[relative target from unrelated cwd] expected success, "
                f"got code={code} out={out!r}"
            )
        if scratch_files(root):
            failures.append(
                "[relative target from unrelated cwd] instruction file not cleaned up after success"
            )

        # 8. Regression (Devin/Codex round 1, Finding E): a typed failure the
        # bridge writes to stderr (not stdout) is parsed and its real
        # category surfaces -- not the generic bridge_caller_invocation_error.
        root = make_fake_repo(tmp_path / "case8", bridge_stub=STUB_BRIDGE_STDERR_FAILURE)
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
            ]
        )
        payload = json.loads(out) if out.strip() else None
        if code != 1 or not payload or payload.get("category") != "non_zero_exit":
            failures.append(
                f"[stderr typed failure] expected category non_zero_exit, "
                f"got code={code} out={out!r}"
            )
        if scratch_files(root):
            failures.append("[stderr typed failure] instruction file not cleaned up after failure")

    if failures:
        print(f"FAIL: {len(failures)} case(s) failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("PASS: all 8 fixture cases behaved as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
