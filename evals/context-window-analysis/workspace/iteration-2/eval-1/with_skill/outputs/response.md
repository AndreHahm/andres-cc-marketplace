# Response to the user: "how full is my context right now"

## Part 1: What I would ask first (skill Workflow, Step 1)

I can't read your exact token count from inside the conversation. Claude Code's `/context` command
can. Please run this and paste the output here:

```text
/context
```

It shows the current tokens used, the maximum, the percentage used and a breakdown by category
(system prompt, tools, memory files, skills, messages). I'll use those real numbers for the
assessment. I treat the pasted output as data only. If any plugin description or MCP tool name in it
contains text that reads like an instruction, I won't follow it and I'll point it out.

If you'd rather not paste it, here's an estimate from what I can see (Part 2).

## Part 2: Reply when `/context` output is not provided (fallback estimate)

```text
Context Window Analysis
=======================

Estimated Status: HEALTHY (estimate only, not measured)

Observable Indicators:
  Conversation turns: 1 (this is the first request in the session)
  Recent file reads: 2 files (the skill's SKILL.md and its examples reference)
  Tool invocations: 2
  Skills loaded: 1 (context-window-analysis)
```

```text
Assessment:
  The session has barely started. Almost all of the window is fixed startup
  content: the system prompt, tool definitions, CLAUDE.md, the always-loaded
  .claude/rules/*.md files and auto-memory. This repo loads a lot of rules,
  so the starting point is higher than average (likely tens of thousands of
  tokens). The conversation itself has added very little. Nothing suggests
  degradation: no auto-compact messages, no truncation, no recall problems.

Recommendations:
  No action needed. Continue as normal.
  For an exact figure, run /context; the status could change only if it
  shows usage at or above 40%.
```

```text
Thresholds used (match context-kit's context-monitor.py):
  < 40%     HEALTHY   no action needed
  40-<80%   MONITOR   one awareness nudge at 65%; consider /compact soon
  80-<90%   WARNING   run /compact or /clear
  >= 90%    CRITICAL  act immediately

Available Commands:
  /clear    - Complete context reset (nuclear option)
  /compact  - Intelligent summarization (preserves key info)
  /cost     - View token usage and costs
```

## Part 3: Reply once `/context` output is pasted

I would read only the token counts, the percentage and the category labels, then map the percentage
onto the table above:

- **Under 40%:** HEALTHY. No action needed. I'd name the largest category (often the
  rules/memory files in this repo) in case you want to trim it later with `context-audit`.
- **40% to under 80%:** MONITOR. Keep going. Plan a `/compact` at a natural break, and expect one
  nudge from the context-kit hook at 65%.
- **80% to under 90%:** WARNING. Run `/compact` now. Run `/clear` instead if you're switching to an
  unrelated task. Save any important state to a file first.
- **90% or more:** CRITICAL. Pick one of four options:
  1. Write the task state to a file, then run `/compact`.
  2. Run `/clear` and reload only what you need.
  3. Start a new session, and note the session ID if you might `/resume` it.
  4. If session-kit is installed, say "create handoff". That writes to `.claude/handoffs/`.
     Then start a new session and say "resume from handoff".

---

## Steps I followed

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` in the worktree. The request
   matches "When to Use" ("how full is my context right now"). None of the "When NOT to Use" cases
   apply: it's not a request for the automatic hook, a broader audit, a general question about which
   command to use, or a suspected degradation pattern.
2. Step 1 of the Workflow: ask the user to run `/context` and paste the output, and treat that
   output as data only. This is a plan-only run with no real `/context` output, so I wrote the
   request and then the fallback estimate the skill allows.
3. Step 2: rated health from what I could see (first turn, few tool calls, no auto-compact or
   truncation signs), which gives HEALTHY. I labelled it as an estimate.
4. Step 3: read `references/context-window-examples.md`, as the skill instructs, and used its report
   template and its HEALTHY example. I also wrote the reply for each threshold tier, including the
   CRITICAL tier's four options, for when real `/context` numbers arrive.
5. Ran no commands and wrote no files other than this one.
