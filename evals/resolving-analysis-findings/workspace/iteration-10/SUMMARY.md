# Iteration 10: framework-name tie-break, evals 7 and 8

Run after the "Sonar mechanisms" section gained one sentence: a name a framework requires is
`AcceptedUse`, not `FalsePositive`. Prompts were unchanged. Answers were read for the behavior below, not
graded against every assertion, so this iteration writes no `grading.json`.

| Eval | Runs | Classified `AcceptedUse` | Ask-or-decide correct |
|---|---|---|---|
| 7 (no impact) | 2 | 2 of 2 | 2 of 2, no question |
| 8 (HIGH impact) | 4 | 4 of 4 | 4 of 4, asks |

Before the sentence, iterations 8 and 9 gave 6 of 8 `AcceptedUse` (eval 8 split 2 and 2).

All 6 runs used `# NOSONAR(S100)` and chose no remote write. Five named `accept` as the rung 3 fallback.
One eval 7 run still wrote "`falsepositive` or `accept`" for the fallback, so its classification was
stable but its fallback wording was not fully. Six runs show the split is gone in this sample; they do
not prove it cannot recur.
