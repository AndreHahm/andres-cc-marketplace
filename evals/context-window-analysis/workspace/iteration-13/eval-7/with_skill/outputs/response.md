```text
Context Window Analysis
=======================

Estimated Status: WARNING (an estimate, not a measurement)

Observable Indicators:
  Conversation turns: about 90
  Auto-compact messages: 3
  Recent file reads: not counted
  Tool invocations: not counted
  Skills loaded: not counted
  Response speed: normal
  Recall of earlier decisions: accurate
  Truncation / context-limit failures: none
```

```text
Assessment:
  I can't give you an exact percentage without /context output.
  The repeated auto-compact messages put the estimate at WARNING.
  There is no critical sign: nothing is truncated, recall is intact
  and no operation has failed on the context limit.

Recommendations:
  1. Run /context and share the output. Its percentage replaces
     this estimate.
  2. Compact only if the measured percentage is 80% or more
     (or use /clear if you are starting a new task). At 90% or more,
     act immediately.
  3. If you do compact or clear, save important context to a file first.
```

```text
Warning Signs to Watch:
  - If responses slow down or recall gets worse, run /context again
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

- Step 1 (Get Real Usage Data First): asked for `/context`; used the indirect fallback because none was shared.
- Step 2 (Assess Health): no Critical indicator; an auto-compact message maps to WARNING. Labelled it an estimate, reported right away, and gave the WARNING advice (run `/context`, compact only at 80% or more) rather than saying to compact now.
- Step 3 (Provide Recommendations): read `references/context-window-examples.md` and used its template and WARNING example. The situation gave no file-read, tool or skill counts, so I marked them not counted.
