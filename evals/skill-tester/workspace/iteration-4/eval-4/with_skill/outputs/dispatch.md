# Dispatch plan: note-formatter, iteration 1 (Full Pipeline)

Agent-launch calls: 2 (one per eval), each a single Agent tool call containing 2 agents launched simultaneously (Phase 3, Step 3.1).

| Call | Eval | Agents in the call |
|---|---|---|
| 1 | eval-1 (mixed-types-grouped) | eval-1-with_skill, eval-1-baseline (general-purpose, parallel) |
| 2 | eval-2 (missing-issue-number) | eval-2-with_skill, eval-2-baseline (general-purpose, parallel) |

Total: 4 agents. Prompts: prompts/eval-N-with_skill.txt (full SKILL.md embedded) and prompts/eval-N-baseline.txt (no skill content).
Calls 1 and 2 may be issued in the same message so all 4 agents run concurrently; the skill only requires each eval's pair to launch together.

Where each agent saves (repo-relative):
- with_skill: evals/note-formatter/workspace/iteration-1/eval-N/with_skill/outputs/ and .../with_skill/timing.json
- baseline:   evals/note-formatter/workspace/iteration-1/eval-N/baseline/outputs/ and .../baseline/timing.json
timing.json shape: { "total_tokens", "duration_ms", "model" }, written by each agent itself.

Pre-dispatch gate (Step 2.5): evals.json already existed, so its prompts are shown and approved via AskUserQuestion before any launch. Re-approval is required on any re-dispatch.
After both agents of every eval finish: Phase 4 grading, Phase 5 aggregate_benchmark.py on evals/note-formatter/workspace/iteration-1, Phase 6 summary.
Caveat: baseline isolation is by instruction only; a baseline output that reproduces the skill is contaminated.
