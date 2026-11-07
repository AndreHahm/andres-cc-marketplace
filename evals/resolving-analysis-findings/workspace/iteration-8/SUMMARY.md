# Iteration 8: Sonar evals at d6350593

Re-run after the review fixes, with_skill only for evals 5-7: baselines do not read the skill, so the
fixes cannot change them. New eval 8 ran both arms. No `benchmark.json`, because only eval 8 has a
baseline in this iteration.

| Eval | with_skill | baseline |
|---|---|---|
| 5 sonar-vulnerability-false-positive | 4/4 | not re-run |
| 6 sonar-minor-smell-inline | 4/4 | not re-run |
| 7 sonar-minor-framework-name-inline | 6/6 | not re-run |
| 8 sonar-minor-high-impact-asks | 5/5 | 2/5 |

Eval 7 is eval 8's control: the same finding without an impact is decided without asking.

The answers under `outputs/` are condensed from each agent's final reply. Agents read the worktree's
SKILL.md by path rather than receiving it embedded in the prompt, so the run used d6350593's files.

Not an assertion failure: for the same facts, eval 7 classified the finding as `AcceptedUse` and eval
8 as `FalsePositive`. The two answers then name different fallback transitions.
