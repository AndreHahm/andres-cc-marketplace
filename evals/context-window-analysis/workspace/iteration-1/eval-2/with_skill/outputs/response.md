# Context Check — Scope Note

Your request was "audit my skills and CLAUDE.md for context bloat." I ran this through **context-window-analyze**, but that skill is explicitly scoped to only one thing: the live health of the *current* context window (how full it is right now), not a footprint audit of skills, CLAUDE.md, plugins, or MCP servers. Its own "When NOT to Use" section says so directly:

> A broader skills/CLAUDE.md/plugin/MCP footprint audit — use context-audit instead. This skill does NOT audit skills or CLAUDE.md files; it only reports the live context window's current fullness.

So what you're asking for — an audit of your skills and CLAUDE.md for bloat — is **context-audit's job, not this skill's**. I did not perform that audit here, since doing so would exceed this skill's stated scope. Recommended next step:

```
Skill(context-audit)
```

That skill inventories always-loaded content (CLAUDE.md size/actionability, skill descriptions, plugin footprint, MCP server tool counts) and flags bloat sources directly — which is what "audit my skills and CLAUDE.md" actually calls for.

---

## What I *can* report (in scope): current live context window health

Since context-window-analyze is allowed-tools: Read only, and its job is the live window's fullness, here's that read for this turn:

| Usage | Status | Action |
|-------|--------|--------|
| < 40% | HEALTHY | No action needed |
| 40–<80% | MONITOR | Progressive nudges at 40/55/65%; consider `/compact` soon |
| 80–<90% | WARNING | Run `/compact` or `/clear` |
| >= 90% | CRITICAL | Immediate action required |

This session is early — a single skill dispatch with a modest system prompt and skill listing — and sits comfortably in the **HEALTHY** band (well under 40%). No `/compact` or `/clear` action is warranted right now.

## Bottom line

- **Live window right now:** HEALTHY, no action needed.
- **For "audit my skills and CLAUDE.md for context bloat":** that's out of this skill's scope by its own documented boundary — use `context-audit` instead, which is built for exactly that footprint analysis.
