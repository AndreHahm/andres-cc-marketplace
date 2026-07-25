# Task File Template

Template for `tasks/step-N-<workflow>-<name>.md` files created during Step 3 of the Implementation Process.

**R18 exception (recorded):** the template below intentionally exceeds the rulebook's 30-line code-block threshold — it's a complete, coherent task-file template; splitting it would break it.

```markdown
# Step N: <Step Name>

## Context
You are executing step N of the <workflow-name> workflow.

## Goal
<Clear, specific goal for this step>

## Input
<What this step receives from previous steps or user>

## Instructions
1. <Specific action>
2. <Specific action>

## Constraints
- <What NOT to do>

## Expected Output
<What to return to orchestrator>

## Success Criteria
- [ ] <Measurable outcome>
```

All task files go directly in `tasks/` — no subdirectories.
