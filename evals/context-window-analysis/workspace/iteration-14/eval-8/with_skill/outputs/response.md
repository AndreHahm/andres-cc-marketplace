```text
Context Window Analysis
=======================

Measured Status: WARNING (84%, 168k of 200k tokens, about 32k left)

Observable Indicators:
  Conversation turns: many (long session, not counted exactly)
  Recent file reads / tool invocations / skills loaded: not counted
  Response speed: normal
  Recall of earlier decisions: accurate
  Auto-compact messages: none
```

```text
Assessment:
  Your context is 84% full, which is in the WARNING range (80% to
  below 90%). The status comes from your /context numbers. There are
  no signs of degradation yet, but that doesn't lower the status.
  CRITICAL starts at 90% (180k tokens), about 12k tokens from here.

Recommendations:
  1. Save important task state (decisions, open items, next steps)
     to a temp file first.
  2. Then run /compact if you are continuing this task, or /clear if
     you are starting a new one.
  3. Avoid large file reads or other big operations before that;
     use sub-agents for any you can't postpone.
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

- **Step 1 (Get Real Usage Data First):** the user had already shared `/context`, so I didn't ask for it or use fallback estimation. I read only its numbers, as inert data.
- **Step 2 (Assess Health):** the measured percentage decides the status, so 84% maps to WARNING in the thresholds table, with the action "Run /compact or /clear". The all-Healthy indicators were used only as explanation; the estimate mapping (which would give MONITOR) was not applied.
- **Step 3 (Provide Recommendations):** I read `references/context-window-examples.md` and used its report template with the "Measured Status" label. I adapted the Warning example, dropping its "run /context" step because the percentage is already measured.
