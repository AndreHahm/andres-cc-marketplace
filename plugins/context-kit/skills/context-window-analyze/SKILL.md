---
name: context-window-analyze
description: >-
  Analyze the current context window's live health and provide optimization recommendations. Use
  when responses feel slow, the user asks "how full is my context", or before deciding between
  /compact, /clear, or continuing as-is.
---

# Check Context

Analyze the current context window state and provide recommendations for optimization. This helps identify when context is becoming bloated and action is needed.

For a broader footprint audit (skills, CLAUDE.md, plugins, MCP servers — not just the live window), see
`context-audit` instead; the two overlap on live `/context` notes but this skill focuses on the current
window's health in the moment.

## When to Use

- "how full is my context right now"
- Responses feel slower than usual, or the user reports memory gaps
- Deciding between `/compact`, `/clear`, or continuing as-is
- Before a large operation that will consume significant context

## When NOT to Use

- Automatic, hook-driven detection of a good compaction moment — that's `strategic-compact`'s job (this
  plugin, Wave 1); this skill is a manually-triggered check, not the automation itself
- A broader skills/CLAUDE.md/plugin/MCP footprint audit — use `context-audit` instead

## Usage

```text
/context-window-analyze
```

## What Gets Analyzed

1. **Current Context Size** - Estimated token usage
2. **Context Composition** - What's consuming tokens
3. **Health Assessment** - Whether action is needed
4. **Optimization Options** - Available remediation

## Context Health Thresholds

| Usage | Status | Action |
|-------|--------|--------|
| < 50% | HEALTHY | No action needed |
| 50-75% | MONITOR | Consider /compact soon |
| 75-85% | WARNING | Run /compact or /clear |
| > 85% | CRITICAL | Immediate action required |

## Context Composition (Typical)

Claude Code's context typically includes:

| Component | Typical Size | Notes |
|-----------|--------------|-------|
| System prompt | 15-25k tokens | Base instructions |
| CLAUDE.md files | 5-15k tokens | Memory files |
| Loaded skills | 1-5k tokens | Active skills |
| Conversation history | Variable | Grows with turns |
| Tool results | Variable | Can be large |
| File contents | Variable | From Read operations |

## Workflow

### Step 1: Estimate Context Usage

Note: Exact context usage is internal to Claude Code. This command provides estimates based on observable factors:

```text
Factors to consider:
- Conversation length (turns)
- Recent file reads
- Tool output volume
- Loaded skills/memory
```

### Step 2: Assess Health

Based on observable signals:

**Healthy Indicators:**

- Quick response times
- No truncation warnings
- Accurate recall of early context

**Warning Indicators:**

- Slower responses
- Occasional memory gaps
- Auto-compact messages appearing

**Critical Indicators:**

- Very slow responses
- Frequent context rot
- Truncation warnings
- Failed operations

### Step 3: Provide Recommendations

**R18 exception (recorded):** the block below is 27 lines, above the rulebook's 20-line Warning threshold — it's a single coherent output template showing every section at once; splitting it would fragment the report shape across multiple fences without removing any content.

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

## Example Output

### Healthy Context

**R18 exception (recorded):** the block below is 21 lines, above the rulebook's 20-line Warning threshold — it's a complete worked example of the Step 3 template applied to a real case; splitting it would separate the example from its own context.

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

### Warning State

**R18 exception (recorded):** the block below is 25 lines, above the rulebook's 20-line Warning threshold — same reasoning as the Healthy Context example above (a complete worked example of the Step 3 template).

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

### Critical State

**R18 exception (recorded):** the block below is 40 lines, above the rulebook's 30-line Critical threshold — it's a complete worked example covering all 4 remediation options at once; splitting it into references/ would just re-wrap the same content in another oversized fence there, since the pedagogical value is seeing all 4 options together for comparison.

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
    3. Fresh 200k token context

  Option 4 (New Session with Handoff, if session-kit is installed):
    1. Trigger session-kit's session-handoff skill — say "create handoff" (it's model-invoked, not
       a slash command). It writes a validated, staleness-checked document to .claude/handoffs/
    2. Start a new Claude Code session, then say "resume from handoff" to load it back
    3. Optimized, focused context in the new session
```

## Notes

- This command provides estimates - exact token counts are internal
- Observable signals are good proxies for context health
- When in doubt, /compact is safer than continuing
- Sub-agents help by isolating context-heavy operations

## Testing & Validation

No `evals/context-window-analyze/evals.json` — this skill is guidance the model applies directly (an estimation heuristic + a fixed report template), not a deterministic tool with branching logic to eval.

**Verify this skill activates on:**
- "how full is my context"
- "should I compact now"
- Responses feel slow and the user asks what's going on

**Verify it does NOT activate on:**
- "audit my skills and CLAUDE.md for context bloat" (broader footprint, not the live window) → `context-audit`
- A request for the automatic hook-driven compaction-timing behavior itself → `strategic-compact`

**Quality gates:**
- [ ] Never references a nonexistent slash command for handoff — Option 4 always names `session-kit`'s real `session-handoff` skill (trigger phrase, not a command) and its real `.claude/handoffs/` storage location
- [ ] Every oversized worked-example block carries its own `R18 exception (recorded)` note rather than being silently over threshold
