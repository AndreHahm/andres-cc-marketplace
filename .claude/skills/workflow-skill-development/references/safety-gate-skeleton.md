# Safety Gate Pattern Skeleton

Structural skeleton for the Safety Gate Pattern (see [workflow-patterns.md](workflow-patterns.md) for when to use it).

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — the file's own stated purpose is this exact skeleton; trimming would remove the two gates and the individual-execution phase the pattern exists to illustrate.

```markdown
## Core Principle: SAFETY FIRST

**Never [perform action] without explicit user confirmation.**

## Workflow

### Phase 1: Comprehensive Analysis
Gather ALL information upfront before any action.
[Data gathering commands]

### Phase 2: Categorize
[Decision tree for categorizing items]
| Category | Meaning | Action |
|----------|---------|--------|
| SAFE | Verified safe | Standard action |
| RISKY | Needs review | User decides |
| KEEP | Active/needed | No action |

### GATE 1: Present Complete Analysis
Present everything in ONE comprehensive view.
[Formatted summary with categories]
Use AskUserQuestion with clear options.
**Do not proceed until user responds.**

### GATE 2: Final Confirmation with Exact Commands
Show the EXACT commands that will run.
Use `AskUserQuestion` — question: "Run these exact commands?", options: "Confirm" / "Cancel".

### Phase 3: Execute
Run each action as a **separate command**.
Report result of each. Continue on individual failure.

### Phase 4: Report
[Summary of what was done and what remains]
```
