# Dispatch plan: note-formatter, iteration 1 (Full Pipeline, Phase 3 Step 3.1)

No agent is launched in this dry run. Per SKILL.md Step 3.1 and the quality gate, each eval gets one `Agent` tool call carrying both of its agents (with_skill and baseline) so they run simultaneously.

## Agent-launch calls: 2 (one per eval), 4 agents in total

| Call | Eval | Agents in the call | Prompt files |
|---|---|---|---|
| 1 | eval-1 (mixed-types-grouped) | with_skill + baseline, both `general-purpose`, parallel | prompts/eval-1-with_skill.txt, prompts/eval-1-baseline.txt |
| 2 | eval-2 (missing-issue-number) | with_skill + baseline, both `general-purpose`, parallel | prompts/eval-2-with_skill.txt, prompts/eval-2-baseline.txt |

Calls 1 and 2 are independent, so they can be issued in the same message. The pipeline then waits for all agents to finish before Phase 4.

## Output and timing locations (repo-relative)

Each agent saves outputs and its own timing.json (the agent writes it, per the template) to:

- eval-1 with_skill: `evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/` and `.../with_skill/timing.json`
- eval-1 baseline: `evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/` and `.../baseline/timing.json`
- eval-2 with_skill: `evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/` and `.../with_skill/timing.json`
- eval-2 baseline: `evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/` and `.../baseline/timing.json`

timing.json shape: `{ "total_tokens": <count>, "duration_ms": <ms>, "model": "<model-id>" }`.

## Notes

- with_skill prompts embed the full fixture SKILL.md (`evals/skill-tester/fixtures/note-formatter/SKILL.md`); baseline prompts contain no skill content (isolation is by instruction only; a baseline that quotes the skill is to be marked contaminated in grading evidence).
- Because evals.json already existed, the pre-dispatch gate applies: prompts are shown and approved via AskUserQuestion before launch (see transcript.md).
- Before the launch, Phase 2 Step 2.3 would also have created eval_metadata.json per eval (not done here; dry run only prompts and plan were requested).
