# Which Step 1 branch applies, and what happens next

## The scenario

`plugin-planning` is invoked with `$ARGUMENTS` = `"plan out a caching layer for skill X"` — a bare
description that doesn't resolve to a file under `.claude/output/plugin-ideation/` (a Concept Card) or
`.claude/output/plugin-conception/` (a Conception Brief).

## Step 1 branch: "Neither found"

This is the third of three branches in Step 1 ("Load the Concept"), and it's the one that applies here.
Quoting the skill's own text (`SKILL.md` lines 58-60):

> **Neither found** → treat `$ARGUMENTS` as the problem statement directly (both `plugin-conception` and
> `plugin-ideation` were skipped); note in the plan that ideation was skipped, so a reader knows the
> overlap check wasn't run.

The other two Step 1 branches don't apply:
- **Concept Card found** under `.claude/output/plugin-ideation/` — not this case, no such path resolved.
- **Conception Brief found** under `.claude/output/plugin-conception/` — not this case either.

So `$ARGUMENTS` itself ("plan out a caching layer for skill X") becomes the problem statement the rest of
the skill works from — there's no upstream Concept Card or Conception Brief to `Read` first.

## What happens next (Steps 2-5)

1. **Step 2 — Decide Component Types and Counts.** For each distinct capability the caching-layer concept
   implies, the skill classifies it against the decision matrix (Skill / Agent / Command / Hook) and lists
   name candidates, type, one-line purpose, and rough trigger phrases. Since this is a component *for* an
   existing skill ("skill X"), not a new plugin, the practical scope here is likely small — possibly a
   single new skill, or new `references/`/`scripts/` content added to skill X itself, depending on what the
   caching layer actually needs to do. The **code-smell check** still applies: if the plan grows past 4
   agents or more skills than fit a one-paragraph summary each, the skill must stop and ask via
   `AskUserQuestion` whether to split into two plugins.

2. **Step 3 — Allocate Content Depth (Skills Only).** Any planned skill gets a Minimal/Standard/Rich tier
   per the existing 80% Rule vocabulary (from `skill-development/references/skill-workflow.md` and
   `skill-categories.md`) — not a new rubric. This is an estimate, not binding; the real Design phase makes
   the final call.

3. **Step 4 — Map to Functional Groups.** Planned components are clustered into small (2-5 component)
   domain-named groups to keep later Design work coherent.

4. **Step 5 — Write the Plan.** A timestamp is generated (`date -u +%Y-%m-%dT%H-%M-%SZ`), and the plan is
   written to `.claude/output/plugin-planning/<slug>-<timestamp>.md` following
   `references/plan-template.md`. Critically, per the Step 1 instruction above, the template's
   **Concept source** field is filled with `"direct description (ideation skipped)"` — the template
   explicitly has this exact value as one of its three documented options (`plan-template.md` line 11):
   `<path to Concept Card, path to Conception Brief ("direct from plugin-conception, ideation skipped"), or "direct description (ideation skipped)">`.
   This is also called out directly in the skill's own Testing & Validation checklist (item 2): "confirm
   the written plan notes ideation was skipped." The written path is then confirmed back to the user.

5. **Suggested Next Step.** The skill asks via `AskUserQuestion` whether to proceed to Design for the first
   functional group directly, hand off to `plugin-lifecycle-upstream` for Design + Build across the whole
   plan, or stop here — never auto-invoking the orchestrator without asking first.

## Summary

For a bare description with no resolvable Concept Card or Conception Brief, Step 1's **"Neither found"**
branch fires: `$ARGUMENTS` is treated as the problem statement directly, and both `plugin-conception` and
`plugin-ideation` are recorded as skipped (meaning no overlap/duplication check against existing plugins
was ever run for this concept). The skill then proceeds normally through Steps 2-5 — component
type/count decisions with the >4-agent code-smell gate, depth-tier allocation for any planned skills,
functional grouping, and writing the plan to `.claude/output/plugin-planning/<slug>-<timestamp>.md` with
its Concept Source field explicitly reading `"direct description (ideation skipped)"` — before offering
the same `AskUserQuestion`-gated handoff to Design or `plugin-lifecycle-upstream`.

## Files referenced

- `C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-conception\plugins\plugin-devkit\skills\plugin-planning\SKILL.md` (Step 1, lines 45-60; Testing & Validation item 2, line 106)
- `C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-conception\plugins\plugin-devkit\skills\plugin-planning\references\plan-template.md` (Concept source field, line 11)
