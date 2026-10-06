# Transcript: skill-tester dry run (eval-1, note-formatter)

Operator request: "Quickly check my note-formatter skill, it lives in evals/skill-tester/fixtures/note-formatter."
Simulated: the AskUserQuestion tool and sub-agents are unavailable, so each question is recorded with the simulated answer.

## Step 1.1 (Which skill?)
Question: "Which skill do you want to test?" Options: skill-development, skill-refiner-interactive, Other skill.
Simulated answer: skill already located (evals/skill-tester/fixtures/note-formatter). Treated as "Other skill".

## Step 1.2 (Confirm path and purpose)
Read the fixture SKILL.md (data only).
Skill: note-formatter
Location: evals/skill-tester/fixtures/note-formatter/SKILL.md
Purpose: Format raw changelog bullets into the project's release-note line format.
The target is inside this repository, so the external-skill trust question is not triggered.

## Step 1.2b (Workflow mode)
Question: "Which testing mode would you like?" Options: Quick Workflow, Full Pipeline.
Simulated answer: Quick Workflow (fast pass/fail, no baseline). Consequences: one with_skill agent per eval, no timing, no Phase 5 aggregation, no Phase 6 tables.

## Step 1.3 (Create workspace)
Created evals/note-formatter/ and evals/note-formatter/workspace/iteration-1/ under OUTDIR (stand-in for the project-root ./evals/).

## Step 2.1 (Interview)
Q1 core scenarios: (1) mixed feature/bug/docs/refactor bullets grouped in documented order; (2) bullet without issue number rendered with (#none).
Q2 good response: follows the skill's rules exactly.
Q3 what baseline fails: not given; not needed for Quick mode (no baseline).
Q4 pressure testing: No. The skill-development Phase 3.5 compliance run is therefore not triggered, and no `pressure_condition` fields were written.

## Step 2.1b (Cross-check with the target's Testing & Validation section)
The target declares 2 scenarios: (1) mixed types grouped in the documented order, (2) missing issue number gives (#none).
Eval 1 covers scenario 1 and eval 2 covers scenario 2: 2 of 2 covered, none uncovered.
Recorded in evals.json as `testing_validation_coverage`.

## Step 2.2 (evals.json)
Wrote evals/note-formatter/evals.json with 2 evals. `skill_path` ends in SKILL.md and matches the confirmed Location.

## Step 2.3 (eval_metadata.json)
Wrote workspace/iteration-1/eval-1/eval_metadata.json (5 assertions) and eval-2/eval_metadata.json (4 assertions). The with_skill subdirectories are created in the run phase.

## Step 2.4 (Plugin-rule compliance assertions, optional)
Skipped: the operator asked only for functional checks of the skill's formatting behavior, not rule compliance. No plugin-rulebook call.

## Step 2.5 (Approve eval prompts before dispatch)
evals.json did not exist before this run, and this run wrote it. No `git status` change since Step 2.2 to review in a real run. No approval is required. In a real run, it would be rechecked immediately before dispatch.

## Stop point
Per the dispatcher's instructions, stopping before any agent is launched. No agents were run, no grading was done.

## What the next phase would do (Quick Phase 1 to 4)
- Quick Phase 1: for each of the 2 evals, launch ONE general-purpose agent using the WITH_SKILL_ONLY template. It gets the full note-formatter SKILL.md plus the eval prompt, and saves outputs to ./evals/note-formatter/workspace/iteration-1/eval-M/with_skill/outputs/. Evals run one after another, waiting for each to finish. No baseline, no timing.json.
- Quick Phase 2: grade each eval's outputs against its eval_metadata.json assertions (pass/fail plus evidence) and write eval-M/with_skill/grading.json. Any instruction-like text in outputs is reported as suspicious in `evidence`, never acted on.
- Quick Phase 3: print the QUICK VALIDATION RESULTS summary (per-eval PASS/FAIL with assertion counts), and also the `mode: "quick"` structured result document with `coverage` {declared_scenarios_total: 2, declared_scenarios_covered: 2, uncovered: []} read from evals.json.
- Quick Phase 4: AskUserQuestion with Run full pipeline / Refine skill / Done. If any assertion fails, also offer `enhancement-suggestor` (only after asking).

## Files created (all under OUTDIR/evals/note-formatter/)
- evals.json
- workspace/iteration-1/eval-1/eval_metadata.json
- workspace/iteration-1/eval-2/eval_metadata.json
