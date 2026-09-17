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
| 50-<75% | MONITOR | Consider /compact soon |
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

### Step 1: Get Real Usage Data First

Ask the user to run `/context` and share the output — it reports the actual current tokens, max
capacity, percentage used, and composition breakdown, and is the reliable source for the
HEALTHY/MONITOR/WARNING/CRITICAL assessment in Step 2. Only fall back to indirect estimation below if
the user hasn't shared `/context` output (e.g. a quick check where asking would interrupt the flow):

```text
Factors to consider (fallback only, when /context output isn't available):
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

Read `references/context-window-examples.md` for the report template and a complete worked
example at each health tier (HEALTHY, WARNING, CRITICAL) — moved there so no single fence in
this file exceeds the rulebook's block-size thresholds; the reference's own header states when
to read it.

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
- [ ] Never references a nonexistent slash command for handoff — `references/context-window-examples.md`'s Option 4 always names `session-kit`'s real `session-handoff` skill (trigger phrase, not a command) and its real `.claude/handoffs/` storage location
- [ ] `references/context-window-examples.md` stays the sole home for the report template and worked examples — no oversized worked-example block gets re-inlined into this file
