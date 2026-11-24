```text
Context Window Analysis
=======================

Estimated Status: WARNING

Observable Indicators:
  Conversation turns: about 90
  Recent file reads: not counted
  Tool invocations: not counted
  Skills loaded: not counted
  Auto-compact messages: 3 (Warning indicator)
  Response speed: normal
  Recall of earlier decisions: accurate
  Conversation truncated: no
  Operations failing on the context limit: none
```

```text
Assessment:
  I can't give you an exact percentage without /context output, so this
  is an estimate, not a measurement. The auto-compact messages put it at
  WARNING. There is no Critical sign: speed and recall are fine, nothing
  is truncated and no operation has failed.

Recommendations:
  1. Run /context and share the output. Its measured percentage decides
     the real status.
  2. Compact only if the measured percentage is 80% or more (or use
     /clear if you are starting a new task).
  3. Save important context to a temp file first.
```

```text
Warning Signs to Watch:
  - If responses slow or recall gets worse, run /context again
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

- **Step 1 (Get Real Usage Data First):** no `/context` output was shared, so I asked for it and used the fallback factors without holding back the report.
- **Step 2 (Assess Health):** an auto-compact message maps to WARNING, and no Critical indicator is present. I labeled the status an estimate and used the WARNING recommendation: run `/context`, and compact only at a measured 80% or more.
- **Step 3 (Provide Recommendations):** I read `references/context-window-examples.md` and used its report template and Warning State example.
