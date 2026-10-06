# Dispatch plan: note-formatter, iteration 1 (Full Pipeline, Phase 3 Step 3.1)

Nothing was launched. Prompt files are in `prompts/`.

## Agent-launch calls: 2

Per SKILL.md Step 3.1, each eval gets one Agent tool call holding both of its agents, so the
with_skill and baseline agents start simultaneously. Both agents are `general-purpose`.

| Call | Agents | Prompt files |
|---|---|---|
| 1 (eval 1, mixed-types-grouped) | with_skill + baseline | `prompts/eval-1-with_skill.txt`, `prompts/eval-1-baseline.txt` |
| 2 (eval 2, missing-issue-number) | with_skill + baseline | `prompts/eval-2-with_skill.txt`, `prompts/eval-2-baseline.txt` |

Total: 4 agents. The two calls are independent. The skill says to wait for both agents of a call
before Phase 4 grading, and does not require serializing the calls.

## Output and timing locations (repo-relative, per eval-schema.md templates)

| Agent | Outputs | Timing |
|---|---|---|
| eval-1 with_skill | `evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/` | `.../eval-1/with_skill/timing.json` |
| eval-1 baseline | `evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/` | `.../eval-1/baseline/timing.json` |
| eval-2 with_skill | `evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/` | `.../eval-2/with_skill/timing.json` |
| eval-2 baseline | `evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/` | `.../eval-2/baseline/timing.json` |

timing.json holds `total_tokens`, `duration_ms` and `model`.

## Baseline parity
with_skill prompts embed the full note-formatter SKILL.md. Baseline prompts contain no skill
content and no expected output.
