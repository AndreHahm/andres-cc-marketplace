# Response to the user

```text
Context Window Analysis
=======================

Estimated Status: MONITOR  (estimate from observable signals, not a measurement)

Observable Indicators:
  Conversation turns: ~60
  Recent file reads: many (exact count not tracked)
  Tool invocations: many (exact count not tracked)
  Skills loaded: context-window-analysis
```

```text
Assessment:
  This is an estimate. I don't have your /context output, so I can't give you a
  measured percentage.

  What I can see:
  - Warning indicator (1): responses are slower than usual.
  - Healthy indicators: no truncation warnings, no auto-compact message, and
    early decisions are still recalled correctly.
  - Context: a long session (about 60 turns with many file reads), so the
    window has clearly grown a lot.

  One Warning indicator in a long session maps to MONITOR, not WARNING. Two or
  more Warning indicators, or an auto-compact message, would be needed for
  WARNING. Nothing points to CRITICAL: there's no truncation, no failed
  operations and no context rot.

  Slowness on its own is a weak signal. A large context does make each turn
  slower to process, but slow responses can also have nothing to do with
  context (for example, server load). Your recall is still accurate, so the
  window isn't degrading in a way that hurts the work yet.

Recommendations:
  1. Keep going. You don't need to /compact or /clear right now.
  2. Plan a /compact at the next natural break (after the current subtask
     finishes or before you start a new one), so it doesn't land mid-task.
  3. For an exact reading, run /context and paste the output here. The
     measured percentage then sets the status:
       < 40%    HEALTHY   - no action needed
       40-<80%  MONITOR   - awareness nudge at 65%; plan a /compact soon
       80-<90%  WARNING   - run /compact or /clear
       >= 90%   CRITICAL  - act immediately
  4. If you're about to switch to an unrelated task, /clear is the cleaner
     choice than /compact.
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

Signs to watch for: if you start seeing an auto-compact message, missed
earlier decisions ("I don't recall"), or truncation warnings, run `/context`
and act on the measured number.

---

# Steps followed (note)

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` in the worktree, then
   `references/context-window-examples.md` as Step 3 instructs.
2. Scope check: a bare slowness complaint with no plugin/skill/CLAUDE.md mention belongs to this
   skill, not `context-audit`. There were no degradation symptoms (recall is intact), so it wasn't
   routed to `context-degradation` either.
3. Step 1: `/context` output was not shared. The skill says to ask for it, but not to hold the
   report back while waiting. I asked for it (Recommendation 3: "run /context and paste the
   output here") and used the fallback estimation factors (turns, file reads, tool output).
4. Step 2, estimate path: one Warning indicator (slower responses) plus Healthy indicators (no
   truncation, no auto-compact, accurate recall) in a long session gives MONITOR. I labelled it an
   estimate and followed the estimate rule for MONITOR: "keep going and plan a `/compact` at a
   natural break". I did not tell the user to compact or clear now.
5. Step 3: formatted the report with the reference's template (status/indicators,
   assessment/recommendations, commands/tips). Counts I couldn't know (exact file reads, tool
   calls) are marked as not tracked instead of being made up.
6. Plan-only run: nothing was executed. The only interaction with the user is the request to run
   `/context` and paste the output. When the user replies with it, I'd map the measured percentage
   onto the thresholds table and replace this estimate with a measured status.
