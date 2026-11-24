I can't see the exact fill level from here, so this is an estimate, not a measurement.

```text
Context Window Analysis
=======================

Estimated Status: WARNING (estimate, no /context output yet)

Observable Indicators:
  Conversation turns: about 90
  Recent file reads: not known
  Tool invocations: not known
  Skills loaded: not known
  Auto-compact messages: 3 (Warning indicator)
  Response speed: normal (healthy)
  Recall of earlier decisions: accurate (healthy)
  Truncation or context-limit failures: none (no Critical indicator)
```

```text
Assessment:
  The auto-compact messages alone put the estimate at WARNING. Seeing
  three of them does not make it CRITICAL: nothing is truncated, recall
  is intact and no operation has failed on the context limit. I can't
  give a percentage without /context.

Recommendations:
  1. Run /context and paste the output here. Its percentage decides the
     status.
  2. Compact only if the measured percentage is 80% or more (or /clear
     if you are switching to a new task).
  3. Save important decisions to a file first if you do.
```

```text
Warning Signs to Watch:
  - Slower responses or gaps in recalling earlier decisions
  - Truncated conversation, or operations failing on the context limit:
    these would make it CRITICAL
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

Could you run `/context` and share the output? I'll replace the estimate with the measured status.

---

## Steps followed

- Step 1: No `/context` output was shared, so I asked for it and gave the estimate right away.
- Step 2: The auto-compact messages map to WARNING; there is no Critical indicator. An estimate below CRITICAL doesn't say to compact or clear now, so the advice is `/context` first, then compact only at 80% or more.
- Step 3: Read `references/context-window-examples.md` and used its report template and Warning example. Counts not given were left as unknown.
