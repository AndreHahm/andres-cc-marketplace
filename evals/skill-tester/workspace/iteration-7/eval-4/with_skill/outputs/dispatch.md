# Dispatch plan: note-formatter, iteration 1 (Full Pipeline)

No agent is launched in this dry run. Source: Phase 3, Step 3.1 and the "Agent Prompt Templates" in `references/eval-schema.md`.

## Agent-launch calls: 2 (one per eval, 4 agents total)

Each call holds both agents for one eval, sent together in a single Agent tool call so they run simultaneously. Both are `general-purpose`.

| Call | Eval | Agents in the call | Prompt files |
|---|---|---|---|
| 1 | eval-1 (mixed-types-grouped) | with_skill + baseline | prompts/eval-1-with_skill.txt, prompts/eval-1-baseline.txt |
| 2 | eval-2 (missing-issue-number) | with_skill + baseline | prompts/eval-2-with_skill.txt, prompts/eval-2-baseline.txt |

The skill does not say whether call 2 may overlap with call 1. It says only to wait for both agents of the dispatched call(s) before Phase 4. I would send the two calls one after the other, or both in the same message, as the operator prefers. Either way the with_skill and baseline agents of one eval always go in the same call.

## Output locations (relative to the project root, under `./evals/`)

- eval-1 with_skill: outputs in `./evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/`, timing in `./evals/note-formatter/workspace/iteration-1/eval-1/with_skill/timing.json`
- eval-1 baseline: outputs in `./evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/`, timing in `./evals/note-formatter/workspace/iteration-1/eval-1/baseline/timing.json`
- eval-2 with_skill: outputs in `./evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/`, timing in `./evals/note-formatter/workspace/iteration-1/eval-2/with_skill/timing.json`
- eval-2 baseline: outputs in `./evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/`, timing in `./evals/note-formatter/workspace/iteration-1/eval-2/baseline/timing.json`

Timing data is `{ "total_tokens", "duration_ms", "model" }`, written by each agent itself.

## Isolation and notes

- with_skill prompts embed the full text of the target SKILL.md (`evals/skill-tester/fixtures/note-formatter/SKILL.md`). Baseline prompts contain no skill content and tell the agent not to use the Skill tool or read any SKILL.md. Baseline isolation is by instruction only.
- The eval prompt text is copied verbatim from evals.json; `expected_output` is never shown to any agent.
- Step 2.5 gate before dispatch: `evals.json` pre-existed, so the eval prompts and the target digest need `AskUserQuestion` approval first (see transcript.md). Dispatch happens only after that approval.
- After both calls finish: Phase 4 grading, Phase 5 `aggregate_benchmark.py` on `./evals/note-formatter/workspace/iteration-1`, then Phase 6.
