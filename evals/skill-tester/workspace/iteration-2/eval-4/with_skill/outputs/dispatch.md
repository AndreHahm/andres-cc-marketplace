# Dispatch plan: note-formatter, iteration 1 (Full Pipeline, Phase 3)

Source: Phase 3 Step 3.1 of skill-tester and the "Agent Prompt Templates" in references/eval-schema.md.
Eval set: 2 evals (1 mixed-types-grouped, 2 missing-issue-number).

## Agent-launch calls: 2 (one per eval), 2 agents in each

- Call 1 (eval-1), both agents in the same Agent tool call so they run concurrently:
  - eval-1-with_skill (general-purpose), prompt: prompts/eval-1-with_skill.txt (full note-formatter SKILL.md embedded)
  - eval-1-baseline (general-purpose), prompt: prompts/eval-1-baseline.txt (no skill content)
- Call 2 (eval-2), same shape:
  - eval-2-with_skill, prompts/eval-2-with_skill.txt
  - eval-2-baseline, prompts/eval-2-baseline.txt

Total: 4 agents. with_skill and baseline are never run sequentially. Wait for all agents before Phase 4 (grading).

## Where each agent saves (relative to repo root)

| Agent | Outputs | Timing |
|---|---|---|
| eval-1-with_skill | evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/ | .../eval-1/with_skill/timing.json |
| eval-1-baseline | evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/ | .../eval-1/baseline/timing.json |
| eval-2-with_skill | evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/ | .../eval-2/with_skill/timing.json |
| eval-2-baseline | evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/ | .../eval-2/baseline/timing.json |

timing.json shape: `{ "total_tokens": N, "duration_ms": N, "model": "<id>" }`, written by each agent per the template.

## Notes

- Parity: only the with_skill prompt contains SKILL.md; the baseline prompt has no skill content and no expected_output (blind).
- Neither prompt includes expected_output; that is for grading only.
- evals.json lists `files: ["release-notes.md"]` but the fixture has no such file and the templates have no slot for it, so the prompts do not reference it. Flag to the operator.
- Prerequisite not done in this dry run: eval_metadata.json per eval (Step 2.3) and the workspace dirs. The evals.json here lives under fixtures/dispatch/evals/, not the standard ./evals/note-formatter/evals.json.
