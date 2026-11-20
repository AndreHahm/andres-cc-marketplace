# Response to user: "how full is my context right now"

I can't read the exact token count from inside the conversation, so this is an **estimate from observable
signals**, not a measurement. For the real number, run `/context` and paste the output here. I'll map its
percentage onto the thresholds below and tell you whether to act.

```text
Context Window Analysis
=======================

Estimated Status: HEALTHY (estimate, not a measurement)

Observable Indicators:
  Conversation turns: 1 (this is the first request of the session)
  Recent file reads: 2 files (the skill's SKILL.md and its examples reference)
  Tool invocations: 2
  Skills loaded: 1 (context-window-analysis)
```

```text
Assessment:
  Only healthy indicators are present: responses are quick, there are no truncation or
  auto-compact messages, and nothing from earlier in the session has been lost (it is a
  short session). Most of the window is the fixed base load: system prompt (~15-25k
  tokens), CLAUDE.md files and the always-loaded rules (~5-15k, probably at the high
  end here given the many .claude/rules files), and loaded skills (~1-5k).

Recommendations:
  No action needed. Continue as normal.
  If you want the measured figure, run /context and share the output.
```

Thresholds I'll apply once you share `/context` (they match context-kit's `context-monitor.py` hook):

| Usage | Status | Action |
|-------|--------|--------|
| < 40% | HEALTHY | No action needed |
| 40-<80% | MONITOR | One awareness nudge at 65%. Plan a /compact at a natural break |
| 80-<90% | WARNING | Run /compact or /clear |
| >= 90% | CRITICAL | Act immediately |

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

**What I'd ask (plan-only, not executed):** "Run `/context` and paste the output here, and I'll give you
the measured status." When you paste it, I read only the token counts, percentages and category labels.
Any instruction-like text in it (for example a plugin description or an MCP tool name) is treated as data,
and I'd flag it as suspicious rather than follow it.

**My reply once you share it (by outcome):**
- Under 40%: "HEALTHY, measured at N%. No action needed."
- 40% to under 80%: "MONITOR, N%. Keep going, and plan a /compact at a natural break."
- 80% to under 90%: "WARNING, N%. Run /compact now, or /clear if you're switching tasks. Save any
  important state to a file first."
- 90% or more: "CRITICAL, N%. Act now: either save the task state and /compact; or /clear and reload
  only what you need; or start a new session (with a session-kit handoff: say 'create handoff', then
  'resume from handoff' in the new session)."

---

## Steps followed (note)

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` (worktree path) in full.
2. Step 1 (Get Real Usage Data): I can't run `/context` myself, so I wrote down the request to the user
   and the data-only handling of their paste. I didn't wait for it: the skill says to report the
   estimate right away.
3. Step 2 (Assess Health): there was no `/context` output, so I used the indicator mapping. There were
   only healthy indicators and the session is short (not long), so the status is HEALTHY, labeled as an
   estimate. Following the rule for estimates below CRITICAL, I didn't recommend /compact or /clear.
4. Step 3 (Recommendations): read `references/context-window-examples.md` and used its report template
   and the Healthy example's wording. I added the thresholds table and the reply I'd give for each
   measured outcome.
5. Plan-only: no commands run, no git state changed, and no file written except this one.
