---
paths:
  - ".claude/skills/skill-tester/**"
  - "plugins/*/skills/skill-tester/**"
---

# Evaluation Protocol

Apply after implementing any suggestion — from `analyzing-sessions`, `enhancement-suggestor`, a direct user request, or any other source — that changes how a skill responds to inputs. The originating source doesn't change what validation is owed; a behavior change made on direct request needs the same evaluation rigor as one sourced from a retrospective.

**Scope — what counts as "changes how a skill responds to inputs":** a change to SKILL.md (or its references/) prose/guidance that alters what Claude actually does when following the skill on some input. This protocol's Blind Testing model (skill-test-subject agents receiving only skill content + input) is built for exactly that case. Two categories are explicitly **out of scope**, validated by other means instead:
- **Deterministic script/code logic changes** (e.g. a language port, a bug fix in a `scripts/*.py` file) — these have no "response to inputs" in the agentic sense; validate via direct execution against fixtures/known-good output, not blind agent testing.
- **Prose fixes that restore an already-documented cross-reference or already-intended behavior** without changing what the skill is supposed to do (e.g. correcting a guardrail tier's name in one section to match the name already used elsewhere in the same file) — these correct a bug in describing existing intended behavior, not a change to the behavior itself. If there's genuine doubt whether a fix in this category actually changes runtime behavior (e.g. because something does a literal string match against the corrected text), treat it as in-scope instead of assuming out-of-scope.

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
