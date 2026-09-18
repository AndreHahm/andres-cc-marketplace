---
name: github-actions-hardening-audit
description: >-
  Audit GitHub Actions workflow YAML files (.github/workflows/*.yml) for
  hardening gaps — missing timeout-minutes/permissions/concurrency and
  floating action refs (@main/@master/@vN) — via static config scoring. Use
  when asked to "audit workflow hardening", "check for missing
  permissions/timeouts in CI", or "score CI hardening risk".
allowed-tools: Bash(python3 */github-actions-hardening-audit/scripts/workflow_hardening_audit.py:*)
---

# GitHub Actions Workflow Hardening Audit

Use this skill to statically audit `.github/workflows/*.yml` files before risky defaults leak into production CI.

## What this skill does
- Scans workflow YAML files and scores hardening risk per file
- Flags jobs missing `timeout-minutes`
- Flags missing `permissions` declarations (workflow-level or job-level)
- Optionally flags missing `concurrency` controls
- Flags floating `uses:` refs (`@main`, `@master`, `@latest`, major-only tags like `@v4`)
- Supports file/event regex filtering for targeted triage in large monorepos
- Raises severity (`ok` / `warn` / `critical`) and can fail CI gates

## Inputs
Optional:
- `WORKFLOW_GLOB` (default: `.github/workflows/*.y*ml`)
- `TOP_N` (default: `20`)
- `OUTPUT_FORMAT` (`text` or `json`, default: `text`)
- `WARN_SCORE` (default: `3`)
- `CRITICAL_SCORE` (default: `7`)
- `REQUIRE_TIMEOUT` (`0`/`1`, default: `1`)
- `REQUIRE_PERMISSIONS` (`0`/`1`, default: `1`)
- `REQUIRE_CONCURRENCY` (`0`/`1`, default: `0`)
- `FLAG_FLOATING_REFS` (`0`/`1`, default: `1`)
- `ALLOW_REF_REGEX` (regex whitelist for approved refs, optional)
- `WORKFLOW_FILE_MATCH` (regex include filter on file path, optional)
- `WORKFLOW_FILE_EXCLUDE` (regex exclude filter on file path, optional)
- `EVENT_MATCH` (regex include filter on parsed `on:` triggers, optional)
- `EVENT_EXCLUDE` (regex exclude filter on parsed `on:` triggers, optional)
- `FAIL_ON_CRITICAL` (`0` or `1`, default: `0`)

## Run

Text report:

```bash
WORKFLOW_GLOB='.github/workflows/*.y*ml' \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/github-actions-hardening-audit/scripts/workflow_hardening_audit.py
```

JSON output + fail gate:

```bash
WORKFLOW_GLOB='.github/workflows/*.y*ml' \
OUTPUT_FORMAT=json \
REQUIRE_CONCURRENCY=1 \
FAIL_ON_CRITICAL=1 \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/github-actions-hardening-audit/scripts/workflow_hardening_audit.py
```

Filter to only PR-target workflows:

```bash
WORKFLOW_GLOB='.github/workflows/*.y*ml' \
EVENT_MATCH='pull_request_target' \
FAIL_ON_CRITICAL=1 \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/github-actions-hardening-audit/scripts/workflow_hardening_audit.py
```

Run against bundled fixtures:

```bash
WORKFLOW_GLOB="${CLAUDE_PLUGIN_ROOT}/skills/github-actions-hardening-audit/fixtures/*.y*ml" \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/github-actions-hardening-audit/scripts/workflow_hardening_audit.py
```

## Output contract
- Exit `0` in report mode (default)
- Exit `1` when `FAIL_ON_CRITICAL=1` and one or more workflows are critical
- Text mode prints summary + ranked workflow risks
- JSON mode prints summary + ranked workflows + critical workflows

## When NOT to Use
- Syntax, security-injection, or actionlint/act-based lint checks — use `github-actions-validator` instead; this skill only scores static hardening config (timeouts/permissions/concurrency/floating refs), it doesn't run actionlint or act.
- Run-history flakiness or instability across past runs — use `github-actions-conclusion-audit` instead; this skill only reads the workflow YAML files themselves, never run history.

## Testing & Validation

**Verify this skill activates on:**
- "audit workflow hardening"
- "check for missing permissions/timeouts in CI"
- "score CI hardening risk"

**Verify it does NOT activate on:**
- "validate this workflow" / "debug actionlint errors" → `github-actions-validator`
- "which workflows are flaky" → `github-actions-conclusion-audit`

**Quality gates (verified against the bundled fixtures this session):**
- [ ] `fixtures/clean.yml` scores `0` (severity `ok`) — has workflow-level `permissions:`, every job has `timeout-minutes`, and its one `uses:` ref is pinned to a full commit SHA.
- [ ] `fixtures/risky.yml` scores `9` (severity `critical`) — missing `permissions`, missing `timeout-minutes` on its `deploy` job, two floating refs (`@main`, `@v4`), and a `pull_request_target` trigger (`on: [push, pull_request_target]`, single-line flow-sequence form — exercises the inline `on:` parser, not just the block-style one).
- [ ] `WORKFLOW_GLOB` resolves to at least one file, or the script exits `1` with a clear `no files matched` error.

Full blind-comparison evals aren't warranted here: the scoring logic is deterministic and fully
exercised end-to-end by the bundled `fixtures/clean.yml`/`fixtures/risky.yml` pair above, which pins
down the exact expected score for both the clean and critical cases.
