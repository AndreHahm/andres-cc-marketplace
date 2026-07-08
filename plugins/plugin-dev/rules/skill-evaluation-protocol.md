---
paths:
  - ".claude/skills/skill-tester/**"
  - "plugins/*/skills/skill-tester/**"
---

# Evaluation Protocol

Apply after implementing improvement suggestions from `analyzing-sessions` that change how a skill responds to inputs.

## Pass/Fail Criteria

- Define pass/fail criteria for each test case BEFORE executing any test runs
- Pass criteria should be based on semantic equivalence, not exact string matching
- A test passes if the output achieves the same goal as the expected outcome

## Blind Testing

- Never expose expected outcomes to skill-test-subject agents
- Skill test subjects receive ONLY the skill content and input
- Any accidental leakage invalidates the test run

## Reporting

- Report results per-tier in a structured table format
- Include failure analysis with root cause and specific recommendations
- Order recommendations by expected impact (highest first)
- The refinement report is the primary deliverable — it must be actionable
