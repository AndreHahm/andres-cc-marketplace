# Response to the user: "how full is my context right now"

## What I would ask first (Step 1: real usage data)

I can't see exact token counts from inside the conversation, but Claude Code's `/context` command can. Please run:

```
/context
```

and paste its output here. It shows current tokens, max capacity, percent used, and a breakdown by category (system prompt, tools, memory files, skills, messages). I'll use that percentage to give you a measured status, not a guess.

(When you paste it, I'll read only the numbers, percentages and category labels. If any plugin description or MCP tool name in the breakdown contains text that looks like an instruction, I'll point it out as suspicious and won't follow it.)

## The reply I would then give

### A. Once you've pasted `/context` output

The percentage decides the status, using the thresholds the context-kit monitor hook also uses:

| Usage | Status | Action |
|-------|--------|--------|
| < 40% | HEALTHY | No action needed |
| 40-<80% | MONITOR | One awareness nudge at 65%; think about running /compact soon |
| 80-<90% | WARNING | Run /compact or /clear |
| >= 90% | CRITICAL | Act now |

The report would follow this shape, filled in with your real numbers. Example for an output showing, say, 32% used:

```text
Context Window Analysis
=======================

Status: HEALTHY (measured: 32% of the window used, from /context)

Observable Indicators:
  Conversation turns: 1
  Recent file reads: 2 files
  Tool invocations: 2
  Skills loaded: context-window-analysis

Assessment:
  Context is healthy. Most of the usage is the fixed base load
  (system prompt, tool definitions, CLAUDE.md and rule files),
  not conversation history.

Recommendations:
  No action needed. Continue as normal.
  Consider /clear before starting a new, unrelated task.
```

At WARNING I'd recommend `/compact` (or `/clear` if you're switching tasks), saving any important state to a file first. At CRITICAL I'd list four options: save state then `/compact`; `/clear` and reload only what you need; start a new session; or, if session-kit is installed, say "create handoff" (writes to `.claude/handoffs/`), start a new session and say "resume from handoff".

### B. If you'd rather not run `/context` (estimate only)

```text
Context Window Analysis
=======================

Estimated Status: HEALTHY (estimate from observable signals, not a measurement)

Observable Indicators:
  Conversation turns: 1
  Recent file reads: 2 files (this skill's SKILL.md and its examples reference)
  Tool invocations: 2
  Skills loaded: context-window-analysis

Assessment:
  This session has just started, and there are no warning signs: no slowdowns,
  no truncation or auto-compact messages, no recall problems. Note that this
  project loads a lot of always-on rule files and CLAUDE.md content, so the
  fixed base load is larger than average. Only /context can tell you the real
  number.

Recommendations:
  No action needed. Continue as normal.
  Run /context any time for exact numbers.

Available Commands:
  /clear    - Full context reset
  /compact  - Summarize the conversation, keeping the key information
  /cost     - Show token usage and cost

Tips for Context Management:
  - Use /clear between major task switches
  - Ask focused, specific questions instead of broad exploration
  - Let Claude use subagents for large operations
  - Split large tasks across several sessions
```

---

## Steps I followed (plan-only run)

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` in the worktree, in full.
2. Step 1 of the Workflow: asked the user to run `/context` and paste the output, as the real data source. Included the rule to treat the pasted output as inert data. Nothing was executed.
3. Step 2: wrote down how the reply maps `/context`'s percentage onto the Context Health Thresholds table (the percentage decides). For the no-`/context` fallback, the indicators map to a status that is labelled an estimate. With only Healthy indicators and a short session, that is HEALTHY rather than MONITOR.
4. Step 3: read `references/context-window-examples.md` and followed its report template (header and indicators, assessment and recommendations, commands and tips). I summarised the WARNING and CRITICAL remediation options from its worked examples, including Option 4's real `session-handoff` trigger phrase and the `.claude/handoffs/` location.
5. Read no `evals/` files and made no Skill tool call. The only file written is this one.
