# Context Window Analysis — Report Template and Worked Examples

Read when: writing or reviewing a `context-window-analyze` report — the output template
(Step 3 of the skill's own Workflow) plus a complete worked example at each of the four
health-status tiers (HEALTHY, WARNING, CRITICAL — MONITOR has no distinct example since its
guidance is the same shape as HEALTHY with an earlier nudge).

## Report Template

```text
Context Window Analysis
=======================

Estimated Status: {HEALTHY | MONITOR | WARNING | CRITICAL}

Observable Indicators:
  Conversation turns: {count}
  Recent file reads: {count} files
  Tool invocations: {count}
  Skills loaded: {list}

Assessment:
  {description of current state}

Recommendations:
  {prioritized actions}

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

## Example: Healthy Context

```text
Context Window Analysis
=======================

Estimated Status: HEALTHY

Observable Indicators:
  Conversation turns: 8
  Recent file reads: 3 files
  Tool invocations: 12
  Skills loaded: 2 (docs-management, skill-development)

Assessment:
  Context appears healthy. Responses are quick and
  accurate. No signs of degradation.

Recommendations:
  No action needed. Continue as normal.

Tips:
  - Current session is efficient
  - Consider /clear before starting a new major task
```

## Example: Warning State

```text
Context Window Analysis
=======================

Estimated Status: WARNING

Observable Indicators:
  Conversation turns: 47
  Recent file reads: 23 files
  Tool invocations: 156
  Skills loaded: 5

Assessment:
  Context is getting full. You may notice:
  - Slightly slower responses
  - Occasional gaps in recalling earlier context
  - Auto-compaction may trigger soon

Recommendations:
  1. Run /compact to summarize and free space
  2. Or run /clear if starting a new task
  3. Save important context to a temp file first

Warning Signs to Watch:
  - If responses slow further, act immediately
  - Watch for truncation or "I don't recall" responses
```

## Example: Critical State

Covers all 4 remediation options together, since the pedagogical value is seeing them
side by side for comparison — this is why the Critical-state example stays a single block
rather than being split further.

```text
Context Window Analysis
=======================

Estimated Status: CRITICAL

Observable Indicators:
  Conversation turns: 89
  Recent file reads: 45 files
  Tool invocations: 312
  Skills loaded: 7
  Auto-compact triggered: 3 times

Assessment:
  Context is near capacity. Significant degradation likely:
  - Very slow responses expected
  - Poor recall of earlier context
  - Risk of failed operations

IMMEDIATE ACTION REQUIRED:

  Option 1 (Preserve Progress):
    1. Document current task state to file
    2. Run /compact
    3. Resume with focused context

  Option 2 (Clean Start):
    1. Run /clear
    2. Reload only essential context
    3. Continue with fresh context

  Option 3 (New Session without Handoff):
    1. Note session ID for /resume if needed
    2. Start new Claude Code session
    3. Fresh context window at the configured model/window size (e.g. `CLAUDE_CONTEXT_WINDOW_TOKENS`)

  Option 4 (New Session with Handoff, if session-kit is installed):
    1. Trigger session-kit's session-handoff skill — say "create handoff" (it's model-invoked, not
       a slash command). It writes a validated, staleness-checked document to .claude/handoffs/
    2. Start a new Claude Code session, then say "resume from handoff" to load it back
    3. Optimized, focused context in the new session
```
