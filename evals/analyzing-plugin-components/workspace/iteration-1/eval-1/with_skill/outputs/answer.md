# Phase 2 → Phase 3 Transition: Next Action

## Context

Following the `analyzing-plugin-components` skill's Phase 2 (Component Inventory) procedure, after emitting the Session Inventory table that found 5 components (2 skills, 1 sub-agent, 1 command, 1 rule).

## Next Action

**Tool Call: AskUserQuestion**

After completing the Phase 2 component inventory and emitting the inventory table, the exact next action is to invoke `AskUserQuestion` to confirm before proceeding to Phase 3.

### Specification

- **Tool:** `AskUserQuestion`
- **Message:** "Found 5 components. Proceed with full analysis?"
- **Options:**
  - "Proceed"
  - "Cancel"

### Reference

From SKILL.md Phase 2, lines 119-120:

> Confirm before proceeding — ask with `AskUserQuestion`: "Found N components. Proceed with full analysis?" — options "Proceed" / "Cancel".

## Why This Step

This is the explicit gate between Phase 2 (Component Inventory) and Phase 3 (SWOT Analysis) per the skill's documented procedure. The confirmation checkpoint ensures the user approves the component list before the skill proceeds into the full analysis phases (SWOT, Self-Critique, Self-Reflection, Suggestions, Grouped Report).

## What Does NOT Happen Yet

- No Phase 3 SWOT analysis is started
- No output artifacts are read or verified at this point
- No handoff-report validation occurs
- No narrative text for later phases is emitted
- No commit SHA resolution occurs

All of these steps occur **after** the confirmation question is answered affirmatively. The confirmation itself is purely a binary checkpoint: proceed or cancel.
