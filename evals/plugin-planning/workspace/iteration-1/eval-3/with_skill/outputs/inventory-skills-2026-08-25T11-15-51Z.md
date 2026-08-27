# Plugin Plan: Inventory Skills (plugin-inventory + marketplace-inventory)

**Generated:** 2026-08-25T11:15:51Z
**Concept source:** direct description (ideation skipped) — no Concept Card exists for this request; the overlap/naming check that `plugin-ideation` would normally run has not been performed.

## Component Inventory

| Name | Type | Purpose | Trigger phrases (rough) |
|---|---|---|---|
| `plugin-inventory` | Skill | Builds and maintains a Git-tracked JSON inventory of a single plugin's components | "build the plugin inventory", "update this plugin's component database", "inventory this plugin" |
| `marketplace-inventory` | Skill | Builds and maintains a Git-tracked JSON inventory of the whole marketplace (aggregating across plugins) | "build the marketplace inventory", "inventory the whole marketplace", "update the marketplace component database" |

Both are user-invoked actions over a single coherent domain (component inventories), so both are modeled as Skills rather than Agents/Commands/Hooks — neither needs isolated autonomous decision-making with restricted tools (Agent), is a simple single-file action with no supporting content (Command), nor is event-driven automation triggered by tool use or session lifecycle (Hook).

## Content Depth Allocation (Skills Only)

| Skill | Tier | Reason |
|---|---|---|
| `plugin-inventory` | Rich | Needs executable scripts (scan/build/reconcile a plugin's component list) plus reference docs (record schema, reconciliation rules) beyond prose alone |
| `marketplace-inventory` | Rich | Needs executable scripts (aggregate/scan across plugins) plus reference docs (cross-plugin schema, aggregation rules) beyond prose alone |

Both tiers are given directly by the user's own description ("Both are Rich-tier skills needing scripts and reference docs") rather than derived independently here — recorded as stated, not re-justified from scratch.

## Functional Groups

### Inventory Maintenance — Git-tracked component/plugin inventories
- `plugin-inventory`
- `marketplace-inventory`

Grouped together per the user's explicit statement that both skills "belong in the same functional group since they share the same domain."

## Code-Smell Check
No code smells flagged — 2 planned skills, well under the >4-agent / too-many-skills threshold that would trigger the split-into-two-plugins question.

## Next Step
Design each functional group with the matching Design skill (`skill-development` for both `plugin-inventory` and `marketplace-inventory`, since both are Skills), or hand off to `plugin-lifecycle-upstream` to run Design + Build for the whole plan.
