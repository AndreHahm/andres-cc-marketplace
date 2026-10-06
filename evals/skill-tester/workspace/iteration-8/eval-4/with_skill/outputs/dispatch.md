# Dispatch plan: note-formatter, iteration 1 (Full Pipeline)

Launch calls: 2 agent-launch calls, one per eval (Step 3.1: "for EACH eval, launch 2 agents SIMULTANEOUSLY in one Agent tool call").
All agents are `general-purpose`. Wait for both agents of a call before Phase 4.

| Call | Agents (launched together) | Prompt files |
|---|---|---|
| 1 | eval-1 with_skill + eval-1 baseline | prompts/eval-1-with_skill.txt, prompts/eval-1-baseline.txt |
| 2 | eval-2 with_skill + eval-2 baseline | prompts/eval-2-with_skill.txt, prompts/eval-2-baseline.txt |

(Calls 1 and 2 are independent and could be issued in the same message so all 4 agents run concurrently; the skill's per-eval wording requires at minimum the with_skill/baseline pair to be in one call.)

## Output locations (repo-relative, under the workspace in `./evals/note-formatter/`)

| Agent | Outputs | Timing |
|---|---|---|
| eval-1 with_skill | evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/ | .../eval-1/with_skill/timing.json |
| eval-1 baseline | evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/ | .../eval-1/baseline/timing.json |
| eval-2 with_skill | evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/ | .../eval-2/with_skill/timing.json |
| eval-2 baseline | evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/ | .../eval-2/baseline/timing.json |

timing.json shape: `{ "total_tokens", "duration_ms", "model" }`.
The with_skill prompts embed the full SKILL.md text; the baseline prompts contain no skill content and forbid the Skill tool and skill folders.

## Pre-dispatch gates (see transcript.md)
Step 2.5 approval was required because evals.json pre-existed; simulated answer: first option (Approve and dispatch).
