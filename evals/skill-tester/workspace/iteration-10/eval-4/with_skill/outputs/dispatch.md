# Dispatch plan: note-formatter, iteration 1 (Full Pipeline)

Mode: Full Pipeline (a full benchmark iteration with baseline comparison). Not executed in this dry run.

## Agent-launch calls: 2

Per Phase 3 Step 3.1, each eval gets one Agent tool call that launches its two agents simultaneously. Every agent is `general-purpose`.

| Call | Eval | Agents in the call |
|---|---|---|
| 1 | eval-1 (mixed-types-grouped) | eval-1-with_skill, eval-1-baseline |
| 2 | eval-2 (missing-issue-number) | eval-2-with_skill, eval-2-baseline |

Total: 4 agents. Wait for both agents of a call to finish before Phase 4. (The SKILL says "for EACH eval, launch 2 agents SIMULTANEOUSLY in one Agent tool call"; whether calls 1 and 2 are also sent together is not specified, so they are per-eval calls.)

## Where each agent saves outputs and timing

| Agent | Outputs | Timing |
|---|---|---|
| eval-1-with_skill | ./evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/ | ./evals/note-formatter/workspace/iteration-1/eval-1/with_skill/timing.json |
| eval-1-baseline | ./evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/ | ./evals/note-formatter/workspace/iteration-1/eval-1/baseline/timing.json |
| eval-2-with_skill | ./evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/ | ./evals/note-formatter/workspace/iteration-1/eval-2/with_skill/timing.json |
| eval-2-baseline | ./evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/ | ./evals/note-formatter/workspace/iteration-1/eval-2/baseline/timing.json |

timing.json shape: `{ "total_tokens": <count>, "duration_ms": <ms>, "model": "<model-id>" }`.

Prompt files are in `prompts/`. The with_skill prompts embed the full text of the note-formatter SKILL.md; the baseline prompts contain no skill content and say not to use the Skill tool or read any SKILL.md (isolation by instruction only, so a baseline output that quotes the skill is contaminated and must be noted in grading evidence).

## Notes
- The evals' `files: ["release-notes.md"]` field is not part of either prompt template, so it is not passed to the agents.
- Phase 4 grading, Phase 5 aggregation (`aggregate_benchmark.py ./evals/note-formatter/workspace/iteration-1`) and Phase 6 happen after the agents finish.
