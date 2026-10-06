# transcript: skill-tester dry run, note-formatter (Quick mode, eval files only)

Operator request: "Quickly check my note-formatter skill, it lives in evals/skill-tester/fixtures/note-formatter."
Dry run: AskUserQuestion is simulated; each question and options are recorded with the simulated answer.

## Step 1.1 Which skill?
Question: "Which skill do you want to test?" Options: skill-development / skill-refiner-interactive / Other skill.
Simulated answer: skill already located (evals/skill-tester/fixtures/note-formatter). Question skipped; the operator named the path.

## Step 1.2 Confirm skill path and purpose
Read the target SKILL.md (treated as data).
```
Skill: note-formatter
Location: evals/skill-tester/fixtures/note-formatter/SKILL.md
Purpose: Format raw changelog bullets into the project's release-note line format.
```
Target manifest recorded (relative path to SHA-256):
{"SKILL.md": "e11f312b5c9ad335fd36185bcabe7092bbccf45b95df48b97d42c38508689a22"}

Trust question: "Run this skill's instructions in full-tool agents?" Options: Continue / Choose another skill / Stop.
Simulated answer: Continue (first option). The target's own allowed-tools is not enforced in the test agent; it declares none, and its text contains no instruction-like content aimed at the tester.

## Step 1.2b Choose workflow mode
Question: "Which testing mode would you like?" Options: Quick Workflow / Full Pipeline.
Simulated answer: Quick Workflow. Note: "Quick mode: only with_skill, no baseline comparison". No baseline agents, no timing, no aggregation, no benchmark.json.

## Step 1.3 Create workspace
Created (under OUTDIR, standard layout): evals/note-formatter/ and evals/note-formatter/workspace/iteration-1/.

## Step 2.1 Interview
Simulated answers:
- Q1 scenarios: (1) mixed feature/bug/docs/refactor bullets grouped in documented order; (2) bullet without issue number rendered with (#none).
- Q2 good response: follows the skill's rules exactly.
- Q3 baseline failure: not asked in Quick mode's outputs (no baseline); not needed.
- Q4 pressure testing: no. So no pdk-compliance-testing run and no pressure_condition on any assertion.

## Step 2.1b Cross-check against target's Testing & Validation
Target lists 2 numbered scenarios: (1) mixed types grouped in documented order, (2) bullet without issue number rendered with (#none). Eval 1 covers item 1, eval 2 covers item 2. Result: 2 of 2 covered, none uncovered. Recorded in evals.json `testing_validation_coverage`.

## Step 2.2 Generate evals.json
Wrote evals/note-formatter/evals.json (2 evals). SHA-256 recorded:
fe44fdabfde412584f942e609c07e875aaf0231f42ad5d226bf553c464195e99
Note: skill_path is the repo-relative confirmed Location, ending in SKILL.md.

## Step 2.3 Generate eval_metadata.json
Wrote workspace/iteration-1/eval-1/eval_metadata.json (5 assertions) and eval-2/eval_metadata.json (4 assertions). Assertion types used: structure, functionality, quality, presence. with_skill/ subdirectories are created in the run phase.

## Step 2.4 Plugin-rule compliance assertions
Skipped: optional, and the operator wants a functional check only, not plugin-rule compliance.

## Step 2.5 Approve eval prompts before any dispatch
Prompts shown:
- Eval 1: "Format these changelog bullets as release notes: - docs: update install guide (#12) / - bug: fix crash on empty input (#7) / - refactor: split parser module (#9) / - feature: add dark mode (#3) / - bug: handle timeout in sync (#15) / - feature: add export to CSV (#4)"
- Eval 2: "Format these changelog bullets as release notes: - feature: add keyboard shortcuts (#21) / - bug: fix typo in error message"
Question: "Approve these eval prompts for dispatch to a full-tool agent?" Options: Approve / Edit prompts / Stop.
Simulated answer: Approve (first option). Manifest and evals.json digest re-recorded (unchanged from the values above).

## STOP POINT
Per the task, work stops here before any agent is launched. Files created: evals.json and two eval_metadata.json files, all under OUTDIR/evals/note-formatter/.

## What the next phase would do (Quick Phase 1 to 4)
1. Quick Phase 1: for each eval, one at a time, launch one general-purpose agent using the WITH_SKILL_ONLY template (full note-formatter SKILL.md plus the eval prompt), saving outputs to evals/note-formatter/workspace/iteration-1/eval-M/with_skill/outputs/. No baseline, no timing.json. Wait for each to finish.
2. Quick Phase 2: grade each eval's outputs against its eval_metadata.json assertions and write eval-M/with_skill/grading.json (passed + evidence per assertion, summary with pass_rate). Any instruction-like text in agent output is only recorded as suspicious evidence.
3. Quick Phase 3: print the pass/fail summary (QUICK VALIDATION RESULTS) plus the structured `mode: "quick"` JSON result document, with `coverage` copied from evals.json (2 of 2 covered). Phase 5 aggregation and Phase 6 tables are skipped.
4. Quick Phase 4: ask "What would you like to do?" with Run full pipeline / Refine skill / Done. If any assertion failed, also ask whether to run enhancement-suggestor (never without asking).
