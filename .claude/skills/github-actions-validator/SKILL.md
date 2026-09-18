---
name: github-actions-validator
description: Validate, lint, and fix GitHub Actions workflow and action files (.github/workflows) using actionlint and act — syntax, security, action-version, and CI-pitfall checks (cache paths, monorepo build order, service containers). Operates on workflow YAML files themselves, not run history or logs.
allowed-tools: Read Edit WebSearch Bash(python3 */github-actions-validator/scripts/validate_workflow.py:*) Bash(actionlint:*) Bash(act:*)
---

# GitHub Actions Validator

## Overview

Validate and test GitHub Actions workflows, custom actions, and public actions using industry-standard tools (actionlint and act). This skill provides comprehensive validation including syntax checking, static analysis, local workflow execution testing, and action verification with version-aware documentation lookup.

## Trigger Phrases

Use this skill when the request includes phrases like:
- "validate this GitHub Actions workflow"
- "check my `.github/workflows/*.yml` file"
- "debug actionlint errors"
- "test this workflow locally with act"
- "verify GitHub Action versions or deprecations"

## When to Use

Use this skill when:
- **Validating workflow files**: Checking `.github/workflows/*.yml` for syntax errors and best practices
- **Testing workflows locally**: Running workflows with `act` before pushing to GitHub
- **Debugging workflow failures**: Identifying issues in workflow configuration
- **Validating custom actions**: Checking composite, Docker, or JavaScript actions
- **Verifying public actions**: Validating usage of actions from GitHub Marketplace
- **Pre-commit validation**: Ensuring workflows are valid before committing

## When NOT to Use

This skill validates and fixes *existing* workflow/action YAML — it doesn't generate new files, score
static hardening risk from a config perspective, analyze run history, or analyze run logs. Use a
sibling `github-actions-kit` skill instead for those:
- **`github-actions-generator`** — scaffolding a new workflow or custom action from scratch (this
  skill auto-invokes `github-actions-validator` on its own output, so you rarely need to call this
  skill directly after generating).
- **`github-actions-hardening-audit`** — a static hardening/risk *score* across many workflow files
  (missing timeout/permissions/concurrency, floating refs) rather than an actionlint/act pass over one.
- **`github-actions-conclusion-audit`** — detecting flaky/unstable workflows from run-history JSON, not
  from the workflow file itself.
- **`github-actions-log-analyzer`** — analyzing recent run *logs* for wasted effort/mistakes, not
  validating the workflow definition.

## Quick Start

Set once per shell session:

```bash
SKILL_DIR="${CLAUDE_PLUGIN_ROOT}/skills/github-actions-validator"
```

### Initial Setup

This skill requires **act** and **actionlint** to be installed and available on `PATH` (or placed
in `scripts/.tools/`) before running any validation. It does not auto-install them.

```bash
command -v act >/dev/null || echo "act not found"
command -v actionlint >/dev/null || echo "actionlint not found"
```

If either is missing, install it manually from its own upstream instructions:
- **act**: https://github.com/nektos/act#installation
- **actionlint**: https://github.com/rhysd/actionlint#installation

`scripts/validate_workflow.py` performs this same check itself and prints these same links if a
required tool is missing — you don't need to pre-check before running it.

## Validation Procedure

Every validation run should follow these steps in order.

### Step 1: Run Validation

Run commands from the repository root that contains `.github/workflows/`.

```bash
# Full validation (actionlint + act, the default)
python3 "$SKILL_DIR/scripts/validate_workflow.py" .github/workflows/ci.yml

# Lint-only (fastest — static analysis only, no Docker required)
python3 "$SKILL_DIR/scripts/validate_workflow.py" --lint-only .github/workflows/ci.yml

# Test-only with act (local dry-run execution, requires Docker)
python3 "$SKILL_DIR/scripts/validate_workflow.py" --test-only .github/workflows/

# Add security hardening warnings (advisory, any mode)
python3 "$SKILL_DIR/scripts/validate_workflow.py" --lint-only --policy-checks .github/workflows/ci.yml
```

**What actionlint checks:** YAML syntax, schema compliance, expression syntax, runner labels, action
inputs/outputs, job dependencies, CRON syntax, glob patterns, shell scripts, security vulnerabilities.

**What act checks:** structural/dry-run validation of workflow execution (`act --list` then
`act --dryrun`) — not a full run. Act has real limitations (see `references/act-usage.md`); a
workflow that passes here can still behave differently on GitHub's actual runners.

**Resource-type notes:**
- **Workflows** — validate a single file or `.github/workflows/` as a whole; key points checked are
  triggers, job configurations, runner labels, environment variables, secrets, conditionals, matrix
  strategies.
- **Custom local actions** — create a test workflow that uses the custom action, then validate that
  workflow the same way.
- **Public actions** (e.g. `actions/checkout@v6`) — check `references/action-versions.md` first; for
  unknown actions, verify against official docs, confirm required inputs and deprecations, and use
  `--check-versions` to automate the comparison. Search format for unknown actions:
  `"[action-name] [version] github action documentation"`.

**Default fallback behavior if tools/runtime are unavailable:**
- If `act` is missing, full validation falls back to actionlint-only.
- If Docker is unavailable, full validation skips act and continues with actionlint.
- `--check-versions` and `--policy-checks` both work in fully offline/local mode.
- If offline and verifying an unknown public action, mark it `UNVERIFIED-OFFLINE` and avoid claiming
  "latest/current" until an online verification pass is possible.

### Step 2: Map Each Error to a Reference

For each actionlint/act error, consult the mapping table below, then extract the matching fix pattern.

| Error Pattern in Output | Reference File to Read | Section to Quote |
|------------------------|----------------------|------------------|
| `runs-on:`, `runner`, `ubuntu`, `macos`, `windows` | `references/runners.md` | Runner labels |
| `cron`, `schedule` | `references/common-errors.md` | Schedule Errors |
| `${{`, `expression`, `if:` | `references/common-errors.md` | Expression Errors |
| `needs:`, `job`, `dependency` | `references/common-errors.md` | Job Configuration Errors |
| `uses:`, `action`, `input` | `references/common-errors.md` | Action Errors |
| `untrusted`, `injection`, `security` | `references/common-errors.md` | Script Injection section |
| `syntax`, `yaml`, `unexpected` | `references/common-errors.md` | Syntax Errors |
| `docker`, `container` | `references/act-usage.md` | Troubleshooting |
| `@v3`, `@v4`, `deprecated`, `outdated` | `references/action-versions.md` | Version table |
| `workflow_call`, `reusable`, `oidc` | `references/modern-features.md` | Relevant section |
| `glob`, `path`, `paths:`, `pattern` | `references/common-errors.md` | Path Filter Errors |

### Step 3: Apply Minimal-Quote Policy

For each issue:
1. Include the exact error line from tool output.
2. Quote only the smallest useful snippet from `references/` (prefer <=8 lines).
3. Paraphrase the rest and cite the source file/section.
4. Show corrected workflow code.

### Step 4: Handle Unmapped Errors Explicitly

If an error does not match any mapping:
1. Label it as `UNMAPPED`.
2. Capture exact tool output, workflow file, and line number (if available).
3. Check `references/common-errors.md` general sections first.
4. If still unresolved, search official docs with the exact error string.
5. Mark the fix as `provisional` until post-fix rerun passes.

### Step 5: Verify Public Action Versions

For each `uses: owner/action@version`:
1. Check `references/action-versions.md`.
2. For unknown actions, verify against official docs.
3. Confirm required inputs and deprecations.

Offline mode: rely on `references/action-versions.md` only, mark unknown actions
`UNVERIFIED-OFFLINE`, and do not claim "latest" version without an online verification pass.

### Step 6: Check CI Pitfalls Static Tools Miss

`actionlint` and `act` catch syntax, schema, and dry-run issues, but not cache-dependency-path
misconfiguration, monorepo build-order mistakes, `npm ci` run from the wrong directory, or service
containers that ignore a custom `CMD` — these depend on real CI environment behavior, not YAML
correctness. When a workflow passes validation here but still fails on GitHub with a "works
locally, not in CI" shape, check `references/common-pitfalls.md` before assuming it's a tooling gap.

### Step 7: Mandatory Post-Fix Rerun

After applying fixes, rerun validation before finalizing:

```bash
python3 "$SKILL_DIR/scripts/validate_workflow.py" <workflow-file-or-directory>
```

### Step 8: Provide Final Summary

Final output should include:
- Issues found and fixes applied
- Any `UNMAPPED` or `UNVERIFIED-OFFLINE` items
- Post-fix rerun command and result
- Remaining warnings/risk notes

## Complete Worked Example: Multi-Error Workflow

This example demonstrates the **full assistant workflow** for handling multiple errors.

### User's Problematic Workflow

```yaml
name: Broken CI
on:
  schedule:
    - cron: '0 0 * * 8'  # ERROR 1
jobs:
  build:
    runs-on: ubuntu-lastest  # ERROR 2
    steps:
      - uses: actions/checkout@v3  # ERROR 3 (outdated)
      - run: echo ${{ github.event.issue.title }}  # ERROR 4 (security)
  deploy:
    needs: biuld  # ERROR 5 (typo)
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying"
```

### Example Phase 1: Run Validation

```bash
python3 "$SKILL_DIR/scripts/validate_workflow.py" --lint-only workflow.yml
```

**Output:**
```
[ERROR] invalid CRON format "0 0 * * 8"
[ERROR] label "ubuntu-lastest" is unknown
[WARN] "github.event.issue.title" is potentially untrusted
[ERROR] job "deploy" needs job "biuld" which does not exist
```

### Example Phase 2-3: Consult References and Quote Fixes (applying Steps 2-3 above)

---

**Error 1: Invalid CRON Expression**

*From `references/common-errors.md` - Schedule Errors:*

> **Cause:** Day of week 8 doesn't exist (valid: 0-6, where 0 = Sunday)
>
> ```yaml
> # Bad
> schedule:
>   - cron: '0 0 * * 8'  # Day 8 doesn't exist
>
> # Good
> schedule:
>   - cron: '0 0 * * 0'  # Sunday
> ```
>
> **CRON format:** `minute hour day month weekday`
> - Weekday: 0-6 (0 = Sunday)

**Fix:** Change `8` to `0` (Sunday) or `1-6` for Monday-Saturday.

---

**Error 2: Invalid Runner Label**

*From `references/common-errors.md` - Job Configuration Errors and `references/runners.md`:*

> **Cause:** Typo in runner label
>
> ```yaml
> # Bad
> runs-on: ubuntu-lastest  # Typo
>
> # Good
> runs-on: ubuntu-latest
> ```
>
> **Valid labels (from `references/runners.md`):**
> - `ubuntu-latest` (Ubuntu 24.04)
> - `ubuntu-24.04`, `ubuntu-22.04`
> - `macos-latest` (macOS 15)
> - `windows-latest` (Windows Server 2022)

**Fix:** Change `ubuntu-lastest` to `ubuntu-latest`.

---

**Error 3: Outdated Action Version**

*From `references/action-versions.md`:*

> | Action | Current Version | Minimum Supported |
> |--------|----------------|-------------------|
> | `actions/checkout` | **v6** | v4 |
>
> **SHA Pinning Best Practice:**
> ```yaml
> # Recommended: SHA pinning with version comment
> - uses: actions/checkout@1af3b93b6815bc44a9784bd300feb67ff0d1eeb3  # v6.0.0
> ```

**Fix:** Update from `@v3` to `@v6` (or SHA-pinned version).

---

**Error 4: Security Vulnerability (Script Injection)**

*From `references/common-errors.md` - Expression Errors:*

> **Warning:** Potential script injection via untrusted input
>
> ```yaml
> # Bad - vulnerable to injection
> run: echo ${{ github.event.issue.title }}
>
> # Good - use environment variables
> env:
>   TITLE: ${{ github.event.issue.title }}
> run: echo "$TITLE"
> ```
>
> **Why:** Untrusted input (issue titles, PR bodies, commit messages) can contain malicious commands. Using environment variables sanitizes the input.

**Fix:** Pass untrusted input through environment variable.

---

**Error 5: Undefined Job Dependency**

*From `references/common-errors.md` - Job Configuration Errors:*

> **Error:** Job 'deploy' depends on job 'biuld' which does not exist
>
> ```yaml
> # Bad
> jobs:
>   build:
>     runs-on: ubuntu-latest
>   deploy:
>     needs: biuld  # Typo
>
> # Good
> jobs:
>   build:
>     runs-on: ubuntu-latest
>   deploy:
>     needs: build
> ```

**Fix:** Change `biuld` to `build`.

---

### Example Phase 4: Provide Corrected Workflow

```yaml
name: Fixed CI
on:
  schedule:
    - cron: '0 0 * * 0'  # Fixed: Sunday (0-6 valid)
jobs:
  build:
    runs-on: ubuntu-latest  # Fixed: typo corrected
    steps:
      - uses: actions/checkout@1af3b93b6815bc44a9784bd300feb67ff0d1eeb3  # v6.0.0 - Fixed: updated version
      - name: Process issue
        env:
          TITLE: ${{ github.event.issue.title }}  # Fixed: use env var
        run: echo "$TITLE"
  deploy:
    needs: build  # Fixed: typo corrected
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying"
```

### Example Phase 5: Mandatory Rerun (applying Step 7 above)

```bash
python3 "$SKILL_DIR/scripts/validate_workflow.py" --lint-only workflow.yml
```

Expected rerun result:
- No previous errors reproduced
- Remaining warnings, if any, are documented explicitly

### Example Phase 6: Summary (applying Step 8 above)

| Error | Type | Fix Applied |
|-------|------|-------------|
| CRON `0 0 * * 8` | Schedule | Changed to `0 0 * * 0` |
| `ubuntu-lastest` | Runner | Changed to `ubuntu-latest` |
| `checkout@v3` | Outdated Action | Updated to `@v6.0.0` (SHA-pinned) |
| Direct `${{ }}` in run | Security | Wrapped in environment variable |
| `needs: biuld` | Job Dependency | Changed to `needs: build` |

**Recommendations:**
- Run `python3 "$SKILL_DIR/scripts/validate_workflow.py" --check-versions` regularly
- Use SHA pinning for all actions in production workflows
- Always pass untrusted input through environment variables

## Reference File Consultation Guide

| Situation | Reference File | Action |
|-----------|---------------|--------|
| actionlint reports any mapped error | `references/common-errors.md` | Find matching error and apply minimal quote policy |
| actionlint reports unmapped error | `references/common-errors.md` + official docs | Label as `UNMAPPED`, capture exact output and verify by rerun |
| act fails with Docker/runtime error | `references/act-usage.md` | Check Troubleshooting section |
| act fails but workflow works on GitHub | `references/act-usage.md` | Read Limitations section |
| User asks about actionlint config | `references/actionlint-usage.md` | Provide examples |
| User asks about act options | `references/act-usage.md` | Read Advanced Options |
| Security vulnerability detected | `references/common-errors.md` | Quote minimal safe fix snippet |
| Validating action versions | `references/action-versions.md` | Check version table and offline note |
| Using modern features | `references/modern-features.md` | Check syntax examples |
| Runner questions/errors | `references/runners.md` | Check labels and availability |
| CI passes locally but fails in a clean run (cache/monorepo/service-container shaped) | `references/common-pitfalls.md` | Check the matching pitfall and its fix |
| `--policy-checks` security warnings (SHA pinning, permissions, injection, OIDC) | `references/common-pitfalls.md` | See "Security Policy Checks (Advisory)" section |

## Reference Files Summary

| File | Content |
|------|---------|
| `references/act-usage.md` | Act tool usage, commands, options, limitations, troubleshooting |
| `references/actionlint-usage.md` | Actionlint validation categories, configuration, integration |
| `references/common-errors.md` | Common errors catalog with fixes |
| `references/action-versions.md` | Current action versions, deprecation timeline, SHA pinning |
| `references/modern-features.md` | Reusable workflows, SBOM, OIDC, environments, containers |
| `references/common-pitfalls.md` | Cache config, monorepo build order, npm ci, service containers, `--policy-checks` security checks |
| `references/runners.md` | GitHub-hosted runners (ARM64, GPU, M2 Pro, deprecations) |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Tools not found" | Install act/actionlint manually — see Initial Setup above |
| "Docker daemon not running" | Start Docker or use `--lint-only` |
| act fails but GitHub works | See `references/act-usage.md` Limitations |

### Debug Mode

```bash
actionlint -verbose .github/workflows/ci.yml  # Verbose actionlint
act -v                                         # Verbose act
act -n                                         # Dry-run (no execution)
```

## Limitations

- **act limitations**: Not all GitHub Actions features work locally
- **Docker requirement**: act requires Docker to be running
- **Network actions**: Some GitHub API actions may fail locally
- **Private actions**: Cannot validate without access
- **Runtime behavior**: Static analysis cannot catch all issues
- **File location**: act can only validate workflows in `.github/workflows/` directory; files outside (like `examples/`) can only be validated with actionlint

## Done Criteria

Validation work is complete when all are true:
- Trigger matched and correct validation mode selected.
- Each mapped error includes source reference and minimal quote.
- Each unmapped error is labeled `UNMAPPED` with exact output captured.
- Public action versions are verified, or marked `UNVERIFIED-OFFLINE`.
- Post-fix rerun executed and result reported.

## Testing & Validation

**Verify this skill activates on:**
- "validate this GitHub Actions workflow"
- "check my `.github/workflows/*.yml` file"
- "debug actionlint errors"

**Verify it does NOT activate on:**
- "generate a workflow for X" → `github-actions-generator`
- "score this workflow's hardening risk" → `github-actions-hardening-audit`
- "why does this workflow keep failing intermittently" → `github-actions-conclusion-audit`

**Quality gates:**
- [ ] `tests/test_validate_workflow.py` passes (run: `python3 tests/test_validate_workflow.py`)
- [ ] `python3 scripts/validate_workflow.py --lint-only <file>` produces mapped, referenced output for a known bad workflow (e.g. `examples/with-errors.yml`)
- [ ] `python3 scripts/validate_workflow.py <file>` passes cleanly for `examples/valid-ci.yml`

Full blind-comparison evals aren't warranted here: `tests/test_validate_workflow.py` already exercises
the script's real logic end-to-end (actionlint/act invocation, policy checks, offline mode) against
known-good and known-bad fixtures; the trigger-phrase and quality-gate lists above cover activation
correctness.

## Summary

1. **Setup**: Confirm act/actionlint are installed (see Initial Setup above)
2. **Validate**: Run `validate_workflow.py` on workflow files
3. **Fix**: Address issues using reference documentation
4. **Rerun**: Verify fixes with a mandatory post-fix validation run
5. **Search**: Use official docs to verify unknown actions
6. **Commit**: Push validated workflows with confidence

For detailed information, consult the appropriate reference file in `references/`.
