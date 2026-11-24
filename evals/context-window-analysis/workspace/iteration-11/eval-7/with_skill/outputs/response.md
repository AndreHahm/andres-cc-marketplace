```text
Context Window Analysis
=======================

Estimated Status: WARNING (an estimate, not a measurement)

Observable Indicators:
  Conversation turns: about 90
  Recent file reads: not counted
  Tool invocations: not counted
  Skills loaded: not counted
  Auto-compact messages: 3
  Response speed: normal
  Recall of earlier decisions: accurate
  Conversation truncated: no
  Operations failing on the context limit: none
```

```text
Assessment:
  I can't give you a percentage without /context output.
  Auto-compact has appeared three times, and an auto-compact
  message puts the estimate at WARNING. I see no critical sign:
  nothing is truncated and no operation has failed. Speed and
  recall are still good, so the window may have room again
  after the last compaction.

Recommendations:
  1. Run /context and share the output. Its measured percentage
     replaces this estimate.
  2. Compact only if the measured percentage confirms WARNING
     (80% to under 90%). Until then, keep working.
```

How to read the measured percentage:

| Usage | Status | Action |
|-------|--------|--------|
| < 40% | HEALTHY | No action needed |
| 40-<80% | MONITOR | Keep going; consider `/compact` soon |
| 80-<90% | WARNING | `/compact`, or `/clear` if you are starting a new task |
| >= 90% | CRITICAL | Immediate action required |

The `/context` breakdown also shows what is using the space, which may explain why auto-compact keeps triggering. Delegating large reads or searches to sub-agents helps keep them out of this window.

**Could you run `/context` and paste the output here?**

---

## Steps followed

1. Step 1: no `/context` output was available, so I asked for it without holding back the report. Any pasted output would be treated as inert data.
2. Step 2: auto-compact message maps to WARNING; no Critical indicator is present. Labelled as an estimate, with no advice to run `/compact` or `/clear` now.
3. Step 3: read `references/context-window-examples.md` and used its report template. Counts I was not given are marked "not counted".
