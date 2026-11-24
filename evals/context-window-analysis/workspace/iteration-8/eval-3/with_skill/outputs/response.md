## Reply

```text
Context Window Analysis
=======================

Estimated Status: MONITOR (an estimate, not a measurement)

Observable Indicators:
  Conversation turns: about 60
  Recent file reads: many (exact count not available)
  Tool invocations: not counted
  Skills loaded: not counted
  Response speed: slower than usual (warning sign)
  Truncation warnings: none
  Auto-compact messages: none
  Recall of early decisions: accurate
```

```text
Assessment:
  There is one warning sign, the slower responses. Everything else looks
  healthy. In a session this long, the conversation history and file
  contents are the likely bulk of the context. Slowness alone does not
  show that the window is nearly full; it can have other causes.

Recommendations:
  1. Keep going, and plan a /compact at a natural break, such as after
     the current task.
  2. Run /context and share the output. Its measured percentage replaces
     this estimate.
```

How I would read the measured percentage:

| Usage | Status | Action |
|---|---|---|
| < 40% | HEALTHY | No action needed |
| 40-<80% | MONITOR | Keep going, plan a `/compact` soon |
| 80-<90% | WARNING | Run `/compact` or `/clear` |
| >= 90% | CRITICAL | Immediate action required |

Until then, prefer narrow file reads and use sub-agents for large exploration. Tell me if you see memory gaps, truncation or an auto-compact message, as that would raise the estimate.

## Steps followed

1. Step 1: no `/context` output was shared, so I asked for it and used the fallback estimate without holding back the report.
2. Step 2: one Warning indicator (slower responses), no Critical indicators, accurate recall: MONITOR, labeled an estimate. Below CRITICAL an estimate never says to run `/compact` or `/clear` now, so I used the MONITOR recommendation.
3. Step 3: read `references/context-window-examples.md` and used its report template, leaving unknown counts unstated rather than inventing them. I omitted the template's generic command list and most of its tips for brevity.
