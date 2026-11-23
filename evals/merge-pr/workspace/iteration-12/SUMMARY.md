# merge-pr iteration 12 (2026-11-23)

Issues #850, #748 and #640 plus the PR-body pre-merge check. Full Pipeline, one run per arm; the baseline is
the pre-change skill on `main`, not a no-skill run. Graded by the author.

| Eval | Scenario | with_skill | baseline |
|---|---|---|---|
| 19 | step 1.5 batch, one push, wait instead of restart | 4/4 | 0/4 |
| 20 | step 1.6 one body edit, waiver sections, pre-edit re-read | 5/5 | 1/5 |
| 21 | ruleset-required context missing | 3/3 | 1/3 |
| 22 | review threads but no outcomes file | 3/3 | 0/3 |
| 23 | bypass plus a touched item: no fix, no push | 3/3 | 0/3 |

Total: with_skill 18/18, baseline 2/18 (mean per-eval pass rate 100% vs 10.7%, +89.3 points).
See `benchmark.json`. Timing figures are the agents' own estimates.
