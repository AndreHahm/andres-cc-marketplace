# Dispatch plan: note-formatter, iteration 1 (Full Pipeline)

Skill path (confirmed Step 1.2): `evals/skill-tester/fixtures/note-formatter/SKILL.md`.
Workspace root: `./evals/note-formatter/workspace/iteration-1/`.

## Agent-launch calls: 2

Phase 3 / Step 3.1 launches both agents of one eval simultaneously in a single Agent tool call, one call per eval.
Both are `general-purpose`.

| Call | Eval | Agents in the call (parallel) |
|---|---|---|
| 1 | eval-1 `mixed-types-grouped` | `prompts/eval-1-with_skill.txt`, `prompts/eval-1-baseline.txt` |
| 2 | eval-2 `missing-issue-number` | `prompts/eval-2-with_skill.txt`, `prompts/eval-2-baseline.txt` |

Total: 4 agents. Wait for both agents of a call to finish before Phase 4. Whether calls 1 and 2 are
themselves sent together is not specified by the skill; the skill only requires with_skill and baseline be parallel
within an eval.

## Output and timing locations (per agent)

- eval-1 with_skill: outputs `./evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/`, timing `.../eval-1/with_skill/timing.json`
- eval-1 baseline: outputs `.../eval-1/baseline/outputs/`, timing `.../eval-1/baseline/timing.json`
- eval-2 with_skill: outputs `.../eval-2/with_skill/outputs/`, timing `.../eval-2/with_skill/timing.json`
- eval-2 baseline: outputs `.../eval-2/baseline/outputs/`, timing `.../eval-2/baseline/timing.json`

timing.json shape: `{ "total_tokens": N, "duration_ms": N, "model": "<id>" }`.

## Parity and gates

- with_skill prompts embed the full SKILL.md text; baseline prompts contain no SKILL.md content and tell the agent
  not to use the Skill tool or read skill folders (isolation by instruction only; a baseline output that reproduces the skill is contaminated).
- Step 2.5 gate before the first launch: `evals.json` pre-existed this run, so its prompts must be shown for
  approval via AskUserQuestion. Simulated answer: approve (first option). No agents were run here.
- `eval_metadata.json` files (Step 2.3) are not part of this task and were not written.

## Observation

Both evals list `files: ["release-notes.md"]`, but no such file exists in the fixtures; the prompt templates have
no place to supply `files`, so it is not passed to any agent.
