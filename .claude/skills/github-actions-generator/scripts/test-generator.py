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
  7. Script injection risk  - no untrusted ${{ }} context interpolated directly
                              into a run: block or an actions/github-script
                              script: block anywhere in templates/ or examples/

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

    # Canonical SHAs, sourced from references/common-actions.md. If common-actions.md is
    # updated, update these constants to match.
    canonical_shas = {
        "actions/checkout": ("de0fac2e4500dabe0009e67214ff5f5447ce83dd", "v6.0.2"),
        "actions/setup-node": ("6044e13b5dc448c55e2357c09f80417699197238", "v6.2.0"),
        "actions/cache": ("cdf6c1fa76f9f475f3d7449005a359c84ca0f306", "v5.0.3"),
        "actions/upload-artifact": ("043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", "v7.0.1"),
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
        r"^[ \t]*(?:-\s*)?uses:[ \t]*[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*"
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
    assert_text_matches_pattern(
        "matches compact single-line step form (- uses:)",
        "      - uses: actions/dependency-review-action@v4",
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

    # --- 7. Script injection risk ---
    print("[7] Script injection risk (no untrusted ${{ }} interpolated into run:/script: blocks)")
    # Mirrors the untrusted-context heuristic in
    # ../github-actions-validator/scripts/validate_workflow.py's find_injection_risk_lines
    # (re-implemented inline here rather than imported, to avoid a runtime dependency on a
    # sibling skill's internal script layout), extended to also cover actions/github-script
    # `script:` blocks (JS), not just `run:` blocks; inline `run: <command>`/`script: <command>`
    # single-line forms, not just block-scalar (`run: |`) forms; and this plugin's own
    # bracketed template-placeholder convention (`inputs.[input-name]`,
    # `steps.[step-id].outputs.[output-name]`, `needs.[job-id].outputs.[output-name]`), alongside
    # the un-bracketed real-usage form. A value from these contexts is attacker-influenced
    # (event/PR data, a prior job's outputs, a composite action's inputs) and must be passed
    # through `env:` + $VAR (shell) or process.env.VAR (JS) rather than substituted directly
    # into the run/script source text by ${{ }} — a raw substitution happens before the
    # shell/JS is parsed and can break out of a string.
    expr_label = "${{ }}"
    # Matches either a real identifier (`input-name`) or this plugin's own bracketed
    # placeholder convention (`[input-name]`) so template files (which use the latter) and
    # generated/real usage (which uses the former) are both covered.
    id_re = r"(?:[\w-]+|\[[\w-]+\])"
    injection_context_re = re.compile(
        r"\$\{\{\s*(?:"
        r"github\.(?:event|head_ref|ref_name|actor|triggering_actor|repository_owner|base_ref)"
        rf"|needs\.{id_re}\.outputs\.{id_re}"
        rf"|steps\.{id_re}\.outputs\.{id_re}"
        rf"|inputs\.{id_re}"
        r")"
    )
    run_block_start_re = re.compile(r"^\s*run:\s*[|>][-+]?\d*\s*$")
    script_block_start_re = re.compile(r"^\s*script:\s*[|>][-+]?\d*\s*$")
    # Inline single-line form: `run: <command>` / `script: <command>` (optionally under a
    # `- ` step-list dash). Block-scalar starts (`run: |`, `run: >-`, ...) are matched and
    # `continue`d past by the two regexes above before this one is ever consulted, so this
    # only ever matches a real inline command.
    inline_run_script_re = re.compile(r"^\s*(?:-\s*)?(run|script):\s*(\S.*)$")

    def find_injection_risk_lines(lines: list[str]) -> list[tuple[int, str]]:
        risky: list[tuple[int, str]] = []
        in_block = False
        block_kind = ""
        block_indent = -1
        for idx, line in enumerate(lines, start=1):
            indent = len(line) - len(line.lstrip(" "))
            if in_block and indent <= block_indent and line.strip() != "":
                in_block = False
            if run_block_start_re.match(line):
                in_block = True
                block_kind = "run"
                block_indent = indent
                continue
            if script_block_start_re.match(line):
                in_block = True
                block_kind = "script"
                block_indent = indent
                continue
            if in_block and injection_context_re.search(line):
                risky.append((idx, block_kind))
                continue
            if not in_block:
                inline_match = inline_run_script_re.match(line)
                if inline_match and injection_context_re.search(inline_match.group(2)):
                    risky.append((idx, f"{inline_match.group(1)}-inline"))
        return risky

    print("  [7a] Detector regression checks")

    def assert_injection_detected(label: str, sample_lines: list[str]) -> None:
        if find_injection_risk_lines(sample_lines):
            ok(label)
        else:
            bad(f"{label} — expected risky interpolation was not detected")

    def assert_injection_not_detected(label: str, sample_lines: list[str]) -> None:
        if not find_injection_risk_lines(sample_lines):
            ok(label)
        else:
            bad(f"{label} — unexpected risky interpolation flagged")

    assert_injection_detected(
        "detects un-bracketed inputs.<name> inside a run: | block",
        ["      run: |", '        echo "${{ inputs.foo }}"'],
    )
    assert_injection_detected(
        "detects bracketed inputs.[input-name] inside a run: | block "
        "(this plugin's template placeholder form)",
        ["      run: |", '        echo "${{ inputs.[input-name] }}"'],
    )
    assert_injection_detected(
        "detects bracketed steps.[step-id].outputs.[output-name] inside a run: | block",
        ["      run: |", '        echo "${{ steps.[step-id].outputs.[output-name] }}"'],
    )
    assert_injection_detected(
        "detects bracketed needs.[job-id].outputs.[output-name] inside a run: | block",
        ["      run: |", '        echo "${{ needs.[job-id].outputs.[output-name] }}"'],
    )
    assert_injection_detected(
        "detects an inline run: <command> single-line form with a risky expression",
        ['      run: echo "${{ inputs.[input-name] }}"'],
    )
    assert_injection_detected(
        "detects an inline script: <command> single-line form with a risky expression",
        ['      script: console.log("${{ steps.[step-id].outputs.[output-name] }}")'],
    )
    assert_injection_not_detected(
        "does not flag inputs.[input-name] referenced only via an env: block, "
        "with the run: block itself using $VAR",
        [
            "      env:",
            "        INPUT_VALUE: ${{ inputs.[input-name] }}",
            "      run: |",
            '        echo "$INPUT_VALUE"',
        ],
    )
    assert_injection_not_detected(
        "does not flag a plain inline run: command with no ${{ }} expression",
        ["      run: npm ci"],
    )
    print()

    for f in all_yaml_files:
        lines = f.read_text(encoding="utf-8").splitlines()
        risky = find_injection_risk_lines(lines)
        if not risky:
            ok(f"no risky {expr_label} interpolation in run:/script: blocks: {rel(f)}")
        else:
            bad(f"risky {expr_label} interpolated directly into a run:/script: block: {rel(f)}")
            for line_no, kind in risky:
                print(f"    {line_no} [{kind}]: {lines[line_no - 1].strip()}")
    print()

    print(f"Results: {PASS} passed, {FAIL} failed")
    print()

    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
