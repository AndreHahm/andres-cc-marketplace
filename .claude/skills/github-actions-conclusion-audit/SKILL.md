---
name: github-actions-conclusion-audit
description: >-
  Audit GitHub Actions run-history JSON (collected via `gh run view --json
  conclusion,...`) for conclusion volatility — workflows that flip between
  success and failure-like outcomes across recent runs — to surface
  chronically flaky pipelines. Use when asked "which workflows are flaky",
  "audit CI stability", or "detect unstable workflows from run history".
allowed-tools: Bash(gh run view:*) Bash(gh repo view:*) Bash(jq:*) Bash(python3 */github-actions-conclusion-audit/scripts/conclusion_volatility_audit.py:*)
---

# GitHub Actions Conclusion Volatility Audit

Use this skill to detect unstable workflows that frequently flip between success and failure-like outcomes.

## What this skill does
- Reads one or more workflow run JSON exports
- Groups runs by repository + workflow + branch
- Calculates volatility using conclusion transitions across run history
- Flags groups by warn/critical instability thresholds
- Emits text or JSON output for CI reporting and quality gates

## Inputs
Optional:
- `RUN_GLOB` (default: `artifacts/github-actions/*.json`)
- `TOP_N` (default: `20`)
- `OUTPUT_FORMAT` (`text` or `json`, default: `text`)
- `MIN_RUNS` (default: `5`) — minimum runs before severity is applied
- `WARN_INSTABILITY_PCT` (default: `35`)
- `CRITICAL_INSTABILITY_PCT` (default: `60`)
- `FAIL_ON_CRITICAL` (`0` or `1`, default: `0`)
- `WORKFLOW_MATCH`, `WORKFLOW_EXCLUDE` (regex, optional)
- `BRANCH_MATCH`, `BRANCH_EXCLUDE` (regex, optional)
- `REPO_MATCH`, `REPO_EXCLUDE` (regex, optional)

Failure-like conclusions are: `failure`, `cancelled`, `timed_out`, `action_required`, `startup_failure`.

## When to Use

Use when asked to find flaky/unstable GitHub Actions workflows from **run history** — e.g. "which
workflows are flaky", "audit CI stability", "detect unstable workflows from run history". Input is
run-history JSON exported via `gh run view --json`.

## When NOT to Use

- **Static workflow-config scoring** (missing `timeout-minutes`/`permissions`/`concurrency`, floating
  action refs) — use `github-actions-hardening-audit` instead; it reads `.github/workflows/*.yml`
  directly, not run history.
- **Raw log content analysis** (wasted effort, mistakes, instruction-compliance gaps within a run) — use
  `github-actions-log-analyzer` instead; it reads full run logs via `gh run view --log`, not the
  conclusion/status summary this skill uses.
- **Syntax/lint validation of a workflow file itself** — use `github-actions-validator` instead; it
  operates on `.github/workflows/*.yml` directly, not run-history JSON.

## Collect run JSON

`gh run view --json` does **not** accept a `repository` field — requesting it errors outright. Collect
the repository name separately and inject it into the JSON payload:

```bash
gh run view <run-id> --json databaseId,workflowName,headBranch,conclusion,createdAt,updatedAt,url \
  | jq --arg repo "$(gh repo view --json nameWithOwner -q .nameWithOwner)" '. + {repository: $repo}' \
  > artifacts/github-actions/run-<run-id>.json
```

`MIN_RUNS` defaults to `5` — a (repository, workflow, branch) group below that count is excluded from
`warn`/`critical` severity entirely, so a single collected run produces no real signal. Collect several
runs per workflow/branch in a loop instead of hand-repeating the single-run command:

```bash
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
for id in $(gh run list --workflow=<workflow-file> --branch=<branch> --json databaseId -q '.[].databaseId' --limit 20); do
  gh run view "$id" --json databaseId,workflowName,headBranch,conclusion,createdAt,updatedAt,url \
    | jq --arg repo "$REPO" '. + {repository: $repo}' \
    > "artifacts/github-actions/run-${id}.json"
done
```

Recommend adding `artifacts/` (or whichever directory `RUN_GLOB` points at) to your own repository's
`.gitignore` — these are scratch run-history exports, not something meant to be committed.

## Run

Text report:

```bash
RUN_GLOB='artifacts/github-actions/*.json' \
WARN_INSTABILITY_PCT=35 \
CRITICAL_INSTABILITY_PCT=60 \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/github-actions-conclusion-audit/scripts/conclusion_volatility_audit.py
```

JSON output + fail gate:

```bash
RUN_GLOB='artifacts/github-actions/*.json' \
OUTPUT_FORMAT=json \
FAIL_ON_CRITICAL=1 \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/github-actions-conclusion-audit/scripts/conclusion_volatility_audit.py
```

## Output contract
- Exit `0` in reporting mode with no critical groups (or `FAIL_ON_CRITICAL=0`)
- Exit `1` when `FAIL_ON_CRITICAL=1` and one or more critical groups are found
- Exit `1` also on invalid input — invalid `OUTPUT_FORMAT`/`TOP_N`/`MIN_RUNS`/`FAIL_ON_CRITICAL`, a
  non-numeric or out-of-range `WARN_INSTABILITY_PCT`/`CRITICAL_INSTABILITY_PCT`,
  `CRITICAL_INSTABILITY_PCT` below `WARN_INSTABILITY_PCT`, an invalid `*_MATCH`/`*_EXCLUDE` regex, or
  `RUN_GLOB` matching zero files. Check stderr to distinguish a critical-instability gate failure from a
  config/input error — both currently exit `1`.
- Text output includes summary, thresholds, a `PARSE_ERRORS:` block (only shown if any input file failed
  to parse as JSON), and the top unstable workflow groups
- JSON output includes `summary`, `groups` (ranked, truncated to `TOP_N`), `all_groups` (the full ranked
  list, untruncated), and `critical_groups`

## Testing & Validation

**Verify this skill activates on:**
- "which workflows are flaky"
- "audit CI stability"
- "detect unstable workflows from run history"

**Verify it does NOT activate on:**
- "audit this workflow for hardening gaps" → `github-actions-hardening-audit`
- "why is this run wasting time" → `github-actions-log-analyzer`

**Quality gates:**
- [ ] `python3 scripts/conclusion_volatility_audit.py` exits `0` in reporting mode with no critical
      groups found
- [ ] `FAIL_ON_CRITICAL=1` exits `1` when a critical group is present
- [ ] JSON output includes all four documented top-level keys (`summary`, `groups`, `all_groups`,
      `critical_groups`)
- [ ] The "Collect run JSON" example runs without error against a real `gh run view` call

Full blind-comparison evals aren't warranted here: the volatility-scoring logic is deterministic and
directly traceable from its inputs (conclusion sequence → transition count → instability percentage);
the quality gates above pin down the exact exit-code and output-shape contract to check against.
