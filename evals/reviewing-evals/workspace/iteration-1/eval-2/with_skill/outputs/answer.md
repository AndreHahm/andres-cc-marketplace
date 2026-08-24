# Check 2 (Coverage-claim accuracy) — Defect Found

## Defect: Overcounted coverage claim (declared_scenarios_covered is wrong)

`testing_validation_coverage` claims:
```
declared_scenarios_total: 3
declared_scenarios_covered: 3
uncovered: []
```

But SKILL.md's own Testing & Validation section defines 3 scenarios:
1. Creating a skill
2. Converting a slash command
3. Improving an existing skill

The `evals` array contains only **one** eval (id 1: "Create a new skill for X"), which exercises scenario 1 only. There is no eval whose prompt exercises scenario 2 (converting a slash command) or scenario 3 (improving an existing skill).

So the actual coverage is:
- `declared_scenarios_covered` should be **1**, not 3.
- `uncovered` should list scenarios 2 and 3, not be empty.

## Arithmetic check (per Check 2's third bullet)

`declared_scenarios_covered + len(uncovered) == declared_scenarios_total` → as written, `3 + 0 == 3` is internally self-consistent, so the arithmetic identity alone does not catch this. The defect only surfaces by actually reading each eval's prompt against each declared scenario (Check 2's first two bullets) — exactly the "eval 2 scenario 3 vs scenario 2" past instance the skill calls out: a coverage count can be internally consistent yet still false because no eval genuinely exercises the scenarios it claims to cover.

## Corrected values

```json
"testing_validation_coverage": {
  "declared_scenarios_total": 3,
  "declared_scenarios_covered": 1,
  "uncovered": [
    "converting a slash command",
    "improving an existing skill"
  ]
}
```

## Recommendation

Either add evals that actually exercise scenarios 2 and 3, or correct `declared_scenarios_covered` to 1 and list the two missing scenarios in `uncovered` so the coverage claim matches what the eval suite actually tests.
