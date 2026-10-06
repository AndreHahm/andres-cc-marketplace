# Dispatch plan: note-formatter, iteration 1 (Full Pipeline)

Skill under test: `evals/skill-tester/fixtures/note-formatter/SKILL.md`. Evals: `evals/skill-tester/fixtures/dispatch/evals/note-formatter/evals.json` (2 evals).
Workspace root (skill name is `note-formatter`, standardized `./evals/<skill-name>/` layout): `./evals/note-formatter/workspace/iteration-1/`.

## Agent-launch calls: 2

SKILL.md Step 3.1 says to launch, for EACH eval, 2 agents simultaneously in ONE Agent tool call. With 2 evals that is 2 launch calls, each carrying 2 `general-purpose` agents (4 agents total). No agent is launched in this dry run.

| Call | Eval | Agents in the call | Prompt files |
|---|---|---|---|
| 1 | eval-1 (mixed-types-grouped) | with_skill + baseline, in parallel | `prompts/eval-1-with_skill.txt`, `prompts/eval-1-baseline.txt` |
| 2 | eval-2 (missing-issue-number) | with_skill + baseline, in parallel | `prompts/eval-2-with_skill.txt`, `prompts/eval-2-baseline.txt` |

Step 3.1 asks for the 2 agents of an eval to run simultaneously; it says to wait for both before Phase 4. It does not say whether the 2 eval calls may overlap, so both are listed as separate calls and the dispatcher may issue them back to back (the pipeline waits for all to complete before Phase 4).

## Output and timing locations (agent-written, repo-relative)

- eval-1 with_skill: `./evals/note-formatter/workspace/iteration-1/eval-1/with_skill/outputs/` and `.../eval-1/with_skill/timing.json`
- eval-1 baseline: `./evals/note-formatter/workspace/iteration-1/eval-1/baseline/outputs/` and `.../eval-1/baseline/timing.json`
- eval-2 with_skill: `./evals/note-formatter/workspace/iteration-1/eval-2/with_skill/outputs/` and `.../eval-2/with_skill/timing.json`
- eval-2 baseline: `./evals/note-formatter/workspace/iteration-1/eval-2/baseline/outputs/` and `.../eval-2/baseline/timing.json`

timing.json shape: `{ "total_tokens": <count>, "duration_ms": <ms>, "model": "<model-id>" }`.

## Notes

- The with_skill prompt embeds the full SKILL.md text; the baseline prompt contains no skill content and tells the agent not to use the Skill tool or read any SKILL.md. Isolation is by instruction only; a baseline output that quotes the skill is contaminated and is not counted as a clean baseline in grading.
- `expected_output` and assertions are not included in any prompt (blind testing).
- Before the first launch, Step 2.5 requires AskUserQuestion approval of the eval prompts (see transcript.md). Afterwards: Phase 4 grading, Phase 5 `aggregate_benchmark.py` on `./evals/note-formatter/workspace/iteration-1`, Phase 6 summary.
