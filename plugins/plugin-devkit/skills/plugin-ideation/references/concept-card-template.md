# Concept Card Templates

Two templates — pick the one matching Step 1's scope answer. Both are written to `.claude/output/plugin-ideation/<slug>-<timestamp>.md`.

**R18 exception (recorded):** both templates below are complete, coherent document skeletons meant to be copied and filled as a whole; splitting either into multiple blocks would break the template it's illustrating.

## Whole-Plugin Concept Card

```markdown
# Plugin Concept: <name-candidate-1>

**Generated:** <UTC timestamp>
**Scope:** Whole new plugin

## Problem
<what problem this solves, in 2-3 sentences>

## Audience
<who uses it, in what situation>

## Overlap Check
**Classification:** None | Partial | Full
<if Partial: name the adjacent component and the boundary this plugin must respect>

## Name Candidates
1. `<name-candidate-1>` — <one-line rationale>
2. `<name-candidate-2>` — <one-line rationale>
3. `<name-candidate-3>` — <one-line rationale>

## Complexity Estimate
**Tier:** Small | Medium | Large
**Reasoning:** <why this tier>

## Next Step
Run `plugin-planning` against this Concept Card to produce a component inventory.
```

## Component Concept Card

```markdown
# Component Concept: <name-candidate-1>

**Generated:** <UTC timestamp>
**Scope:** New component in `<target-plugin-name>`
**Component type:** Skill | Agent | Command | Hook

## Problem
<what gap in the target plugin this fills>

## Audience
<who invokes it, in what situation>

## Overlap Check
**Classification:** None | Partial | Full
<if Partial: name the adjacent component and the boundary this component must respect —
this becomes the basis for a "When NOT to Use" exclusion during Design>

## Name Candidates
1. `<name-candidate-1>` — <one-line rationale>
2. `<name-candidate-2>` — <one-line rationale>
3. `<name-candidate-3>` — <one-line rationale>

## Complexity Estimate
**Tier:** Small | Medium | Large
**Reasoning:** <why this tier>

## Next Step
Run `plugin-planning` against this Concept Card, or go directly to the matching Design
skill (`skill-development`/`agent-development`/`command-development`/`hook-development`/
`rule-development`) if the component is simple enough to skip a separate planning pass.
```
