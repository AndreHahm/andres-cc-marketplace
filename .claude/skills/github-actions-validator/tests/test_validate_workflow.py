#!/usr/bin/env python3
"""Regression test suite for scripts/validate_workflow.py.

Covers:
- P0: no false-success when actionlint is missing and act cannot validate target
- P1: advisory policy checks (SHA pinning, permissions, script injection, OIDC)

Builds an isolated sandbox per case with stub `docker`/`act`/`actionlint`
executables on PATH so the real tools never need to be installed to run
this suite.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
VALIDATOR_SOURCE = SKILL_DIR / "scripts" / "validate_workflow.py"

PASS = 0
FAIL = 0


def ok(label: str) -> None:
    global PASS
    print(f"  PASS: {label}")
    PASS += 1


def bad(label: str, output: str = "") -> None:
    global FAIL
    print(f"  FAIL: {label}")
    FAIL += 1
    if output:
        print("\n".join(f"    {line}" for line in output.splitlines()))


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class Sandbox:
    def __init__(self, tmp_root: Path):
        self.root = Path(tempfile.mkdtemp(dir=tmp_root, prefix="case-"))
        self.skill_dir = self.root / "skill" / "scripts"
        self.tools_dir = self.skill_dir / ".tools"
        self.repo_dir = self.root / "repo"
        self.bin_dir = self.root / "bin"

        (self.repo_dir / ".github" / "workflows").mkdir(parents=True)
        (self.repo_dir / "examples").mkdir(parents=True)
        self.tools_dir.mkdir(parents=True)
        self.bin_dir.mkdir(parents=True)

        self.validator_path = self.skill_dir / "validate_workflow.py"
        shutil.copy(VALIDATOR_SOURCE, self.validator_path)
        self.validator_path.chmod(self.validator_path.stat().st_mode | stat.S_IEXEC)

        write_executable(
            self.bin_dir / "docker",
            "#!/usr/bin/env bash\n"
            'if [[ "${1:-}" == "info" ]]; then\n'
            '  exit "${DOCKER_INFO_STUB_EXIT:-0}"\n'
            "fi\n"
            "exit 0\n",
        )

    def create_act_stub(self) -> None:
        write_executable(
            self.tools_dir / "act",
            "#!/usr/bin/env bash\n"
            'if [[ "$*" == *"--list"* ]]; then\n'
            '  exit "${ACT_LIST_STUB_EXIT:-0}"\n'
            "fi\n"
            'if [[ "$*" == *"--dryrun"* ]]; then\n'
            '  exit "${ACT_DRYRUN_STUB_EXIT:-0}"\n'
            "fi\n"
            'exit "${ACT_STUB_EXIT:-0}"\n',
        )

    def create_actionlint_stub(self) -> None:
        write_executable(
            self.tools_dir / "actionlint",
            '#!/usr/bin/env bash\nexit "${ACTIONLINT_STUB_EXIT:-0}"\n',
        )

    def write_repo_file(self, rel_path: str, content: str) -> Path:
        path = self.repo_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_validator(self, *args: str, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
        env = dict(os.environ)
        env["PATH"] = f"{self.bin_dir}:{env.get('PATH', '')}"
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, str(self.validator_path), *args],
            cwd=self.repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout + proc.stderr


def assert_exit(label: str, exit_code: int, expected: int, output: str) -> None:
    if exit_code == expected:
        ok(f"{label} (exit {exit_code})")
    else:
        bad(f"{label} (expected exit {expected}, got {exit_code})", output)


def assert_contains(label: str, output: str, pattern: str) -> None:
    import re

    if re.search(pattern, output):
        ok(label)
    else:
        bad(f"{label} (pattern not found: {pattern})", output)


def assert_not_contains(label: str, output: str, pattern: str) -> None:
    import re

    if re.search(pattern, output):
        bad(f"{label} (unexpected pattern found: {pattern})", output)
    else:
        ok(label)


def main() -> int:
    print("Running github-actions-validator regression tests...")
    print()

    with tempfile.TemporaryDirectory() as tmp_root_str:
        tmp_root = Path(tmp_root_str)

        print("[P0] actionlint missing + target outside .github/workflows must fail")
        sb = Sandbox(tmp_root)
        sb.create_act_stub()
        sb.write_repo_file(
            "examples/outside.yml",
            "name: Outside\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: echo hi\n",
        )
        exit_code, output = sb.run_validator(str(sb.repo_dir / "examples" / "outside.yml"))
        if exit_code != 0:
            ok("returns non-zero when no effective validator executed")
        else:
            bad(
                "returns non-zero when no effective validator executed (expected non-zero, got 0)",
                output,
            )
        assert_contains("reports skipped act path", output, "act validation skipped")
        assert_contains(
            "reports no effective validator",
            output,
            "No effective validator executed|No validator executed; refusing to report success",
        )

        print()
        print("[P0] actionlint run + act skip should still pass")
        sb = Sandbox(tmp_root)
        sb.create_act_stub()
        sb.create_actionlint_stub()
        sb.write_repo_file(
            "examples/outside.yml",
            "name: Outside\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: echo hi\n",
        )
        exit_code, output = sb.run_validator(str(sb.repo_dir / "examples" / "outside.yml"))
        assert_exit(
            "passes when actionlint runs and act skips unsupported target", exit_code, 0, output
        )
        assert_contains("shows actionlint success", output, "actionlint validation passed")
        assert_contains(
            "shows act skip message",
            output,
            r"act validation skipped: target file is outside \.github/workflows",
        )

        print()
        print("[P0] fallback to act-only still works for real workflow paths")
        sb = Sandbox(tmp_root)
        sb.create_act_stub()
        sb.write_repo_file(
            ".github/workflows/ci.yml",
            "name: CI\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: echo hi\n",
        )
        exit_code, output = sb.run_validator(str(sb.repo_dir / ".github" / "workflows" / "ci.yml"))
        assert_exit(
            "passes in act-only fallback mode for workflow under .github/workflows",
            exit_code,
            0,
            output,
        )
        assert_contains(
            "warns about actionlint fallback",
            output,
            r"actionlint not found\. Falling back to act-only validation",
        )
        assert_contains("act dry-run success is reported", output, "act validation passed")

        print()
        print("[P1] policy checks report hardening warnings (advisory)")
        sb = Sandbox(tmp_root)
        sb.create_actionlint_stub()
        sb.write_repo_file(
            "examples/policy-bad.yml",
            "name: Policy Bad\n"
            "on: pull_request\n"
            "jobs:\n"
            "  release:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: docker/build-push-action@v6\n"
            "      - uses: aws-actions/configure-aws-credentials@v4\n"
            "      - name: Unsafe run usage\n"
            '        run: echo "${{ github.event.pull_request.title }}"\n',
        )
        exit_code, output = sb.run_validator(
            "--lint-only", "--policy-checks", str(sb.repo_dir / "examples" / "policy-bad.yml")
        )
        assert_exit("policy warnings do not change exit code", exit_code, 0, output)
        assert_contains(
            "warns for unpinned third-party action",
            output,
            r"third-party action is not SHA pinned: docker/build-push-action@v6",
        )
        assert_contains(
            "warns for missing permissions", output, "missing explicit permissions block"
        )
        assert_contains(
            "warns for script injection pattern",
            output,
            "potential script injection risk in run step",
        )
        assert_contains(
            "warns for missing id-token with OIDC action",
            output,
            "OIDC-related action but does not declare id-token: write",
        )
        assert_contains("prints policy warning summary", output, "Security policy warnings:")

        print()
        print("[P1] policy checks accept hardened workflow")
        sb = Sandbox(tmp_root)
        sb.create_actionlint_stub()
        sb.write_repo_file(
            "examples/policy-good.yml",
            "name: Policy Good\n"
            "on: pull_request\n"
            "permissions:\n"
            "  contents: read\n"
            "  id-token: write\n"
            "jobs:\n"
            "  release:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: docker/build-push-action@"
            "0123456789abcdef0123456789abcdef01234567\n"
            "      - uses: aws-actions/configure-aws-credentials@"
            "0123456789abcdef0123456789abcdef01234567\n"
            "      - name: Safe run usage\n"
            "        env:\n"
            "          PR_TITLE: ${{ github.event.pull_request.title }}\n"
            '        run: echo "$PR_TITLE"\n',
        )
        exit_code, output = sb.run_validator(
            "--lint-only", "--policy-checks", str(sb.repo_dir / "examples" / "policy-good.yml")
        )
        assert_exit("hardened workflow remains successful", exit_code, 0, output)
        assert_contains("prints clean policy summary", output, "No security policy warnings found")
        assert_not_contains(
            "does not print warning summary when clean", output, "Security policy warnings:"
        )

        print()
        print("[P1] script injection check catches chomping-indicator run: block forms")
        sb = Sandbox(tmp_root)
        sb.create_actionlint_stub()
        sb.write_repo_file(
            "examples/policy-chomping.yml",
            "name: Policy Chomping\n"
            "on: pull_request\n"
            "jobs:\n"
            "  release:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: Dash chomped block\n"
            "        run: |-\n"
            "          echo ${{ github.event.pull_request.title }}\n"
            "      - name: Plus chomped block\n"
            "        run: >+\n"
            "          echo ${{ github.head_ref }}\n"
            "      - name: Indented block\n"
            "        run: |2\n"
            "          echo ${{ github.actor }}\n",
        )
        exit_code, output = sb.run_validator(
            "--lint-only", "--policy-checks", str(sb.repo_dir / "examples" / "policy-chomping.yml")
        )
        assert_exit("chomping-indicator run: blocks do not change exit code", exit_code, 0, output)
        assert_contains(
            "warns for injection inside a '|-' chomped block",
            output,
            r"policy-chomping\.yml:9 potential script injection risk",
        )
        assert_contains(
            "warns for injection inside a '>+' chomped block",
            output,
            r"policy-chomping\.yml:12 potential script injection risk",
        )
        assert_contains(
            "warns for injection inside a '|2' indented block",
            output,
            r"policy-chomping\.yml:15 potential script injection risk",
        )

        print()
        print("[P1] script injection check catches needs/steps/inputs laundered-taint sinks")
        sb = Sandbox(tmp_root)
        sb.create_actionlint_stub()
        sb.write_repo_file(
            "examples/policy-laundered.yml",
            "name: Policy Laundered\n"
            "on: pull_request\n"
            "jobs:\n"
            "  release:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: needs output\n"
            '        run: echo "${{ needs.build.outputs.artifact }}"\n'
            "      - name: steps output\n"
            '        run: echo "${{ steps.tag.outputs.version }}"\n'
            "      - name: workflow_call input\n"
            '        run: echo "${{ inputs.branch }}"\n',
        )
        exit_code, output = sb.run_validator(
            "--lint-only", "--policy-checks", str(sb.repo_dir / "examples" / "policy-laundered.yml")
        )
        assert_exit("laundered-taint sinks do not change exit code", exit_code, 0, output)
        assert_contains(
            "warns for needs.*.outputs.* sink",
            output,
            r"policy-laundered\.yml:8 potential script injection risk",
        )
        assert_contains(
            "warns for steps.*.outputs.* sink",
            output,
            r"policy-laundered\.yml:10 potential script injection risk",
        )
        assert_contains(
            "warns for inputs.* sink",
            output,
            r"policy-laundered\.yml:12 potential script injection risk",
        )

        print()
        print("[P1] script injection check catches context wrapped inside a function call")
        sb = Sandbox(tmp_root)
        sb.create_actionlint_stub()
        sb.write_repo_file(
            "examples/policy-wrapped.yml",
            "name: Policy Wrapped\n"
            "on: pull_request\n"
            "jobs:\n"
            "  release:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: toJSON-wrapped context\n"
            '        run: echo "${{ toJSON(github.event.issue.title) }}"\n'
            "      - name: format-wrapped context\n"
            "        run: echo \"${{ format('{0}', inputs.branch) }}\"\n",
        )
        exit_code, output = sb.run_validator(
            "--lint-only", "--policy-checks", str(sb.repo_dir / "examples" / "policy-wrapped.yml")
        )
        assert_exit("function-wrapped injection does not change exit code", exit_code, 0, output)
        assert_contains(
            "warns for github.event wrapped in toJSON(...)",
            output,
            r"policy-wrapped\.yml:8 potential script injection risk",
        )
        assert_contains(
            "warns for inputs.branch wrapped in format(...)",
            output,
            r"policy-wrapped\.yml:10 potential script injection risk",
        )

        print()
        print("[P0] act failing with an unrecognized, nonzero exit must be reported as failure")
        sb = Sandbox(tmp_root)
        sb.create_act_stub()
        sb.write_repo_file(
            ".github/workflows/ci.yml",
            "name: CI\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: echo hi\n",
        )
        exit_code, output = sb.run_validator(
            "--test-only",
            str(sb.repo_dir / ".github" / "workflows" / "ci.yml"),
            extra_env={"ACT_DRYRUN_STUB_EXIT": "3"},
        )
        assert_exit("unrecognized nonzero act exit is reported as failure", exit_code, 1, output)
        assert_contains(
            "reports act validation failed", output, r"act validation failed \(exit code: 3\)"
        )
        assert_not_contains(
            "does not report act as merely completed with warnings",
            output,
            "act completed with warnings",
        )

    print()
    print(f"Test summary: PASS={PASS} FAIL={FAIL}")
    if FAIL != 0:
        return 1

    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
