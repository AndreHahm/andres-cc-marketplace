I can't read the exact fill level myself. For a measured answer, run `/context` and paste its output here; it gives the real token count, window size, percentage and breakdown, and I'll read your status from that. Until then, here is an estimate.

```text
Context Window Analysis
=======================

Estimated Status: HEALTHY (estimate, not a measurement)

Observable Indicators:
  Conversation turns: 1
  Recent file reads: 2 files (small)
  Tool invocations: 2 before this report
  Skills loaded: 1 (context-window-analysis)
```

```text
Assessment:
  Short session with little tool output. No truncation warnings,
  auto-compact messages or memory gaps seen. I can't measure my own
  response speed. The project instructions and tool/skill listings
  loaded at the start are sizable; only /context shows their real cost.

Recommendations:
  No action needed.
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

With your `/context` percentage, the status is: below 40% HEALTHY, 40 to below 80% MONITOR, 80 to below 90% WARNING, 90% and above CRITICAL.

---

## Steps followed

1. Step 1: asked for `/context` output. None was shared, so used the fallback factors.
2. Step 2: only Healthy indicators in a short session, so HEALTHY, labeled an estimate and reported right away. An estimate below CRITICAL never says to compact or clear now, so the recommendation is "no action needed".
3. Step 3: read `references/context-window-examples.md` and used its report template.
