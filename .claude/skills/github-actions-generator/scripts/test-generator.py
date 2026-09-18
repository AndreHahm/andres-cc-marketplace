#!/usr/bin/env python3
"""Regression test suite for github-actions-generator.

Tests:
  1. YAML syntax validity   - all templates and examples parse without errors
  2. SHA pinning compliance - no unpinned @vN action refs in positive examples
  3. EOF newlines           - all YAML files end with a newline
  4. SHA consistency        - templates/examples use the canonical SHAs from
                              references/common-actions.md
  5. Required workflow keys - example workflows contain mandatory top-level keys
  6. Template placeholders  - workflow/docker templates keep safe placeholders

Prerequisites: yamllint must be installed (pip install yamllint)

Exit 0 when all assertions pass; non-zero on any failure.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

PASS = 0
FAIL = 0


def ok(label: str) -> None:
    global PASS
    print(f"  PASS: {label}")
    PASS += 1


def bad(label: str) -> None:
    global FAIL
    print(f"  FAIL: {label}")
    FAIL += 1


def rel(path: Path) -> str:
    return str(path.relative_to(SKILL_DIR))


def assert_file_contains(label: str, file: Path, pattern: str) -> None:
    text = file.read_text(encoding="utf-8")
    if re.search(pattern, text, re.MULTILINE):
        ok(label)
    else:
        bad(f"{label} — pattern '{pattern}' not found in {file}")


def assert_file_not_contains(label: str, file: Path, pattern: str) -> None:
    text = file.read_text(encoding="utf-8")
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    if not matches:
        ok(label)
    else:
        bad(f"{label} — unexpected pattern '{pattern}' found in {file}")
        for m in matches:
            line_no = text.count("\n", 0, m.start()) + 1
            print(f"    {line_no}:{m.group(0)}")


def assert_file_ends_with_newline(label: str, file: Path) -> None:
    data = file.read_bytes()
    if data and data[-1:] == b"\n":
        ok(label)
    else:
        bad(f"{label} — {file} is missing a trailing newline")


def assert_text_matches_pattern(label: str, text: str, pattern: str) -> None:
    if re.search(pattern, text):
        ok(label)
    else:
        bad(f"{label} — text did not match pattern '{pattern}': {text}")


def assert_text_not_matches_pattern(label: str, text: str, pattern: str) -> None:
    if not re.search(pattern, text):
        ok(label)
    else:
        bad(f"{label} — text unexpectedly matched pattern '{pattern}': {text}")


def yamllint_errors(file: Path) -> str:
    proc = subprocess.run(
        ["yamllint", "-d", "relaxed", str(file)],
        capture_output=True,
        text=True,
    )
    output = proc.stdout + proc.stderr
    lines = [line for line in output.splitlines() if "error" in line and "line-length" not in line]
    return "\n".join(lines)


def main() -> int:
    template_files = sorted((SKILL_DIR / "assets" / "templates").glob("**/*.yml"))
    example_files = sorted((SKILL_DIR / "examples").glob("**/*.yml"))
    all_yaml_files = template_files + example_files

    print(
        f"Discovered {len(template_files)} template file(s) and "
        f"{len(example_files)} example file(s)."
    )
    print()

    # Canonical SHAs, sourced from references/common-actions.md.
    # If common-actions.md is updated, update these constants to match.
    canonical_shas = {
        "actions/checkout": ("de0fac2e4500dabe0009e67214ff5f5447ce83dd", "v6.0.2"),
        "actions/setup-node": ("6044e13b5dc448c55e2357c09f80417699197238", "v6.2.0"),
        "actions/cache": ("cdf6c1fa76f9f475f3d7449005a359c84ca0f306", "v5.0.3"),
        "actions/upload-artifact": ("5d5d22a31266ced268874388b861e4b58bb5c2f3", "v4.3.1"),
        "actions/download-artifact": ("c850b930e6ba138125429b7e5c93fc707a7f8427", "v4.1.4"),
        "actions/github-script": ("60a0d83039c74a4aee543508d2ffcb1c3799cdea", "v7.0.1"),
        "actions/dependency-review-action": ("05fe4576374b728f0c523d6a13d64c25081e0803", "v4.8.3"),
        "actions/attest-sbom": ("bd218ad0dbcb3e146bd073d1d9c6d78e08aa8a0b", "v2.4.0"),
        "actions/attest-build-provenance": ("e8998f949152b193b063cb0ec769d69d929409be", "v2.4.0"),
        "github/codeql-action/init": ("ae9ef3a1d2e3413523c3741725c30064970cc0d4", "v3.32.5"),
        "github/codeql-action/analyze": ("ae9ef3a1d2e3413523c3741725c30064970cc0d4", "v3.32.5"),
        "github/codeql-action/upload-sarif": (
            "ae9ef3a1d2e3413523c3741725c30064970cc0d4",
            "v3.32.5",
        ),
        "actions/setup-python": ("a309ff8b426b58ec0e2a45f0f869d46889d02405", "v6.2.0"),
        "aws-actions/configure-aws-credentials": (
            "61815dcd50bd041e203e49132bacad1fd04d2708",
            "v5.1.1",
        ),
        "docker/metadata-action": ("8e5442c4ef9f78752691e2d8f8d19755c6f78e81", "v5.5.1"),
        "anchore/sbom-action": ("fbfd9c6c189226748411491745178e0c2017392d", "v0.20.10"),
        "aquasecurity/trivy-action": ("b6643a29fecd7f34b3597bc6acb0a98b03d33ff8", "v0.33.1"),
        "hashicorp/setup-terraform": ("b9cd54a3c349d3f38e8881555d616ced269862dd", "v3.1.2"),
        "dorny/paths-filter": ("de90cc6551a0c30ca4af50ac82dafbf57eb22fab", "v3.0.2"),
        "golangci/golangci-lint-action": ("e7fa5ac41e1cf5b7d48e45e42232ce7ada589601", "v9.1.0"),
        "actions/cache/save": ("0c45773b623bea8c8e75f6c82b208c3cf94ea4f9", "v4.0.2"),
    }

    # --- 1. YAML syntax validity ---
    print("[1] YAML syntax validity")
    if not shutil.which("yamllint"):
        bad("yamllint not installed — skipping YAML syntax checks")
    else:
        for f in all_yaml_files:
            errors = yamllint_errors(f)
            if not errors:
                ok(f"valid YAML: {rel(f)}")
            else:
                bad(f"YAML error in: {rel(f)}")
                print("\n".join(f"    {line}" for line in errors.splitlines()))
    print()

    # --- 2. SHA pinning compliance ---
    print("[2] SHA pinning compliance (no bare @vN refs in positive examples)")
    unpinned_pattern = (
        r"^[ \t]*uses:[ \t]*[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*"
        r"@v[0-9]+(\.[0-9]+){0,2}([ \t]|$)"
    )

    print("  [2a] Regex regression checks")
    assert_text_matches_pattern(
        "matches top-level action major tag",
        "        uses: actions/dependency-review-action@v4",
        unpinned_pattern,
    )
    assert_text_matches_pattern(
        "matches nested action path major tag",
        "        uses: github/codeql-action/upload-sarif@v3",
        unpinned_pattern,
    )
    assert_text_matches_pattern(
        "matches nested action path semver tag",
        "        uses: owner/repo/sub-path@v3.2.1 # mutable",
        unpinned_pattern,
    )
    assert_text_not_matches_pattern(
        "does not match full SHA pin",
        "        uses: github/codeql-action/upload-sarif@"
        "ae9ef3a1d2e3413523c3741725c30064970cc0d4 # v3.32.5",
        unpinned_pattern,
    )

    for f in template_files + example_files:
        text = f.read_text(encoding="utf-8")
        unpinned = [
            f"{i}:{line}"
            for i, line in enumerate(text.splitlines(), start=1)
            if re.search(unpinned_pattern, line, re.MULTILINE)
        ]
        if not unpinned:
            ok(f"no unpinned refs: {rel(f)}")
        else:
            bad(f"unpinned action ref(s) in: {rel(f)}")
            print("\n".join(f"    {line}" for line in unpinned))
    print()

    # --- 3. EOF newlines ---
    print("[3] EOF newlines (all YAML files must end with a newline)")
    for f in all_yaml_files:
        assert_file_ends_with_newline(f"EOF newline: {rel(f)}", f)
    print()

    # --- 4. SHA consistency ---
    print("[4] SHA consistency (templates and examples match canonical SHAs)")

    def check_sha_consistency(action: str, expected_sha: str, file: Path) -> None:
        text = file.read_text(encoding="utf-8")
        wrong = []
        for line in text.splitlines():
            if f"uses: {action}@" not in line:
                continue
            if expected_sha in line:
                continue
            if re.search(r"#.*BAD|#.*UNSAFE|#.*AVOID|#.*-.*uses:", line):
                continue
            wrong.append(line)
        if not wrong:
            ok(f"SHA consistent for {action}: {rel(file)}")
        else:
            bad(f"Wrong SHA for {action} in: {rel(file)}")
            print("\n".join(f"    {line}" for line in wrong))
            print(f"    Expected SHA: {expected_sha}")

    for f in template_files + example_files:
        text = f.read_text(encoding="utf-8")
        for action, (sha, _version) in canonical_shas.items():
            if f"uses: {action}@" in text:
                check_sha_consistency(action, sha, f)
    print()

    # --- 5. Required workflow keys ---
    print("[5] Required workflow keys (name, on, permissions, jobs)")
    workflow_examples = (
        sorted((SKILL_DIR / "examples" / "workflows").glob("*.yml"))
        + sorted((SKILL_DIR / "examples" / "security").glob("*.yml"))
        + sorted((SKILL_DIR / "examples" / "triggers").glob("*.yml"))
        + sorted((SKILL_DIR / "examples" / "caching").glob("*.yml"))
        + sorted((SKILL_DIR / "assets" / "templates" / "workflow").glob("*.yml"))
    )
    for f in workflow_examples:
        assert_file_contains(f"has 'name:' key: {rel(f)}", f, r"^name:")
        assert_file_contains(f"has 'on:' trigger: {rel(f)}", f, r"^on:")
        assert_file_contains(f"has 'permissions:' key: {rel(f)}", f, r"permissions:")
        assert_file_contains(f"has 'jobs:' key: {rel(f)}", f, r"^jobs:")
    print()

    # --- 6. Template placeholder integrity ---
    print("[6] Template placeholder integrity")
    basic_template = SKILL_DIR / "assets" / "templates" / "workflow" / "basic-workflow.yml"
    docker_template = SKILL_DIR / "assets" / "templates" / "action" / "docker" / "Dockerfile"

    assert_file_contains(
        "basic-workflow.yml: bracketed step name is quoted",
        basic_template,
        r'name: "\[SETUP_STEP_NAME\]',
    )

    if shutil.which("yamllint"):
        errors = yamllint_errors(basic_template)
        if not errors:
            ok("basic-workflow.yml: no YAML syntax errors")
        else:
            bad("basic-workflow.yml: YAML syntax errors found")
            print("\n".join(f"    {line}" for line in errors.splitlines()))

    assert_file_contains(
        "docker action template: has package-install flags placeholder",
        docker_template,
        r"\[PACKAGE_INSTALL_FLAGS\]",
    )
    assert_file_not_contains(
        "docker action template: no apt-only hardcoded install flags",
        docker_template,
        r"--no-install-recommends",
    )
    print()

    print(f"Results: {PASS} passed, {FAIL} failed")
    print()

    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
