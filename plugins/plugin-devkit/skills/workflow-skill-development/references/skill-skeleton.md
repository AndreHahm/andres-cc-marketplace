# SKILL.md Skeleton

Standard skeleton for every workflow-based skill, regardless of pattern.

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — the file's own stated purpose is this exact "standard skeleton for every workflow-based skill"; trimming would contradict that.

```markdown
---
name: kebab-case-name
description: "Third-person description with trigger keywords — this is how Claude decides to activate the skill"
allowed-tools: Tool1 Tool2 Tool3
# Optional fields: see tool-assignment-guide.md for the full reference
---

# Title

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
```
