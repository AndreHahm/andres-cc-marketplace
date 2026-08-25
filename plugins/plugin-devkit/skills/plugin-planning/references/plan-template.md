# Plugin Plan Template

Written to `.claude/output/plugin-planning/<slug>-<timestamp>.md`.

**R18 exception (recorded):** the template below is a complete, coherent document skeleton meant to be copied and filled as a whole; splitting it would break the template it's illustrating.

```markdown
# Plugin Plan: <name>

**Generated:** <UTC timestamp>
**Concept source:** <path to Concept Card, path to Conception Brief ("direct from plugin-conception, ideation skipped"), or "direct description (ideation skipped)">

## Component Inventory

| Name | Type | Purpose | Trigger phrases (rough) |
|---|---|---|---|
| `<name>` | Skill | <one line> | "<phrase 1>", "<phrase 2>" |
| `<name>` | Agent | <one line> | invoked by `<calling component>` |

## Content Depth Allocation (Skills Only)

| Skill | Tier | Reason |
|---|---|---|
| `<name>` | Minimal / Standard / Rich | <one-clause reason> |

## Functional Groups

### <Group name — domain, not lifecycle stage>
- `<component-1>`
- `<component-2>`

## Code-Smell Check
<state explicitly: "No code smells flagged" OR name the flagged smell and the user's decision (split into two plugins / proceed anyway with reasoning)>

## Next Step
Design each functional group with the matching Design skill (`skill-development`, `agent-development`, `command-development`, `hook-development`, `rule-development`),
or hand off to `plugin-lifecycle-upstream` to run Design + Build for the whole plan.
```
