```text
Context Window Analysis
=======================

Estimated Status: WARNING (an estimate, not a measurement)

Observable Indicators:
  Conversation turns: many (long session; not counted)
  Recent file reads: not counted
  Tool invocations: not counted
  Skills loaded: not counted
  Warning signs: slower responses; occasional memory gaps
                 (an earlier decision forgotten twice)
  Not seen: auto-compact messages, truncation warnings
```

```text
Assessment:
  Two Warning indicators together give a WARNING estimate.
  I see no Critical indicator. I can't give you a percentage
  without your /context output.

Recommendations:
  1. Run /context and share the output. Its measured percentage
     replaces this estimate.
  2. Compact only if the measured percentage is 80% or more
     (/compact, or /clear if you are starting a new task).
     Below 80%, don't compact because of this estimate.
  3. Before compacting or clearing, save the important decisions
     to a temp file, including the one that was forgotten.
```

```text
Warning Signs to Watch:
  - If responses slow further or recall gets worse, run /context again
  - If the conversation is truncated or operations fail on the
    context limit, act immediately
```

```text
Available Commands:
  /clear    - Complete context reset (nuclear option)
  /compact  - Intelligent summarization (preserves key info)
  /cost     - View token usage and costs

Tips for Context Management:
  - Use /clear between major task switches
  - Prefer focused, specific queries over broad exploration
  - Let Claude use sub-agents for large operations
  - Break large tasks into smaller sessions
```

## Steps followed

- **Step 1 (Get Real Usage Data First):** asked for `/context`. No output had been shared, so I used the indirect-estimate fallback.
- **Step 2 (Assess Health):** slower responses (one Warning indicator) plus occasional memory gaps (a second) meet "Two or more Warning indicators", so WARNING. No Critical indicator applied. I labeled it an estimate, reported right away, and gave the WARNING advice: run `/context`, compact only at 80% or more.
- **Step 3 (Provide Recommendations):** read `references/context-window-examples.md` and used its report template and Warning example. I left unknown counts as "not counted" instead of inventing them.
