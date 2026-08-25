No — that candidate does **not** go into the Fix bundle.

## What Step 4 does with it

`improve-a-plugin.md`'s Step 4 ("Route by Classification, Then Hand Off to Fix") routes each of Step 3's classified candidates into one of three buckets:

1. Repair (bypassed or full-brief), or Enhance/Consolidate/Reposition **with no new components implied** → Fix bundle.
2. Enhance/Consolidate/Reposition **where the brief's classification implies a new or restructured component** → **excluded** from the Fix bundle.
3. Retain/Reject/Defer → excluded, not actionable.

An Enhance classification whose Conception Brief's implementation plan implies building a new sub-component falls squarely into bucket 2, not bucket 1. The skill is explicit that "Enhance" alone isn't sufficient to route into Fix — it's specifically "Enhance/Consolidate/Reposition **with no new components implied**" that lands there. The moment the brief implies a new (or restructured) component, it's carved out regardless of which of those three classifications it carries.

## Why, and what happens instead

`improve-a-plugin` (via `plugin-lifecycle-maintenance`) has no Design/Build capability of its own — it can only hand fixes to `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix), which applies changes to *existing* components, not build new ones. So for this candidate, Step 4:

- Does **not** force it into the Fix bundle.
- Presents the already-written Conception Brief to the user.
- States plainly that this specific candidate needs `plugin-planning` instead — mirroring `plugin-conception`'s own Step 7 hand-off table, which routes exactly this case (new/restructured component) to `plugin-planning`, and explicitly *never* to `plugin-lifecycle-upstream` (that pipeline's Gate 1 stops on any non-Create classification and doesn't resume into it).
- Reuses the brief Step 3 already wrote as `plugin-planning`'s own Step 1 input — described as "not wasted work," since `plugin-planning` already accepts a Conception Brief path directly.
- Excludes the candidate from the Fix bundle that gets handed to `plugin-lifecycle-downstream`.

## Net effect on the workflow

If this was the *only* candidate among the three, and the other two also end up excluded (e.g. Retain/Reject/Defer), the Fix bundle would be empty and Step 4 states this plainly and skips the `plugin-lifecycle-downstream` hand-off entirely (per Step 4's own instruction: "If the Fix bundle is empty ... state this plainly and skip the `plugin-lifecycle-downstream` invocation"). If at least one of the other two candidates does qualify for the Fix bundle, that subset still proceeds to `plugin-lifecycle-downstream`'s Phase 8 hand-off, while this Enhance-with-new-component candidate is separately reported to the user as redirected to `plugin-planning`.

Either way, Step 4's exit criteria require every candidate to get an explicit, disclosed disposition — "bundled-and-applied, redirected to `plugin-planning`, or excluded as Retain/Reject/Defer" — never silently dropped. So this candidate's disposition is: **redirected to `plugin-planning`**, with its Conception Brief handed over as the starting input, not merged into the Fix bundle.

## Source

- `plugins/plugin-devkit/skills/plugin-lifecycle-maintenance/workflows/improve-a-plugin.md`, Step 4 ("Route by Classification, Then Hand Off to Fix") — the routing rule and its rationale.
- `plugins/plugin-devkit/skills/plugin-lifecycle-maintenance/SKILL.md` — corroborating cross-reference: "`plugin-conception` skill ... Step 3 (Conceive) in both `improve-a-plugin`/`enhance-a-plugin` — classifies the human-approved findings and produces a Conception Brief (or takes its own narrow-repair bypass) before the Fix hand-off," and quality gate 12a, which requires this bypass/redirect logic to be confirmed, not skipped.
