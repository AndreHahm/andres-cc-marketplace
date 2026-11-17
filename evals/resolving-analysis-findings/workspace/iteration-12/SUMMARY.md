# Iteration 12: rung 3 after the long-flag fix, evals 9 and 10

Run after the cross-model review finding on the issue #760 branch: the read-only id resolve used the short
`-i`, one letter-case away from `-I` (`--ignore-issue`) on `codacy pull-request`, so the skill now names the long
`--issue` form. Step 5 also gained a line taking the PR number only from the validated request. Prompts were
unchanged from iteration 11. Only the with-skill arm was re-run: the baseline never reads the skill, so iteration
11's baselines (3 of 10) still stand.

Eval 9's third assertion was tightened from "`-i 131570938278` or equivalent" to require the long `--issue` form.

| Eval | With skill |
|---|---|
| 9 (numeric id, fresh record) | 6 of 6 |
| 10 (hex id, old record) | 4 of 4 |

Both answers use `--issue` for the read-only resolve and contain no short `-i` or `-I`. No benchmark.json: one
arm only. Token and timing figures in `timing.json` are the agents' own estimates.
