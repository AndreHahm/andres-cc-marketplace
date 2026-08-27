# Plan JSON Companion Schema

Written alongside the Markdown plan at the same base path with a `.json` extension
(`.claude/output/plugin-planning/<slug>-<timestamp>.json`) — the machine-readable contract other tooling
(e.g. `plugin-inventory`) reads directly, instead of parsing the Markdown plan's prose. The Markdown
stays the user-facing artifact; this JSON is the machine contract.

**R18 exception (recorded):** the JSON block below is a complete, coherent schema example whose value
depends on showing the whole shape — including the two-entry `planned_components` array and its
`functional_groups` cross-link — at once; splitting it would break the worked example it's illustrating.

```json
{
  "schema_version": "1.0.0",
  "plan_id": "<slug>-<timestamp>",
  "generated_at": "2026-08-25T14:30:00Z",
  "concept_source": {"type": "concept_card", "path": ".claude/output/plugin-ideation/<slug>-<timestamp>.md"},
  "ideation_skipped": false,
  "planned_components": [
    {
      "name_candidate": "plugin-inventory",
      "type": "skill",
      "purpose": "One-line purpose from Step 2's list.",
      "trigger_phrases": ["build the plugin inventory", "update this plugin's component database"],
      "depth_tier": "rich",
      "functional_group": "Inventory Maintenance"
    },
    {
      "name_candidate": "marketplace-inventory",
      "type": "skill",
      "purpose": "Another one-line purpose from Step 2's list.",
      "trigger_phrases": ["build the marketplace inventory"],
      "depth_tier": "rich",
      "functional_group": "Inventory Maintenance"
    }
  ],
  "functional_groups": [
    {"name": "Inventory Maintenance", "component_names": ["plugin-inventory", "marketplace-inventory"]}
  ]
}
```

`generated_at` uses standard ISO-8601 with colons (`2026-08-25T14:30:00Z`), not the hyphenated,
file-safe timestamp form (`2026-08-25T14-30-00Z`) used in filenames and in `plan_id` — both are derived
from the same `date -u` instant Step 5 generates, just formatted differently for their respective uses.

## Field Rules

- **`type` is restricted to exactly the five types Step 2's decision matrix actually chooses among:
  `"skill"`, `"agent"`, `"command"`, `"hook"`, `"rule"`.** This JSON's `type` enum reflects only what
  this skill can actually produce today. Extending Step 2's decision matrix to propose other component
  types (`mcp-server`/`theme`/etc.) is a separate, later change to this skill, not something this
  schema pre-declares. A planned Rule has no `depth_tier` (only skills get one, per the `depth_tier`
  rule below) and no `functional_group` requirement beyond the same clustering every other component
  type gets.
- **`depth_tier`** (`"minimal"` / `"standard"` / `"rich"`, always lowercase in this JSON — the Markdown
  plan's own Content Depth Allocation table uses the capitalized `Minimal`/`Standard`/`Rich` form per
  Step 3; the two are the same value in different casings, not a mismatch) is included for completeness
  but is **not** consumed by `plugin-inventory` — it's Design-phase guidance, not an inventory field.
  Included only so the JSON is a complete, useful record of the plan on its own. Agents, commands, and
  hooks omit this field (only skills get a depth tier, per Step 3).
- **`concept_source` is `object | null`**, and is `null` exactly when `ideation_skipped` is `true` and
  no Conception Brief was read either (a bare direct-description input) — a populated object otherwise,
  one of two shapes: `{"type": "concept_card", "path": "..."}` (read via `plugin-ideation`'s normal
  Create pipeline — `ideation_skipped` is `false`) or `{"type": "conception_brief", "path": "...",
  "classification": "Enhance" | "Consolidate" | "Reposition"}` (read directly from `plugin-conception`,
  bypassing `plugin-ideation` entirely — `ideation_skipped` is **also `false`** here, since real
  grounding did occur, just not via the interview; `ideation_skipped: true` means no grounding
  artifact was read at all, not "ideation specifically wasn't the source"). The `classification` field
  on the `conception_brief` variant only exists because this concept was never validated as Create at
  `plugin-lifecycle-upstream`'s own Gate 1 — `plugin-lifecycle-upstream`'s Auto-Detection Logic reads it
  before silently resuming a build from this plan (see that skill's own Auto-Detection Logic table).
- **No `id` field is minted here.** Stable-ID assignment for an eventual inventory record is
  `plugin-inventory`'s own responsibility at bootstrap/import time — this schema doesn't invent one
  ahead of time for a component that doesn't exist yet.
- **`plan_id`** is the same `<slug>-<timestamp>` used in both sibling filenames — it's how a consumer
  correlates the JSON back to its Markdown counterpart without relying on matching paths alone.

## Consumption Contract

This JSON is a **candidate list, not a pre-approved one**. Writing it is this skill's own Step 5, which
has no user-approval gate of its own for the plan's *contents* — its only `AskUserQuestion` is the
Suggested Next Step offer (what to do next), not ratification of what's in the plan. Approval for
importing a planned component into an inventory happens entirely inside the consuming tool's own
plan/apply gate (e.g. `plugin-inventory`'s Build workflow proposes `add` operations from this JSON, and
those proposals go through the exact same human sign-off as any other reconciliation operation) — this
schema does not need, and must not invent, a separate approval field or approval record of its own.
On import, the consuming inventory tool renames this JSON's `name_candidate` to its own `name` field
(a planned component has no confirmed final name yet, hence the distinct field name here) — this schema
does not mint a `name` field itself.

A mismatch between this JSON and its sibling Markdown (e.g. a hand-edited Markdown plan with no
corresponding re-run) is out of scope for this skill to detect or reconcile — a consumer that cares about
staleness compares this file's `generated_at` against its own evidence of the Markdown's last
modification.
