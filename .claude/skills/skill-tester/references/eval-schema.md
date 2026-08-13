# Evaluation Schema Reference

Complete JSON schemas for all evaluation data files created during the skill-tester pipeline.

---

## evals.json — Test Case Definitions

**Location:** `./evals/<skill-name>/evals.json`

**Purpose:** Central registry of all test cases for a skill. Defines what the skill is being tested on.

**Schema:**

```json
{
  "skill_name": "string (required) — name of skill being tested",
  "skill_path": "string (required) — path to SKILL.md file",
  "description": "string (required) — one-line purpose of skill",
  "evals": [
    {
      "id": "integer (required) — unique eval identifier (1, 2, 3, ...)",
      "name": "string (required) — short eval scenario name",
      "prompt": "string (required) — complete user prompt for this test case",
      "expected_output": "string (required) — description of good output",
      "files": [
        "string (optional) — file paths that should be created or modified"
      ]
    }
  ],
  "testing_validation_coverage": {
    "declared_scenarios_total": "integer (optional) — scenario count from the target's own Testing & Validation section, per Step 2.1b's cross-check; omit if the target has no such section",
    "declared_scenarios_covered": "integer (optional) — how many of those this eval set exercises",
    "uncovered": ["string (optional) — declared scenario text not covered by any eval"]
  }
}
```

**Example:** see `assets/evals-example.json`.

`testing_validation_coverage` is written once by Step 2.1b's cross-check during eval creation, then read back (not recomputed) by Quick Phase 3 and Phase 6 Step 6.1 to populate their own structured output's `coverage` field.

---

## eval_metadata.json — Assertions Per Eval

**Location:** `<workspace>/iteration-N/eval-M/eval_metadata.json`

**Purpose:** Define what "success" means for a specific eval. Contains assertions Claude will check against outputs.

**Schema:**

```json
{
  "eval_id": "integer (required) — which eval this metadata applies to",
  "skill_path": "string (required) — path to SKILL.md being tested",
  "assertions": [
    {
      "text": "string (required) — assertion to verify (e.g., 'Output includes a clear skill name')",
      "type": "string (required) — assertion category: 'presence', 'quality', 'structure', 'functionality'",
      "target": "string (required) — where to look for this assertion (e.g., 'SKILL.md frontmatter', 'references/ directory', 'outputs/ directory')",
      "pressure_condition": "string (optional) — name of a pressure type from skill-development's Pressure Types table (references/compliance-testing.md) if this assertion was verified under adversarial pressure framing rather than a cooperative baseline; omit for standard assertions"
    }
  ]
}
```

**Assertion Types:**

- `presence` — File/section/field exists (or is absent)
- `quality` — Content meets quality criteria (clarity, specificity, completeness)
- `structure` — Directory layout, file organization, nesting levels match requirements
- `functionality` — Skill performs expected action, produces expected behavior

**`pressure_condition` (optional):** this pipeline's own agent dispatch doesn't apply adversarial framing — it runs cooperative with_skill/baseline scenarios. Set this field only to record that a given assertion's evidence came from a `skill-development` Phase 3.5 compliance-testing run (`references/compliance-testing.md`) rather than this pipeline, so a reader of `grading.json` can tell which methodology produced which result. Deliberately not a closed enum here — the pressure-type list is owned by `compliance-testing.md`'s Pressure Types table; duplicating it as a hardcoded list here would drift if that table changes.

**Example:** see `assets/eval-metadata-example.json`.

---

## grading.json — Assertion Results

**Location:** `<workspace>/iteration-N/eval-M/with_skill/grading.json` and `baseline/grading.json`

**Purpose:** Record whether each assertion passed or failed. Includes evidence quotes from outputs.

**Schema:**

```json
{
  "eval_id": "integer (required) — which eval this grades",
  "configuration": "string (required) — 'with_skill' or 'baseline'",
  "assertions_evaluated": [
    {
      "text": "string (required) — assertion text (from eval_metadata.json)",
      "passed": "boolean (required) — true if assertion passed",
      "evidence": "string (required) — quote or reference from output proving pass/fail"
    }
  ],
  "summary": {
    "assertions_total": "integer — total assertions evaluated",
    "assertions_passed": "integer — count of passed assertions",
    "pass_rate": "float (0.0–1.0) — assertions_passed / assertions_total"
  }
}
```

**Example (with_skill, high pass rate):** see `assets/grading-with-skill-example.json`.

**Baseline example (lower pass rate):** see `assets/grading-baseline-example.json`.

---

## timing.json — Execution Metrics

**Location:** `<workspace>/iteration-N/eval-M/with_skill/timing.json` and `baseline/timing.json`

**Purpose:** Track resource usage (tokens, wall-clock time) for each eval run.

**Schema:**

```json
{
  "total_tokens": "integer (required) — total tokens consumed (input + output)",
  "duration_ms": "integer (required) — wall-clock execution time in milliseconds",
  "model": "string (required) — model used (e.g., 'claude-opus-4-6')",
  "timestamp": "string (optional) — ISO 8601 timestamp when eval ran"
}
```

**Example:**

```json
{
  "total_tokens": 2847,
  "duration_ms": 8234,
  "model": "claude-opus-4-6",
  "timestamp": "2026-03-04T10:35:22Z"
}
```

---

## benchmark.json — Aggregated Results

**Location:** `<workspace>/iteration-N/benchmark.json`

**Purpose:** Summary statistics across all evals for an iteration. Generated by `aggregate_benchmark.py`.

**Schema:** see `assets/benchmark-schema.json`.

**Example:** see `assets/benchmark-example.json`. `skill_name` is derived by `aggregate_benchmark.py` from the standardized workspace path (`./evals/<skill-name>/workspace/iteration-N`), or set explicitly via `--skill-name`.

---

## Structured Result Documents (Quick Phase 3 / Phase 6 Step 6.1)

Both modes print a machine-readable result document alongside their human-readable summary
(additive, never a replacement) — a caller parses this instead of re-deriving pass/fail from
prose. Both share `coverage`, sourced from `evals.json`'s own `testing_validation_coverage`
field (Step 2.1b's cross-check) and omitted entirely when the target had no Testing &
Validation section to cross-check against, rather than emitted as misleading zeros.

**Quick Workflow** (`mode: "quick"`):

```json
{
  "version": "1.0",
  "source": "skill-tester",
  "mode": "quick",
  "skill_name": "<skill-name>",
  "summary": {"assertions_passed": 11, "assertions_total": 15, "pass_rate": 0.73},
  "results": [
    {"eval_id": 1, "name": "<Scenario>", "status": "pass", "assertions_passed": 5, "assertions_total": 5}
  ],
  "coverage": {"declared_scenarios_total": 4, "declared_scenarios_covered": 3, "uncovered": ["<scenario text>"]}
}
```

**Full Pipeline** (`mode: "full_pipeline"`) — `results[].with_skill`/`baseline` mirror
`benchmark.json`'s own per-eval fields above rather than introducing a second set of field
names for the same numbers:

```json
{
  "version": "1.0",
  "source": "skill-tester",
  "mode": "full_pipeline",
  "skill_name": "<skill-name>",
  "iteration": 1,
  "summary": {"with_skill_pass_rate": 0.965, "baseline_pass_rate": 0.67, "improvement_points": 29.5},
  "results": [
    {"eval_id": 1, "name": "<Scenario>",
     "with_skill": {"passed": 3, "total": 3, "tokens": 2500, "duration_s": 8},
     "baseline": {"passed": 2, "total": 3, "tokens": 1800, "duration_s": 5}}
  ],
  "coverage": {"declared_scenarios_total": 4, "declared_scenarios_covered": 4}
}
```

---

## Workspace Directory Structure (Standardized)

All evaluation artifacts live in a **centralized `./evals/` directory at project root**, not inside skill directories — see `SKILL.md`'s own "Artifact Location (Standardized)" section for the full directory tree; not restated here to avoid drift.

**Advantages:**
- Easy to compare multiple skills' test results in one place
- Keeps skill directories clean (no `/evals/` subdirs inside skills/)
- Natural location for project-wide evaluation data
- Simplifies path references in automation and scripts

---

## aggregate_benchmark.py — The Aggregation Script

The Python script reads all `grading.json` and `timing.json` files from an iteration directory and produces `benchmark.json`.

**Invocation:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/aggregate_benchmark.py ./evals/<skill-name>/workspace/iteration-N [--skill-name <name>]
```

`skill_name` in the output is derived from the standardized `./evals/<skill-name>/workspace/iteration-N` path; pass `--skill-name` explicitly if the path doesn't follow that convention.

**Example:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/aggregate_benchmark.py ./evals/skill-development/workspace/iteration-1
```

**Output:**

```
✓ Benchmark aggregated: ./evals/skill-development/workspace/iteration-1/benchmark.json

Summary:
  Evals processed: 2
  With Skill pass rate: 90.0%
  Baseline pass rate: 50.0%
  Improvement: +40.0 percentage points
  Token cost: +602
  Duration cost: +2667ms
```

**Logic:**

1. Discover all `eval-N/` directories
2. For each eval:
   - Read `with_skill/grading.json` → extract pass_rate
   - Read `baseline/grading.json` → extract pass_rate
   - Read `with_skill/timing.json` → extract total_tokens, duration_ms
   - Read `baseline/timing.json` → extract total_tokens, duration_ms
   - Calculate delta (with_skill - baseline)
3. Compute summary statistics:
   - Average pass rates across all evals
   - Average tokens and duration across all evals
   - Calculate improvement (with_skill - baseline)
4. Write `benchmark.json` with all results

See skill-tester `SKILL.md` Phase 5 for integration instructions.

---

## Agent Prompt Templates

Standard prompts for evaluation agents. Reference these in Phase 3 (Full Pipeline) and Quick Workflow.

### WITH_SKILL Template (Full Pipeline — Phase 3)

```
Agent type: general-purpose
Prompt: "
You are testing a Claude Code skill. Your job: HELP THE USER ACCOMPLISH THEIR TASK
using the skill provided below.

SKILL TO USE:
<read and include full SKILL.md content>

USER TASK:
<eval-N prompt from evals.json>

After completing the task, save all outputs (code, files, notes) to:
./evals/<skill-name>/workspace/iteration-N/eval-M/with_skill/outputs/

Then create ./evals/<skill-name>/workspace/iteration-N/eval-M/with_skill/timing.json:
{ "total_tokens": <count>, "duration_ms": <milliseconds>, "model": "claude-opus-4-6" }
"
```

### BASELINE Template (Full Pipeline — Phase 3)

```
Agent type: general-purpose
Prompt: "
You are providing a BASELINE. Help the user accomplish their task WITHOUT any special
skill or methodology. NO SKILLS AVAILABLE. Use standard Claude capabilities only.

USER TASK:
<eval-N prompt from evals.json>

After completing the task, save all outputs (code, files, notes) to:
./evals/<skill-name>/workspace/iteration-N/eval-M/baseline/outputs/

Then create ./evals/<skill-name>/workspace/iteration-N/eval-M/baseline/timing.json:
{ "total_tokens": <count>, "duration_ms": <milliseconds>, "model": "claude-opus-4-6" }
"
```

### WITH_SKILL_ONLY Template (Quick Workflow)

```
Agent type: general-purpose
Prompt: "
You are testing a Claude Code skill. Your job: HELP THE USER ACCOMPLISH THEIR TASK
using the skill provided below.

SKILL TO USE:
<read and include full SKILL.md content>

USER TASK:
<eval-N prompt from evals.json>

After completing the task, save all outputs to:
./evals/<skill-name>/workspace/iteration-N/eval-M/with_skill/outputs/

NO timing metrics needed for quick workflow. Just save your work.
"
```
