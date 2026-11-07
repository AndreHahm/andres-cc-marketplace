# Iteration 9: classification repeat of evals 7 and 8 at d6350593

Three more with_skill runs of each eval, after iteration 8 showed `AcceptedUse` on eval 7 and
`FalsePositive` on eval 8 for the same facts about `setUp`. Skill files and prompts were unchanged. This
iteration records what each run chose. Its answers were read for the behavior below, not graded against
every assertion, so it writes no `grading.json`.

| Run | Eval 7 (no impact) | Eval 8 (HIGH impact) |
|---|---|---|
| iteration 8 | AcceptedUse, no question | FalsePositive, asks |
| repeat 1 | AcceptedUse, no question | FalsePositive, asks |
| repeat 2 | AcceptedUse, no question | AcceptedUse, asks |
| repeat 3 | AcceptedUse, no question | AcceptedUse, asks |

- The decision rule held in 8 of 8 runs: eval 7 never asked and eval 8 always asked. All 8 used
  `# NOSONAR(S100)` on line 18 with the reason on that line, and none chose a remote write.
- The classification did not hold: eval 8 split 2 and 2, so the fallback transition differs by run.
- Cause, read from the skill: a framework-required name fits both "the rule misreads the code" and
  "deliberate and accepted" in "Real or false positive", and nothing there breaks the tie. Why the split
  shows on eval 8 and not eval 7 is not known; four runs each cannot separate the HIGH impact from the
  prompt's added approval sentence, or from chance.
