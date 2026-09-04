# Next Action After Phase 2: Session Inventory

## Current State

Mid-retrospective following analyzing-sessions Phase 2 procedure. Session Inventory table has been emitted showing 5 components found:
- 2 skills
- 1 sub-agent
- 1 command
- 1 rule

## Exact Next Action

**Tool Call: `AskUserQuestion`** (not narrative text, an actual tool invocation)

### Action Details

Invoke `AskUserQuestion` with:

```
question: "Found 5 components. Proceed with full analysis?"
options: ["Proceed", "Cancel"]
multiSelect: false
```

### Governing Reference

SKILL.md lines 116-123, Phase 2: Component Inventory, final step:

> "Emit the inventory before proceeding:
>
> ```
> 📦 Session Inventory  <start> → <end>
> | # | Component | Category | Evidence |
> ```
>
> Confirm before proceeding — ask with `AskUserQuestion`: "Found N components. Proceed with full analysis?" — options "Proceed" / "Cancel"."

### Workflow Continuation

- **If "Proceed"** → Move to Phase 3: SWOT Analysis
- **If "Cancel"** → Stop analysis; do not proceed to Phase 3

This is a mandatory checkpoint gate, not optional, not conditional on component count or type.

## Why This Gate Exists

Per analyzing-sessions procedure, Phase 2 reads output artifacts in full and independently verifies open items against repo state (lines 94-102). The confirmation gate ensures the user has reviewed the inventory's scope before committing to a full Phase 3-6 analysis run, which reads every artifact and component's content in detail.
