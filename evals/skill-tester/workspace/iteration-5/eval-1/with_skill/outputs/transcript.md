# Transcript: skill-tester dry run (eval-1)

Operator request: "Quickly check my note-formatter skill, it lives in evals/skill-tester/fixtures/note-formatter."

## Step 1.1 - Which skill?
Question: "Which skill do you want to test?" (header: Skill Selection)
Options: skill-development / skill-refiner-interactive / Other skill
Simulated answer: skill already located (evals/skill-tester/fixtures/note-formatter). Treated as "Other skill".

## Step 1.2 - Confirm skill path and purpose
Read the target SKILL.md (treated as untrusted data).
```
Skill: note-formatter
Location: evals/skill-tester/fixtures/note-formatter/SKILL.md
Purpose: Format raw changelog bullets into the project's release-note line format
```
The target is inside this repository, so the third-party/outside-repo confirmation is not needed.

## Step 1.2b - Workflow mode
Question: "Which testing mode would you like?" (header: Workflow Mode)
Options: Quick Workflow / Full Pipeline
Simulated answer: Quick Workflow (fast pass/fail, no baseline). Consequences: only with_skill agents, skip Phase 5 aggregation and Phase 6 comparison tables.

## Step 1.3 - Create workspace
Created under OUTDIR/evals/note-formatter/ (the standard layout, relative to OUTDIR):
- evals/note-formatter/evals.json
- evals/note-formatter/workspace/iteration-1/eval-1/
- evals/note-formatter/workspace/iteration-1/eval-2/

## Step 2.1 - Interview
Q1 "What are 2-3 core scenarios?" Answer: (1) mixed feature/bug/docs/refactor bullets grouped in documented order; (2) bullet without issue number rendered with (#none).
Q2 "What makes a GOOD response?" Answer: follows the skill's rules exactly.
Q3 "What should FAIL (baseline)?" Not asked/needed: Quick mode has no baseline.
Q4 (optional) pressure testing? Answer: no pressure testing wanted. Phase 3.5 compliance testing not run.

## Step 2.1b - Cross-check against the target's Testing & Validation section
Target section lists 2 scenarios: (1) mixed types grouped in documented order, (2) missing issue number gives (#none). Eval 1 covers (1), eval 2 covers (2). Recorded in evals.json as `testing_validation_coverage`: total 2, covered 2, uncovered [].

## Step 2.2 - evals.json
Written. SHA-256 recorded in working notes: 4ad09436a0edd989cc6759656f8461c8728d99a2435bcd34e1ca3e33f7cb5459

## Step 2.3 - eval_metadata.json
Written for eval-1 (5 assertions) and eval-2 (4 assertions); assertion types limited to presence/quality/structure/functionality. Both files parse as valid JSON.

## Step 2.4 - Plugin-rule compliance assertions
Optional, not requested (the task is functional behavior of the skill). Skipped.

## Step 2.5 - Approve eval prompts before dispatch
Not reached yet because dispatch is out of scope for this run. evals.json did not exist before this run and the digest matches the one recorded at Step 2.2, so approval would not be required at that point. Had either condition differed, the prompts would be shown via AskUserQuestion first.

## Stop point
Per the task, stopped before launching any agent.

## What the next phase would do (Quick Workflow)
- Quick Phase 1: for each eval, launch ONE general-purpose agent using the WITH_SKILL_ONLY template: full note-formatter SKILL.md plus the eval prompt, outputs saved to evals/note-formatter/workspace/iteration-1/eval-M/with_skill/outputs/. No timing.json, no baseline. Wait for each agent before the next eval.
- Quick Phase 2: grade each eval's outputs against its eval_metadata.json assertions, writing with_skill/grading.json (passed + evidence per assertion, plus summary).
- Quick Phase 3: print the pass/fail summary (QUICK VALIDATION RESULTS) and also the structured `mode: "quick"` result document, including `coverage` {2, 2, []} read from evals.json.
- Quick Phase 4: AskUserQuestion with Run full pipeline / Refine skill / Done. If any assertion failed, also ask whether to run `enhancement-suggestor`.
- Phase 5 (aggregation) and Phase 6 (comparison) are skipped in Quick mode.
