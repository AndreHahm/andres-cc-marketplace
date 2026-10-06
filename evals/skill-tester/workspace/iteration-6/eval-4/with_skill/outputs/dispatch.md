# Dispatch plan: note-formatter, iteration 1 (Full Pipeline)

Agent-launch calls: 2 (one per eval). Each call contains both agents for that eval,
launched simultaneously in the same message (Phase 3, Step 3.1). Total agents: 4,
all `general-purpose`, same model. Nothing was launched in this dry run.

| Call | Eval | Agents in the call | Prompt files |
|---|---|---|---|
| 1 | 1 (mixed-types-grouped) | with_skill + baseline | prompts/eval-1-with_skill.txt, prompts/eval-1-baseline.txt |
| 2 | 2 (missing-issue-number) | with_skill + baseline | prompts/eval-2-with_skill.txt, prompts/eval-2-baseline.txt |

Calls 1 and 2 are independent. Phase 4 grading waits until the agents of both calls have finished.

## Output and timing locations (each agent writes its own)
- Eval 1 with_skill: ./evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/ and .../with_skill/timing.json
- Eval 1 baseline:   ./evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/ and .../baseline/timing.json
- Eval 2 with_skill: ./evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/ and .../with_skill/timing.json
- Eval 2 baseline:   ./evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/ and .../baseline/timing.json

timing.json holds `total_tokens`, `duration_ms`, `model`. The with_skill prompts embed the full
SKILL.md text; the baseline prompts contain none of it (isolation is by instruction only, so a
baseline that quotes the skill is recorded as contaminated at grading).

## Preconditions before dispatch (Step 2.5)
`evals.json` already existed, so the eval prompts are shown to the operator for approval before
any launch. Also eval_metadata.json files must exist per eval directory (Step 2.3).
