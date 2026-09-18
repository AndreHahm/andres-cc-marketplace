#!/usr/bin/env python3
"""GitHub Actions Validator - Workflow Validation Script.

Validates GitHub Actions workflows using actionlint and act. Includes
version checking, advisory security policy checks, and reference file hints.

Tools are expected pre-installed (on PATH, or in scripts/.tools/) -- this
script does not auto-fetch actionlint/act; see SKILL.md for manual
installation instructions.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR / ".tools"
SKILL_DIR = SCRIPT_DIR.parent
REFERENCES_DIR = SKILL_DIR / "references"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def log_info(msg: str) -> None:
    print(f"{GREEN}[INFO]{NC} {msg}")


def log_warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC} {msg}")


def log_error(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}")


def log_section(title: str) -> None:
    print()
    print(f"{BLUE}=== {title} ==={NC}")
    print()


def log_reference(msg: str) -> None:
    print(f"{CYAN}[REF]{NC} {msg}")


def tool_exists(tool_name: str) -> bool:
    candidate = TOOLS_DIR / tool_name
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return True
    return shutil.which(tool_name) is not None


def check_docker() -> bool:
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def precheck_docker() -> bool:
    if not check_docker():
        log_warn("Docker is not running - act testing will be skipped")
        log_info("To enable full validation, start Docker Desktop or Docker daemon")
        log_info("Continuing with actionlint validation only...")
        print()
        return False
    return True


# Current recommended action versions (December 2025)
# Format: action_name -> (current_version, minimum_version)
ACTION_VERSIONS: dict[str, tuple[str, str]] = {
    "actions/checkout": ("v6", "v4"),
    "actions/setup-node": ("v6", "v4"),
    "actions/setup-python": ("v5", "v4"),
    "actions/setup-java": ("v4", "v4"),
    "actions/setup-go": ("v5", "v4"),
    "actions/cache": ("v4", "v4"),
    "actions/upload-artifact": ("v4", "v4"),
    "actions/download-artifact": ("v4", "v4"),
    "docker/setup-buildx-action": ("v3", "v3"),
    "docker/login-action": ("v3", "v3"),
    "docker/build-push-action": ("v6", "v5"),
    "docker/metadata-action": ("v5", "v5"),
    "aws-actions/configure-aws-credentials": ("v4", "v4"),
}


def get_major_version(version: str) -> str:
    """v4.1.1 -> '4', v4 -> '4'."""
    return version.lstrip("v").split(".")[0]


def collect_workflow_files(workflow_path: str) -> list[str] | None:
    """Files to check for a file-or-directory target. None means path not found."""
    p = Path(workflow_path)
    if p.is_file():
        return [str(p)]
    if p.is_dir():
        return sorted(str(f) for f in p.iterdir() if f.is_file() and f.suffix in (".yml", ".yaml"))
    return None


USES_VERSION_RE = re.compile(r"uses:\s*([^@]+)@([^\s#]+)")
SHA_LIKE_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{7,}$")
VERSION_IN_LINE_RE = re.compile(r"v(\d+)")


def check_action_versions(workflow_path: str) -> int:
    log_section("Action Version Check")

    files = collect_workflow_files(workflow_path) or []
    if not files:
        log_warn("No workflow files found to check")
        return 0

    has_issues = False
    outdated_count = 0
    deprecated_count = 0
    uptodate_count = 0

    for file in files:
        log_info(f"Checking: {file}")
        text = Path(file).read_text(encoding="utf-8", errors="replace")

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            m = USES_VERSION_RE.search(line)
            if not m:
                continue

            action = m.group(1).strip().strip('"').strip("'")
            version = m.group(2)

            if action not in ACTION_VERSIONS:
                continue

            current_version, minimum_version = ACTION_VERSIONS[action]
            current_major = get_major_version(current_version)
            minimum_major = get_major_version(minimum_version)

            used_major: str | None
            if SHA_LIKE_RE.match(version):
                vm = VERSION_IN_LINE_RE.search(line)
                if vm:
                    used_major = vm.group(1)
                else:
                    print(f"  ⚪ {action}@{version[:12]}... - SHA pinned (version unknown)")
                    continue
            else:
                used_major = get_major_version(version)

            if not used_major or not used_major.isdigit():
                print(f"  ⚪ {action}@{version} - Unable to parse version")
                continue

            used_major_i = int(used_major)
            if used_major_i < int(minimum_major):
                print(
                    f"  {RED}❌{NC} {action}@{version} - {RED}DEPRECATED{NC} "
                    f"(minimum: {minimum_version}, using: v{used_major})"
                )
                deprecated_count += 1
                has_issues = True
            elif used_major_i < int(current_major):
                print(
                    f"  {YELLOW}⚠️{NC}  {action}@{version} - {YELLOW}OUTDATED{NC} "
                    f"(current: {current_version}, using: v{used_major})"
                )
                outdated_count += 1
            else:
                print(
                    f"  {GREEN}✅{NC} {action}@{version} - UP-TO-DATE (current: {current_version})"
                )
                uptodate_count += 1

    print()
    log_info("Version Check Summary:")
    log_info(f"  Up-to-date: {uptodate_count}")
    if outdated_count > 0:
        log_warn(f"  Outdated: {outdated_count}")
    if deprecated_count > 0:
        log_error(f"  Deprecated: {deprecated_count}")

    if outdated_count > 0 or deprecated_count > 0:
        print()
        log_info("Recommendations:")
        if deprecated_count > 0:
            log_error(
                "  - Update deprecated actions to current versions (see references/action-versions.md)"
            )
        if outdated_count > 0:
            log_warn("  - Consider updating outdated actions for latest features")
        log_info("  - Use SHA pinning for security: action@SHA # vX.Y.Z")

    return 1 if has_issues else 0


INJECTION_CONTEXT_RE = re.compile(
    r"\$\{\{\s*github\.(event|head_ref|ref_name|actor|triggering_actor|repository_owner|base_ref)"
)
RUN_BLOCK_START_RE = re.compile(r"^\s*run:\s*[|>]\s*$")
RUN_INLINE_RISK_RE = re.compile(
    r"^\s*run:\s*.*\$\{\{\s*github\.(event|head_ref|ref_name|actor|triggering_actor|repository_owner|base_ref)"
)


def find_injection_risk_lines(lines: list[str]) -> list[int]:
    """Heuristic: untrusted github.* context interpolated directly into a run: step."""
    risky: list[int] = []
    in_run_block = False
    run_indent = -1

    for idx, line in enumerate(lines, start=1):
        indent = len(line) - len(line.lstrip(" "))

        if in_run_block and indent <= run_indent and line.strip() != "":
            in_run_block = False

        if RUN_BLOCK_START_RE.match(line):
            in_run_block = True
            run_indent = indent
            continue

        if RUN_INLINE_RISK_RE.match(line):
            risky.append(idx)
            continue

        if in_run_block and INJECTION_CONTEXT_RE.search(line):
            risky.append(idx)

    return risky


USES_LINE_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)@([^\s#]+)")
OIDC_ACTION_RE = re.compile(
    r"uses:\s*(aws-actions/configure-aws-credentials|azure/login|google-github-actions/auth|"
    r"hashicorp/vault-action|actions/attest-build-provenance)@",
    re.IGNORECASE,
)


def check_security_policies(workflow_path: str) -> int:
    """Advisory security hardening checks. Always returns 0 (warnings don't fail the run)."""
    log_section("Security Policy Checks (Advisory)")

    files = collect_workflow_files(workflow_path)
    if files is None:
        log_error(f"Path not found: {workflow_path}")
        return 1
    if not files:
        log_warn("No workflow files found for security checks")
        return 0

    warning_count = 0

    for file in files:
        log_info(f"Checking policies in: {file}")
        text = Path(file).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        # 1) Third-party actions should be pinned to full SHA.
        for line_no, line in enumerate(lines, start=1):
            m = USES_LINE_RE.match(line)
            if not m:
                continue
            action = m.group(1).strip().strip('"').strip("'")
            version = m.group(2).strip().strip('"').strip("'").rstrip(", ")

            if (
                action.startswith("./")
                or action.startswith("../")
                or action.startswith("docker://")
            ):
                continue

            if "/" in action:
                owner = action.split("/", 1)[0]
                if owner not in ("actions", "github") and not re.match(
                    r"^[0-9a-fA-F]{40}$", version
                ):
                    log_warn(
                        f"{file}:{line_no} third-party action is not SHA pinned: {action}@{version}"
                    )
                    warning_count += 1

        # 2) Explicit least-privilege permissions.
        if not re.search(r"^\s*permissions:\s*", text, re.MULTILINE):
            log_warn(
                f"{file} missing explicit permissions block. Add workflow/job-level permissions (or permissions: {{}})."
            )
            warning_count += 1
        if re.search(r"^\s*permissions:\s*write-all\s*(#.*)?$", text, re.MULTILINE):
            log_warn(f"{file} uses permissions: write-all. Prefer least-privilege scopes.")
            warning_count += 1

        # 3) Heuristic detection for untrusted github context in run scripts.
        for line_no in find_injection_risk_lines(lines):
            log_warn(
                f"{file}:{line_no} potential script injection risk in run step. Move untrusted input to env and quote it."
            )
            warning_count += 1

        # 4) OIDC-integrated actions should explicitly request id-token: write.
        if OIDC_ACTION_RE.search(text) and not re.search(r"id-token:\s*write", text, re.IGNORECASE):
            log_warn(
                f"{file} uses an OIDC-related action but does not declare id-token: write in permissions."
            )
            warning_count += 1

    print()
    if warning_count == 0:
        log_info("✓ No security policy warnings found")
    else:
        log_warn(f"Security policy warnings: {warning_count} (advisory only; exit code unchanged)")
        log_info('See references/common-pitfalls.md\'s "Security Policy Checks (Advisory)" section')

    return 0


def show_reference_hints(error_output: str) -> None:
    log_section("Reference Documentation")
    showed_hint = False
    lower = error_output.lower()

    def has(*keys: str) -> bool:
        return any(k in lower for k in keys)

    if has("syntax", "yaml", "unexpected"):
        log_reference(
            "Syntax errors detected - see references/common-errors.md (Syntax Errors section)"
        )
        showed_hint = True
    if has("expression", "${{"):
        log_reference(
            "Expression errors detected - see references/common-errors.md (Expression Errors section)"
        )
        showed_hint = True
    if has("cron", "schedule"):
        log_reference(
            "Schedule errors detected - see references/common-errors.md (Schedule Errors section)"
        )
        showed_hint = True
    if has("runner", "runs-on", "ubuntu", "macos", "windows"):
        log_reference("Runner label issues - see references/runners.md")
        showed_hint = True
    if has("action", "uses:"):
        log_reference(
            "Action issues detected - see references/common-errors.md (Action Errors section)"
        )
        showed_hint = True
    if has("docker", "container"):
        log_reference(
            "Docker/container issues - see references/act-usage.md (Troubleshooting section)"
        )
        showed_hint = True
    if has("needs:", "dependency", "job"):
        log_reference(
            "Job dependency issues - see references/common-errors.md (Job Configuration Errors section)"
        )
        showed_hint = True
    if has("injection", "security", "secret", "untrusted"):
        log_reference(
            "Security issues detected - see references/common-errors.md (Security section)"
        )
        showed_hint = True
    if has(
        "workflow_call",
        "reusable",
        "oidc",
        "id-token",
        "attestation",
        "environment:",
        "permissions:",
    ):
        log_reference("Modern features - see references/modern-features.md")
        showed_hint = True
    if has("version", "deprecated", "outdated") or re.search(r"v\d", lower):
        log_reference("Action versions - see references/action-versions.md")
        showed_hint = True
    if has("glob", "paths:", "paths-ignore", "pattern"):
        log_reference(
            "Path filter issues - see references/common-errors.md (Path Filter Errors section)"
        )
        showed_hint = True

    if not showed_hint:
        log_reference("No direct mapping found for this error output")
        log_reference(
            "Fallback: check references/common-errors.md, then search the exact error text in official docs"
        )
        log_reference("Include exact tool output, workflow file, and line number in your report")


def check_tools(run_actionlint: bool, run_act: bool, allow_fallback: bool) -> tuple[bool, bool]:
    missing = False

    if run_actionlint and not tool_exists("actionlint"):
        if allow_fallback and run_act and tool_exists("act"):
            log_warn("actionlint not found. Falling back to act-only validation.")
            run_actionlint = False
        else:
            log_error("actionlint not found.")
            missing = True

    if run_act and not tool_exists("act"):
        if allow_fallback and run_actionlint and tool_exists("actionlint"):
            log_warn("act not found. Falling back to actionlint-only validation.")
            run_act = False
        else:
            log_error("act not found.")
            missing = True

    if missing:
        log_info("Install act: https://github.com/nektos/act#installation")
        log_info("Install actionlint: https://github.com/rhysd/actionlint#installation")
        log_info("See SKILL.md's Initial Setup section for details.")
        sys.exit(1)

    return run_actionlint, run_act


def get_tool_path(tool_name: str) -> str:
    candidate = TOOLS_DIR / tool_name
    if candidate.is_file():
        return str(candidate)
    found = shutil.which(tool_name)
    if found:
        return found
    log_error(f"{tool_name} not found")
    sys.exit(1)


def validate_with_actionlint(workflow_path: str) -> tuple[int, str]:
    log_section("Running actionlint")
    actionlint_path = get_tool_path("actionlint")
    p = Path(workflow_path)

    if p.is_file():
        log_info(f"Validating: {workflow_path}")
        proc = subprocess.run([actionlint_path, workflow_path], capture_output=True, text=True)
        output = proc.stdout + proc.stderr
        if output:
            print(output, end="" if output.endswith("\n") else "\n")
        if proc.returncode == 0:
            log_info("✓ actionlint validation passed")
            return 0, output
        log_error("✗ actionlint found issues")
        return 1, output

    if p.is_dir():
        log_info(f"Validating all workflows in: {workflow_path}")
        workflow_files = sorted(
            str(f) for f in p.iterdir() if f.is_file() and f.suffix in (".yml", ".yaml")
        )
        if not workflow_files:
            log_warn(f"No workflow files found in: {workflow_path}")
            return 0, ""
        proc = subprocess.run([actionlint_path, *workflow_files], capture_output=True, text=True)
        output = proc.stdout + proc.stderr
        if output:
            print(output, end="" if output.endswith("\n") else "\n")
        if proc.returncode == 0:
            log_info(f"✓ actionlint validation passed for {len(workflow_files)} file(s)")
            return 0, output
        log_error("✗ actionlint found issues")
        return 1, output

    log_error(f"Path not found: {workflow_path}")
    return 1, ""


RUNNER_IMAGES = [
    "-P",
    "ubuntu-latest=catthehacker/ubuntu:act-latest",
    "-P",
    "ubuntu-22.04=catthehacker/ubuntu:act-22.04",
    "-P",
    "ubuntu-20.04=catthehacker/ubuntu:act-20.04",
]


def _find_repo_root(search_path: Path) -> Path | None:
    current = search_path
    while True:
        if (current / ".github" / "workflows").is_dir():
            return current
        s = str(current)
        if "/.github/workflows" in s:
            candidate = Path(s.split("/.github/workflows")[0])
            if (candidate / ".github" / "workflows").is_dir():
                return candidate
        if current.parent == current:
            break
        current = current.parent

    if (Path.cwd() / ".github" / "workflows").is_dir():
        return Path.cwd()
    return None


def test_with_act(workflow_path: str) -> tuple[int, str]:
    """Returns (result_code, skip_reason). result_code: 0=pass, 1=fail, 2=skipped."""
    log_section("Running act (validation)")

    if not check_docker():
        log_error("Docker is not running!")
        log_warn("act requires Docker to validate and test workflows.")
        log_warn("")
        log_warn("Solutions:")
        log_warn("  1. Start Docker Desktop or Docker daemon")
        log_warn("  2. Use --lint-only flag to skip act testing")
        log_warn("")
        return 1, ""

    act_path = get_tool_path("act")
    abs_workflow_path = Path(workflow_path).resolve()
    search_path = abs_workflow_path.parent if abs_workflow_path.is_file() else abs_workflow_path

    repo_root = _find_repo_root(search_path)
    if repo_root is None:
        log_warn("No .github/workflows directory found in path hierarchy")
        log_warn("Skipping act validation - workflows must be in .github/workflows/ directory")
        log_info(f"Searched from: {workflow_path}")
        return 2, "no .github/workflows directory found in path hierarchy"

    log_info(f"Repository root: {repo_root}")

    workflow_flag: list[str] = []
    target_description = ""

    if abs_workflow_path.is_file():
        if "/.github/workflows/" in str(abs_workflow_path):
            rel = str(abs_workflow_path.relative_to(repo_root))
            workflow_flag = ["-W", rel]
            target_description = f"workflow: {abs_workflow_path.name}"
        else:
            log_warn(f"Target file is outside .github/workflows/: {abs_workflow_path}")
            log_warn("act can only validate workflows in .github/workflows/ directory")
            log_info("Skipping act validation for this file")
            log_info("Note: actionlint validation still applies to this file")
            return 2, "target file is outside .github/workflows"
    elif abs_workflow_path.is_dir():
        if (
            str(abs_workflow_path).endswith("/.github/workflows")
            or abs_workflow_path == repo_root / ".github" / "workflows"
        ):
            target_description = "all workflows in .github/workflows/"
        else:
            log_warn(f"Target directory is outside .github/workflows/: {abs_workflow_path}")
            log_warn("act can only validate workflows in .github/workflows/ directory")
            log_info("Skipping act validation for this directory")
            return 2, "target directory is outside .github/workflows"
    else:
        return 1, ""

    log_info(f"Target: {target_description}")
    log_info("Step 1: Listing workflows...")
    print()

    list_cmd = [act_path, "--list", *workflow_flag, *RUNNER_IMAGES]
    log_info(f"Running: act --list {' '.join(workflow_flag)}")
    list_proc = subprocess.run(list_cmd, cwd=repo_root, capture_output=True, text=True)
    list_output = list_proc.stdout + list_proc.stderr
    print("\n".join(list_output.splitlines()[:30]))
    if list_proc.returncode != 0:
        log_warn("Could not list workflows - this may indicate parsing issues")
        print()
    else:
        print()
        log_info("✓ Workflow listing successful")

    print()
    log_info("Step 2: Validating workflow syntax with dry-run...")
    log_info("Note: This validates workflow structure without executing jobs")
    log_info("Using medium-sized runner images (catthehacker/ubuntu:act-*)")
    print()

    dryrun_cmd = [
        act_path,
        "--dryrun",
        *workflow_flag,
        "--container-architecture",
        "linux/amd64",
        *RUNNER_IMAGES,
    ]
    log_info(
        f"Running: act --dryrun {' '.join(workflow_flag)} --container-architecture linux/amd64"
    )
    dryrun_proc = subprocess.run(dryrun_cmd, cwd=repo_root, capture_output=True, text=True)
    act_output = dryrun_proc.stdout + dryrun_proc.stderr
    act_exit_code = dryrun_proc.returncode

    print(act_output)
    print()

    if act_exit_code == 0:
        log_info("✓ act validation passed")
        return 0, ""

    lowered = act_output.lower()
    if "eof" in lowered:
        log_error("✗ act encountered EOF error")
        log_warn("This should not happen with -P flags set")
        log_info("Try running: act --list manually to diagnose")
        return 1, ""
    if "unable to get git repo" in act_output:
        log_warn("Not a git repository - some act features limited")
        log_info("act validation completed with warnings")
        return 0, ""
    if "pull access denied" in lowered or re.search(r"image.*not found", lowered):
        log_error("✗ Docker image pull failed")
        log_warn("Cannot pull runner images. This may be due to:")
        log_warn("  - Docker registry connectivity issues")
        log_warn("  - Rate limiting")
        log_warn("First-time run will download ~500MB of images")
        return 1, ""
    if "error" in lowered or "failed" in lowered:
        log_error(f"✗ act validation failed (exit code: {act_exit_code})")
        log_warn("This may indicate:")
        log_warn("  - Workflow syntax errors")
        log_warn("  - Invalid action references")
        log_warn("  - Docker image issues")
        log_warn("  - Configuration problems")
        return 1, ""

    log_warn(f"act completed with warnings (exit code: {act_exit_code})")
    return 0, ""


def usage(prog: str, exit_code: int = 0) -> None:
    print(f"Usage: {prog} [OPTIONS] <workflow-file-or-directory>")
    print()
    print("Options:")
    print("  --lint-only       Run only actionlint validation")
    print("  --test-only       Run only act testing (requires Docker)")
    print("  --check-versions  Check action versions against recommended versions")
    print("  --policy-checks   Run advisory security policy checks (warnings only)")
    print("  --help            Display this help message")
    print()
    print("Examples:")
    print(f"  {prog} .github/workflows/ci.yml")
    print(f"  {prog} .github/workflows/")
    print(f"  {prog} --lint-only .github/workflows/ci.yml")
    print(f"  {prog} --test-only .github/workflows/")
    print(f"  {prog} --check-versions .github/workflows/ci.yml")
    print(f"  {prog} --lint-only --policy-checks .github/workflows/ci.yml")
    print()
    print("Requirements:")
    print("  - actionlint: For static analysis (see SKILL.md's Initial Setup for installation)")
    print("  - act: For workflow testing (see SKILL.md's Initial Setup for installation)")
    print("  - Docker: Required for act to run (must be running)")
    print()
    sys.exit(exit_code)


def main(argv: list[str]) -> int:
    prog = "validate_workflow.py"
    workflow_path = ""
    lint_only = False
    test_only = False
    check_versions = False
    policy_checks = False

    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--lint-only":
            lint_only = True
        elif arg == "--test-only":
            test_only = True
        elif arg == "--check-versions":
            check_versions = True
        elif arg == "--policy-checks":
            policy_checks = True
        elif arg == "--help":
            usage(prog, 0)
        else:
            workflow_path = arg

    if not workflow_path:
        log_error("No workflow file or directory specified")
        print()
        usage(prog, 1)

    if lint_only and test_only:
        log_error("Cannot combine --lint-only and --test-only")
        return 1

    if test_only:
        run_actionlint, run_act = False, True
    elif lint_only:
        run_actionlint, run_act = True, False
    else:
        run_actionlint, run_act = True, True

    allow_tool_fallback = not (lint_only or test_only)

    version_only = False
    if check_versions and not lint_only and not test_only and not policy_checks:
        version_only = True
        run_actionlint, run_act = False, False
        allow_tool_fallback = False

    log_section("GitHub Actions Validator")
    log_info(f"Target: {workflow_path}")

    run_actionlint, run_act = check_tools(run_actionlint, run_act, allow_tool_fallback)

    docker_available = True
    if run_act:
        if not precheck_docker():
            if test_only:
                log_error("Docker is required for --test-only mode")
                return 1
            if run_actionlint:
                docker_available = False
                run_act = False
                log_warn("Proceeding without act because Docker is unavailable")
            else:
                log_error("Docker is required for act validation in the selected mode")
                return 1

    exit_code = 0
    actionlint_output = ""

    if check_versions:
        if check_action_versions(workflow_path) != 0:
            exit_code = 1
        if version_only:
            log_section("Version Check Complete")
            return exit_code

    did_actionlint = False
    if run_actionlint:
        did_actionlint = True
        result, actionlint_output = validate_with_actionlint(workflow_path)
        if result != 0:
            exit_code = 1

    if policy_checks:
        if check_security_policies(workflow_path) != 0:
            exit_code = 1

    did_act = False
    act_skip_reason = ""
    if run_act and docker_available:
        act_result, skip_reason = test_with_act(workflow_path)
        if act_result == 0:
            did_act = True
        elif act_result == 2:
            act_skip_reason = skip_reason
            log_warn(f"act validation skipped: {act_skip_reason}")
            if not did_actionlint:
                log_error(
                    "No effective validator executed: act was skipped and actionlint did not run"
                )
                exit_code = 1
        else:
            exit_code = 1

    if not version_only and not did_actionlint and not did_act:
        log_error("No validator executed; refusing to report success")
        exit_code = 1

    log_section("Validation Summary")
    if exit_code == 0:
        if act_skip_reason:
            log_info(f"✓ Validation passed (actionlint completed; act skipped: {act_skip_reason})")
        else:
            log_info("✓ All validations passed")
    else:
        log_error("✗ Some validations failed")
        if actionlint_output:
            show_reference_hints(actionlint_output)
        print()
        log_info("Tips:")
        log_info("  - Review error messages above")
        log_info("  - Use --lint-only to skip Docker-dependent tests")
        log_info("  - Use --check-versions to check for outdated actions")
        log_info("  - Use --policy-checks for security hardening warnings")
        log_info("  - Check references/common-errors.md for solutions")

    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
