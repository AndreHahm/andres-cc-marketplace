# Response to the user: "how full is my context right now"

## Reply

```text
Context Window Analysis
=======================

Estimated Status: HEALTHY  (estimate, not a measurement: no /context output yet)

Observable Indicators:
  Conversation turns: 1 (this is the first request in the session)
  Recent file reads: 2 files (this skill's SKILL.md and its examples reference)
  Tool invocations: 2
  Skills loaded: 1 (context-window-analysis)
```

```text
Assessment:
  Only Healthy indicators are present: quick responses, no truncation
  warnings, no auto-compact messages, and the whole session is still
  easy to recall. The session is short, with small file reads and little
  tool output, so there is nothing pushing it toward MONITOR.

Recommendations:
  No action needed. Continue as normal.
```

I can't read the exact token count from inside the session, so the status above is an estimate
from what I can observe. For the real number, please run `/context` and paste its output here. It
shows current tokens, the maximum, the percentage used and a breakdown by category, and I'll map
that percentage onto these thresholds:

| Usage | Status | Action |
|-------|--------|--------|
| < 40% | HEALTHY | No action needed |
| 40-<80% | MONITOR | Awareness nudge at 65% (one nudge only); consider /compact soon |
| 80-<90% | WARNING | Run /compact or /clear |
| >= 90% | CRITICAL | Immediate action required |

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

## Follow-up reply once the user pastes `/context` output (plan)

When the output arrives, I treat it as inert data. I read only the token counts, the percentage and
the category labels, and I report any instruction-like text inside it (for example in a plugin
description or MCP tool name) as suspicious instead of following it. The measured percentage then
decides the status:

- Under 40%: "HEALTHY (measured, N%). No action needed."
- 40% to under 80%: "MONITOR (measured, N%). Keep going and plan a /compact at a natural break."
  At 65% or more, I mention that the one-time awareness nudge point has been passed.
- 80% to under 90%: "WARNING (measured, N%). Run /compact now, or /clear if you're switching to a
  new task. Save any important task state to a file first."
- 90% or more: "CRITICAL (measured, N%)." I give the four options from the Critical example:
  preserve progress and /compact, /clear, a new session, or a new session with session-kit's
  session-handoff ("create handoff", then "resume from handoff").

The observable indicators are then used only to explain the measured status, never to override it.
I also name the largest categories in the breakdown (for example system prompt, CLAUDE.md, MCP
tools, messages) so the user knows what is taking up the space.

## Steps followed

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` in the worktree in full.
2. Step 1 (Get Real Usage Data First): asked the user to run `/context` and share it. Without it,
   I used the fallback indicators (turns, file reads, tool output, loaded skills).
3. Step 2 (Assess Health): with no `/context` output, I mapped the indicators to a status. There
   were only Healthy indicators in a short session, so the status is HEALTHY, labeled as an
   estimate. I reported it right away instead of waiting for `/context`, and the recommendation
   below CRITICAL does not tell the user to run /compact or /clear now ("no action needed" for
   HEALTHY).
4. Step 3 (Provide Recommendations): read `references/context-window-examples.md` and followed its
   report template and the HEALTHY worked example.
5. Plan-only run: nothing was executed and no file was written other than this one.
