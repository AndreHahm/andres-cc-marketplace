# github-actions-conclusion-audit — Synthetic Eval (no live `gh` access)

## Setup

No live `gh` CLI access was available in this sandbox, so 6 synthetic run-history JSON files were
hand-authored to match the exact shape documented in the skill's "Collect run JSON" section:
`databaseId`, `workflowName`, `headBranch`, `conclusion`, `createdAt`, `updatedAt`, `url`, `repository`.

All 6 runs share the same (repository, workflow, branch) group —
`acme-org/widget-service` / `CI` / `main` — with `databaseId` 1001–1006, one run per day from
2026-09-12 through 2026-09-17, and conclusions alternating strictly:

| databaseId | createdAt | conclusion |
|---|---|---|
| 1001 | 2026-09-12T09:00:00Z | success |
| 1002 | 2026-09-13T09:00:00Z | failure |
| 1003 | 2026-09-14T09:00:00Z | success |
| 1004 | 2026-09-15T09:00:00Z | failure |
| 1005 | 2026-09-16T09:00:00Z | success |
| 1006 | 2026-09-17T09:00:00Z | failure |

Files: `synthetic-runs/run-1001.json` … `synthetic-runs/run-1006.json` (this directory).

## Runs performed

Both commands from the skill's own "Run" section were executed against
`RUN_GLOB='<this-dir>/synthetic-runs/*.json'`, unmodified otherwise:

1. **Text report** (`WARN_INSTABILITY_PCT=35 CRITICAL_INSTABILITY_PCT=60`, defaults) — saved to
   `script-output-text.txt`.
2. **JSON output + fail gate** (`OUTPUT_FORMAT=json FAIL_ON_CRITICAL=1`) — saved to
   `script-output-json.txt`.

## Results

- 6 runs scanned across 6 files, 0 parse errors, 0 filtered, all grouped into exactly 1 group
  (repository+workflow+branch match, as expected).
- `run_count=6` clears `MIN_RUNS=5`, so the group gets real severity classification instead of being
  excluded.
- 5 transitions across 5 adjacent-run pairs (every single one flips, since conclusions strictly
  alternate) → `instability_pct = 5/5 * 100 = 100.0`.
- `failure_rate_pct = 3/6 * 100 = 50.0` (3 of 6 runs are `failure`, a failure-like conclusion per the
  skill's documented set).
- `max_failure_streak = 1` (failures never run back-to-back in this alternating pattern — correctly
  distinguished from *how often* it fails).
- `100.0% >= CRITICAL_INSTABILITY_PCT (60%)` → severity = **critical**, exactly the workflow this skill
  is meant to catch (chronic flip-flopping, not just a low pass rate).
- Text-mode run (`FAIL_ON_CRITICAL` not set, default `0`): **exit code 0** — correct per the Output
  Contract ("Exit 0 in reporting mode ... or FAIL_ON_CRITICAL=0"), even though a critical group exists.
- JSON-mode run (`FAIL_ON_CRITICAL=1`): **exit code 1** — correct per the Output Contract ("Exit 1 when
  FAIL_ON_CRITICAL=1 and one or more critical groups are found"). The JSON payload includes all four
  documented top-level keys (`summary`, `groups`, `all_groups`, `critical_groups`), and
  `critical_groups` correctly contains the one flagged group.

## Verdict

The script behaves exactly as the SKILL.md documents for this scenario:
- Grouping by (repository, workflow, branch) works correctly.
- The transition-based instability formula matches the doc's description (conclusion sequence →
  transition count → instability percentage) and produces the maximum possible value (100%) for a
  strictly-alternating sequence, which is the intended flaky-workflow signal.
- `MIN_RUNS` gating, severity thresholds, and the two documented exit-code paths (reporting-mode 0 vs.
  gated-mode 1) all check out against this synthetic fixture.
- No parse errors, no unexpected filtering — all 6 hand-authored files were consumed as intended.

This exercises the skill's core Testing & Validation quality gates:
`python3 conclusion_volatility_audit.py` reporting-mode exit 0 with critical groups present (confirmed),
`FAIL_ON_CRITICAL=1` exit 1 with a critical group present (confirmed), and JSON output including all
four documented top-level keys (confirmed). The one quality gate not exercised here is "the Collect run
JSON example runs without error against a real `gh run view` call" — out of scope, since no live `gh`
CLI access exists in this sandbox; that gate needs a real GitHub Actions run to validate.
