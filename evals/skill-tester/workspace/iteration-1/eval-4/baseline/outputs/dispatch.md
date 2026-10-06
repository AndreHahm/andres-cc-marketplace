# Dispatch plan: note-formatter, iteration 1

Source: evals/skill-tester/fixtures/dispatch/evals/note-formatter/evals.json (2 evals, so 4 agents: 2 with_skill, 2 baseline).

## Agent-launch calls

I would make ONE agent-launch call turn containing 4 parallel Agent tool uses, so all runs start together and none sees another's results:

| Agent | Prompt file | Outputs dir |
|---|---|---|
| eval-1 with_skill | prompts/eval-1-with_skill.txt | evals/skill-tester/workspace/iteration-1/eval-1/with_skill/outputs |
| eval-1 baseline | prompts/eval-1-baseline.txt | evals/skill-tester/workspace/iteration-1/eval-1/baseline/outputs |
| eval-2 with_skill | prompts/eval-2-with_skill.txt | evals/skill-tester/workspace/iteration-1/eval-2/with_skill/outputs |
| eval-2 baseline | prompts/eval-2-baseline.txt | evals/skill-tester/workspace/iteration-1/eval-2/baseline/outputs |

Total: 1 call turn, 4 agents. Agents are general-purpose, fresh (never fork).

## Outputs and timing

- Each agent writes result.md and transcript.md into its outputs directory.
- Timing: each agent's token count and duration come from its task-completion notification. The dispatcher (not the agent) writes timing.json next to outputs/ (eval-N/<mode>/timing.json) with total_tokens and duration_ms, as soon as each notification arrives, since that data is not recoverable later.

## Notes / gaps

- The evals list files: ["release-notes.md"], but no such file exists in the fixtures dir. Agents are told to use it if present and otherwise say so.
- The prompt files tell agents to write timing.json themselves; if the dispatcher owns timing, drop that line from the prompts.
