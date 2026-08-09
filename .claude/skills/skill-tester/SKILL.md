---
name: skill-tester
description: >-
  Test and benchmark Claude Code skills empirically using evaluation-driven development.
  Use when validating a skill's effectiveness, running evals, comparing skill vs. baseline
  performance, running benchmarks with timing/token metrics, or iterating on skill improvements
  based on empirical data. Supports both a fast pass/fail check and a full baseline-comparison
  benchmark with timing/token metrics.
allowed-tools: Read Write Edit Glob Grep Agent Bash(python:*) Skill
---

# Skill Tester

**Purpose:** Empirically validate Claude Code skills through evaluation-driven testing. Proves skills actually help Claude (with data) rather than guessing.

## Mindset

Skills must be **measured, not assumed**. This pipeline provides systematic evidence: Does the skill improve Claude's performance? By how much? What should we improve next?

## When to Use

- Validating a newly created skill against baseline Claude performance without it
- Benchmarking skill refinements across multiple iterations
- Proving skill effectiveness with timing, token usage, and pass rates side-by-side
- Making data-driven decisions on what to improve next in a skill

## When NOT to Use

- **Creating skills** — use `skill-development` instead.
- **Reviewing skill quality** — use `skill-reviewer` for a single-pass structural quality check without benchmarking.
- **Validating plugin structure** — use the `plugin-validator` agent for manifest and directory checks.
- **Testing during initial skill authoring (Phase 3 of skill creation, before the skill is finalized)** — use `skill-development`'s own Phase 3 workflow; switch to this skill once the skill exists and you need a dedicated with/baseline benchmark or a multi-iteration comparison.
- **Automated structural fix-review loops until skill-reviewer passes** — use `skill-improver-loop` instead; this skill iterates on empirical eval/benchmark data, not skill-reviewer's structural findings.
- **Sweeping a batch of skills' persisted smoke-test scripts in one pass** — use the `smoke-tester` agent instead (Structured Output Mode available) when more than a small handful of skills need a quick pass/fail/skipped/error check; this skill's Quick Workflow is for one skill's eval-based validation, not a multi-skill persisted-script sweep.

## Core Principles

**Empirical Evidence** — Intuition ≠ proof. Collect actual performance data: pass rates, tokens, timing.

**Parallel Testing** — For each eval, test WITH skill AND baseline SIMULTANEOUSLY (2 agents per eval, in parallel). Eliminates confounding variables from different test runs.

**Workspace Isolation** — Each iteration lives in `workspace/iteration-N/`. Keeps history clean. Easy to compare iteration 1 → 2 → 3 performance.

**Schema Consistency** — All JSON outputs follow strict schemas (evals.json, grading.json, benchmark.json, timing.json). Enables reliable aggregation and comparison.

## Quick Start: The 7-Phase Pipeline

```
Phase 1: Setup          → Identify skill + confirm what it does
Phase 2: Create Evals   → Interview user → write test cases + assertions
Phase 3: Run Tests      → Launch 2 agents per eval (with_skill + baseline) in parallel
Phase 4: Grade Results  → Evaluate outputs against assertions
Phase 5: Aggregate      → Run aggregation script to compute benchmark.json
Phase 6: Review Summary → Show comparison table + improvement suggestions
Phase 7: Iterate        → Update skill + run next iteration (or stop if satisfied)
```

## Artifact Location (Standardized)

**All evaluation artifacts live in a centralized `./evals/` directory at project root.**

```
./evals/                          ← Project root, NOT inside skill directory
├── <skill-name-1>/
│   ├── evals.json
│   └── workspace/
│       ├── iteration-1/
│       │   ├── eval-1/, eval-2/, eval-3/  ← Per-eval directories
│       │   └── benchmark.json              ← Aggregated results
│       └── iteration-2/
│           └── ...
└── <skill-name-2>/
    └── ...
```

See `references/workflow.md` — "Phase 1: Setup" for workspace location rationale.

---

## PHASE 1: Setup

**Goal:** Identify the skill being tested. Confirm what it does. Prepare workspace.

### Step 1.1: Ask User - Which Skill?

Use AskUserQuestion to ask which skill to test:

```
question: "Which skill do you want to test?"
header: "Skill Selection"
options: [
  {label: "skill-development", description: "Testing skill-development from skills/ directory"},
  {label: "skill-refiner-interactive", description: "Testing skill-refiner-interactive from skills/ directory"},
  {label: "Other skill", description: "Testing a skill not listed above"}
]
```

⏸️ **Collect user input.** Wait for response before proceeding.

### Step 1.2: Confirm Skill Path & Purpose

Read the skill's SKILL.md to understand:
- What does this skill do?
- What are its core use cases?
- What problem does it solve?

Show user a summary:
```
Skill: <name>
Location: <path>
Purpose: <one-line summary from description>
```

### Step 1.2b: Choose Workflow Mode

**Question:** Which testing mode do you want?

Use AskUserQuestion with 2 options:

```
questions: [
  {
    question: "Which testing mode would you like?",
    header: "Workflow Mode",
    options: [
      {
        label: "Quick Workflow",
        description: "Fast validation: only test WITH skill (no baseline), no timing metrics. Just pass/fail on assertions. Perfect for quick checks."
      },
      {
        label: "Full Pipeline",
        description: "Complete analysis: test WITH skill + baseline parallel, measure tokens/timing, aggregate & compare. For comprehensive benchmarking."
      }
    ],
    multiSelect: false
  }
]
```

⏸️ **Collect user input.**

**If Quick Workflow selected:**
- Skip to Phase 2 with note: "Quick mode: only with_skill, no baseline comparison"
- Jump to simplified Phase 3 (only 1 agent per eval)
- Skip Phase 5 (aggregation) and Phase 6 comparison tables
- Show simple pass/fail results

**If Full Pipeline selected:**
- Continue with standard 7-phase pipeline (proceed to Step 1.3)

### Step 1.3: Create Workspace

Create directory structure in project root (standardized):
```
./evals/<skill-name>/
./evals/<skill-name>/workspace/iteration-1/
```

Log workspace path. All subsequent phases write to this directory (NOT inside the skill's directory).

---

## PHASE 2: Create Evals

**Goal:** Build evaluation cases that measure skill effectiveness.

### Step 2.1: Interview User for Test Scenarios

Ask 3 questions plus an optional 4th (use AskUserQuestion with free-form "Other" option):

```
Question 1: "What are 2-3 core scenarios this skill should handle?"
Example: "skill-development should handle: creating a new skill from scratch,
converting a slash command, improving an existing skill"

Question 2: "For each scenario, what makes a GOOD response?"
Example: "Good responses: skill has clear name, description with trigger phrases,
correct SKILL.md structure, efficient references/"

Question 3: "What should FAIL (baseline without skill)?"
Example: "Baseline will miss best practices, create vague descriptions,
skip necessary structure"

Question 4 (optional): "Should any of these scenarios also be tested under pressure —
e.g. time constraints, sunk cost, exhaustion, authority — to verify the skill holds up
when an agent is incentivized to skip it?"
Example: "Yes — the validation scenario should be re-run with a 'you have 5 minutes' framing"
```

⏸️ **Collect responses.** Store in memory.

If Question 4 is answered yes, this pipeline's quantitative pass rates don't cover that axis — run `skill-development`'s Phase 3.5 compliance testing (`references/compliance-testing.md`) before or alongside this pipeline; see "Integration with skill-development, skill-refiner-interactive" in `references/workflow.md`.

### Step 2.1b: Cross-Check Against the Target's Own Testing & Validation Section

Before writing `evals.json`, `Read` the target skill's own SKILL.md for a "Testing & Validation" section. If one exists and lists numbered scenarios, check whether the eval scenarios collected in Step 2.1 collectively exercise each item — or explicitly note the gap for any that aren't covered. A skill's own Testing & Validation checklist is a direct, authoritative claim about what "tested" should mean for it; writing an eval set that doesn't cross-check against it risks shipping eval coverage narrower than the skill's own documented claims, which reads as tested when it isn't.

### Step 2.2: Generate evals.json

Write `./evals/<skill-name>/evals.json` with fields: `skill_name`, `skill_path`, `description`, and `evals` array (each entry: `id`, `name`, `prompt`, `expected_output`, `files`).

See `references/eval-schema.md` for full schema and annotated examples.

### Step 2.3: Generate eval_metadata.json Files

Create `workspace/iteration-1/eval-N/eval_metadata.json` for each eval. Required fields: `eval_id`, `skill_path`, `assertions` array (each entry: `text`, `type`, `target`). Assertion types: `presence`, `quality`, `structure`, `functionality`.

Create directories: `workspace/iteration-1/eval-1/`, `eval-2/`, etc. (with_skill and baseline subdirs created in Phase 3).

See `references/eval-schema.md` for full schema and annotated examples.

### Step 2.4: Plugin-Rule Compliance Assertions (Optional)

When evaluating a skill for plugin-rule compliance (naming, tool-scoping, language, formatting), invoke `plugin-rulebook` before writing `eval_metadata.json` to obtain the active rule set. Use each enabled rule as a separate assertion:

```
Skill: plugin-rulebook
→ Returns active rules with descriptions, examples, and enforcement levels
```

Add rule-compliance assertions to `eval_metadata.json` alongside functional assertions:

```json
{"text": "allowed-tools uses space-separated format (R6)", "type": "structure", "target": "SKILL.md frontmatter"}
```

---

## QUICK WORKFLOW (Alternative Path)

**If user chose "Quick Workflow" in Step 1.2b, follow this streamlined path instead of Phases 3-7.**

### Quick Phase 1: Run WITH_SKILL Only (No Baseline)

**Goal:** Test the skill itself. No baseline comparison, no timing metrics. Just: Does it work?

For EACH eval in evals.json, launch ONE agent (no parallel baseline):

See `references/eval-schema.md` — "Agent Prompt Templates" section for the WITH_SKILL_ONLY prompt template (Quick Workflow variant, no timing metrics).

⏸️ **Wait for agent completion before proceeding to next eval.**

### Quick Phase 2: Grade Results (Assertions Only)

For each eval, grade against assertions in eval_metadata.json. Record pass/fail + evidence for each assertion.
Save to: `./evals/<skill-name>/workspace/iteration-1/eval-N/with_skill/grading.json`

See `references/eval-schema.md` for grading.json schema.

### Quick Phase 3: Show Results

Display simple pass/fail summary (no benchmark.json):

```
QUICK VALIDATION RESULTS: <skill-name>
====================================

Eval 1: <Scenario>  ✓ PASS (5/5 assertions)
Eval 2: <Scenario>  ✓ PASS (4/5 assertions)
Eval 3: <Scenario>  ✗ FAIL (2/5 assertions)

Summary: 11/15 assertions passed (73%)
Status: Ready to refine or deploy
```

### Quick Phase 4: Next Steps

Ask user:

```
question: "What would you like to do?"
header: "Next Steps"
options: [
  {label: "Run full pipeline", description: "Move to complete benchmarking with baseline comparison"},
  {label: "Refine skill", description: "Update skill based on failed assertions"},
  {label: "Done", description: "Quick validation complete"}
]
```

---

## PHASE 3: Run Tests

**Goal:** Execute 2 agents per eval (WITH skill + BASELINE) in parallel. Capture outputs.

### Step 3.1: Spawn Agents (Parallel Execution)

For EACH eval, launch 2 agents SIMULTANEOUSLY in one Agent tool call:

See `references/eval-schema.md` — "Agent Prompt Templates" section for the WITH_SKILL and BASELINE prompt templates.

⏸️ **Wait for both agents to complete before proceeding to Phase 4.**

---

## PHASE 4: Grade Results

**Goal:** Evaluate each agent's outputs against assertions in eval_metadata.json.

### Step 4.1: Review Outputs & Grade

For EACH eval:

1. Read `with_skill/outputs/` files
2. Read `baseline/outputs/` files
3. For EACH assertion in `eval-N/eval_metadata.json`:
   - Does with_skill output satisfy the assertion? (true/false)
   - Does baseline output satisfy the assertion? (true/false)
   - Collect brief evidence quotes from outputs

### Step 4.2: Write grading.json Files

Create `workspace/iteration-1/eval-N/with_skill/grading.json` and `baseline/grading.json`.
Required fields: `eval_id`, `configuration` (`"with_skill"` or `"baseline"`), `assertions_evaluated` array (each: `text`, `passed`, `evidence`), `summary` (`assertions_total`, `assertions_passed`, `pass_rate`).

See `references/eval-schema.md` for full schema and pass/fail examples.

---

## PHASE 5: Aggregate

**Goal:** Compute benchmark.json with summary stats (pass rates, tokens, timing).

### Step 5.1: Run Aggregation Script

Execute the aggregation script (see `scripts/aggregate_benchmark.py` for the full implementation; `references/eval-schema.md` for the invocation command and output schema):

```bash
python ${CLAUDE_SKILL_DIR}/scripts/aggregate_benchmark.py \
  ./evals/<skill-name>/workspace/iteration-1
```

Example:
```bash
python ${CLAUDE_SKILL_DIR}/scripts/aggregate_benchmark.py \
  ./evals/skill-development/workspace/iteration-1
```

This reads all grading.json and timing.json files from the standardized location, outputs `benchmark.json` with per-eval stats (pass rates, tokens, duration, delta) and summary statistics.

See `references/eval-schema.md` for benchmark.json schema and full example.

---

## PHASE 6: Review Summary

**Goal:** Show user a clear comparison table + next steps.

### Step 6.1: Render Comparison Table

Display results in human-readable format:

```
EVALUATION RESULTS: skill-tester iteration-1
==============================================

Eval 1: [Scenario Name]
  WITH SKILL:  3/3 (100%) | 2500 tokens | 8s
  BASELINE:    2/3 (67%)  | 1800 tokens | 5s
  DELTA:       +33% better | +700 tokens | +3s

Eval 2: [Scenario Name]
  WITH SKILL:  2/3 (67%)  | 2100 tokens | 7s
  BASELINE:    2/3 (67%)  | 1900 tokens | 4s
  DELTA:       Even      | +200 tokens | +3s

SUMMARY
-------
With Skill Avg:    96.5% pass rate | 2300 avg tokens
Baseline Avg:      67.0% pass rate | 1850 avg tokens
IMPROVEMENT:       +29.5 percentage points
```

### Step 6.2: Offer Next Steps

Ask user (AskUserQuestion):

```
question: "What would you like to do?"
header: "Next Steps"
options: [
  {
    label: "Iterate (update skill, run next iteration)",
    description: "Based on results, modify the skill and run workspace/iteration-2"
  },
  {
    label: "Stop (satisfied with results)",
    description: "Evaluation complete. Save benchmark data for reference"
  },
  {
    label: "Refine evals (change test cases, rerun)",
    description: "Update evals.json and run iteration again with same eval set"
  }
]
```

⏸️ **Collect user input.**

---

## PHASE 7: Iterate

**Goal:** If user chose "Iterate", update the skill and run next iteration.

### Step 7.1: Get Improvement Feedback

Ask user (AskUserQuestion, free-form):

```
question: "What would you like to improve about the skill?"
header: "Improvement"
```

⏸️ **Collect feedback.**

### Step 7.2: Update Skill

Use `skill-refiner-interactive` or direct edits to improve the skill based on feedback:
- Reword descriptions for clarity
- Add missing guidance to SKILL.md body
- Reorganize references
- Trim token usage

### Step 7.3: Run Next Iteration

Create `workspace/iteration-2/` directory. Repeat Phases 3–6 with updated skill.

### Step 7.4: Compare Iterations

Show delta between iteration-1 benchmark and iteration-2 benchmark:

```
ITERATION COMPARISON
====================
Iteration 1 pass rate: 67%  → Iteration 2: 95% (+28 points)
Iteration 1 tokens:   1900  → Iteration 2: 2100 (+200, acceptable)
```

Loop back to Phase 6 (Step 6.2) to ask: iterate again or stop?

---

**Suggested next step:** if a benchmark run shows a regression, a failed assertion, or a Quick Workflow FAIL, ask with `AskUserQuestion`: "Run `enhancement-suggestor` against these results for a classified (complexity/risk/benefit) WHAT/WHY/HOW action plan?" — options "Yes" / "No". If yes, invoke the `enhancement-suggestor` agent (via `Agent`) against the results. Never invoke it without asking first.

## Testing & Validation

After a test run, verify:

1. **Trigger phrases** — confirm skill activates on: "run evals on skill-X", "benchmark this skill", "validate skill performance", "compare skill vs. baseline", "test skill effectiveness"
2. **Non-triggers** — confirm skill does NOT activate on: "review my skill structure", "create a new skill", "fix this PR"
3. **Mode selection** — Quick Workflow and Full Pipeline branches both produce correctly structured output directories
4. **Schema integrity** — all JSON files (`evals.json`, `grading.json`, `benchmark.json`, `timing.json`, `eval_metadata.json`) validate against `references/eval-schema.md` schemas
5. **Baseline parity** — baseline agent receives no SKILL.md content; with_skill agent receives full SKILL.md content

**Verified 2026-07-11:** items 1 and 2 checked directly against the current frontmatter description — each of the 5 trigger phrases maps to specific description language ("running evals", "validating a skill's effectiveness", "comparing skill vs. baseline performance", "running benchmarks"), and none of the 3 non-trigger phrases share that vocabulary (they map to `skill-reviewer`'s and `skill-development`'s domains instead). `aggregate_benchmark.py`'s new guard/sort behavior (items covering script robustness) was verified with synthetic fixtures — see the script's own commit history. A live end-to-end pipeline run (spawning real with_skill/baseline agents) has not been performed — that remains the one unverified item.

**Quality gates:**
- [ ] WITH_SKILL and BASELINE agents launched simultaneously (not sequentially) in Full Pipeline
- [ ] `benchmark.json` exists in `workspace/iteration-N/` before presenting Phase 6 summary
- [ ] All destructive operations (deleting eval dirs) confirmed with user before execution

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/eval-schema.md` | JSON schemas, agent prompt templates, and workspace structure |
| `references/workflow.md` | Decision points and detailed workflow guidance |
| `scripts/aggregate_benchmark.py` | Python script that aggregates grading/timing data into benchmark.json |
| `plugin-rulebook` skill | Active rule configuration for compliance-testing assertions |
| `enhancement-suggestor` agent | Turns a regression/fail/delta result into a classified, prioritized action plan |
