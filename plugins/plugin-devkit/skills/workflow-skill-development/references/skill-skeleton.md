# SKILL.md Skeleton

Standard skeleton for every workflow-based skill, regardless of pattern. The block below is an intentional whole-example illustration: splitting it would destroy its value as a single copy-ready file.

```markdown
---
name: kebab-case-name
description: >-
  Third-person description with trigger keywords. This is how Claude decides
  to activate the skill.
allowed-tools: Tool1 Tool2 Tool3
# Optional fields: see tool-assignment-guide.md for the full reference
---

# Title

## Quick Start
[2-4 numbered steps: the shortest path from activation to a finished result]

## Essential Principles
[3-5 non-negotiable rules with WHY explanations]

## When to Use
[4-6 specific scenarios — scopes behavior after activation]

## When NOT to Use
[3-5 scenarios with named alternatives — scopes behavior after activation]

## [Pattern-Specific Section]
[Routing table / Pipeline steps / Phase list / Gates]

## Quick Reference
[Compact tables for frequently-needed info]

## Reference Index
[Links to all supporting files]

## Success Criteria
[Checklist for output validation]

## Testing & Validation
[Phrases that should activate the skill; phrases that should NOT, naming the right alternative; checkable pass criteria. Add a "Last dated run record:" line once evals or a smoke test exist]
```
