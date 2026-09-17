---
name: context-engineering
description: >-
  Master the four operations of context engineering — Write, Select, Compress, Isolate — to manage
  token budgets, compaction strategies, and context partitioning. Use when planning how to keep an AI
  coding session efficient, deciding what to persist vs. retrieve vs. compress, or designing a
  context budget for a task before it starts.
user-invocable: true
allowed-tools: Read
---

# Context Engineering

Four operations control everything about how context flows through an AI coding session. Master them and you control the quality of every response.

This skill is the canonical source for the Write/Select/Compress/Isolate framework in this plugin —
`context-degradation` references it (rather than restating it) when mapping a diagnosed degradation
pattern to the operation that mitigates it.

## When to Use

- Planning how to keep an AI coding session's context lean before or during a task
- Deciding whether information should be persisted (Write), retrieved precisely (Select), summarized
  (Compress), or isolated to a sub-agent/worktree/fresh session (Isolate)
- Setting up a context budget for a task, or choosing between `/clear`, `/compact`, and delegating to
  a subagent
- Writing a project's own CLAUDE.md guidance for context management

## When NOT to Use

- A context failure is already happening (lost-in-middle, poisoning, confusion, clash) and needs
  diagnosis first — use `context-degradation` to identify which pattern is active, then come back here
  for the matching operation
- Only the automatic phase-transition/compaction-timing suggestion behavior is wanted — that's
  `strategic-compact`'s job (hook-driven, this plugin's own automatic layer); this skill is the
  manually-applied conceptual framework, not the automation itself
- @ mentions or semantic search specifically — see `context-optimization` for that detailed how-to
- A live, point-in-time read of the current window's actual fullness/composition — use
  `context-window-analyze` first to get the real numbers, then return here for the general
  Write/Select/Compress/Isolate framework if still deciding what to do about it

## The Four Operations

### 1. Write — Persist Info Outside Context

Move information out of the context window into durable storage so it survives compaction and session boundaries.

**Where to write:**

| Target | When | Example |
|--------|------|---------|
| CLAUDE.md | Permanent project rules | "Always use pnpm, never npm" |
| A gitignored scratch file | Working state for current task | Architecture decisions, open questions |
| `.claude/memory/` | Learnings and patterns | `[LEARN]` rules from corrections |
| External files | Data too large for context | Test plans, migration checklists |

**Pattern — Scratchpad workflow:** name the file `NOTES.md` if you like, but put it wherever this
project already keeps gitignored scratch content (a session scratchpad, `.claude/`, `.draft/`, etc.) —
never bare at the repo root, which turns working state into untracked clutter the project can't clean up.
```text
1. Start complex task → create a gitignored scratch file with goals and constraints
2. After research → write findings to it
3. After compaction → the scratch file survives, context does not
4. Resume → read it back to recover full state
```

### 2. Select — Retrieve Relevant Info

Pull the right information into context at the right time. Precision matters more than volume.

**Methods ranked by precision:**

1. `@file` references — exact file injection
2. `grep` / `Glob` — targeted pattern search
3. Subagent exploration — delegated deep search
4. RAG / embeddings — semantic retrieval for large codebases

**Key principle: Focused 1000 tokens > unfocused 113K tokens.**

A surgical grep result that returns the exact function signature beats dumping an entire module into context. Every irrelevant token dilutes attention.

**Pattern — Progressive retrieval:**
```text
1. Start with file names (Glob)
2. Narrow to specific functions (Grep)
3. Read only the relevant lines (Read with offset+limit)
4. Never read entire large files when you need one function
```

### 3. Compress — Reduce Tokens, Preserve Signal

Shrink context without losing the information that matters.

**Compaction strategies:**

| Strategy | How | When |
|----------|-----|------|
| `strategic-compact`'s hooks (this plugin) | Automatic — no manual trigger; nudges via `additionalContext`/`Stop`-block when a good compaction point is detected | Automated phase-transition/tool-call-threshold signals |
| `/compact` with focus | `/compact focus: auth module changes` | Task boundaries |
| Microcompact | Ask Claude to summarize tool output inline | After large reads/searches |
| Head+tail | Read first 20 + last 20 lines of large output | Log analysis, test results |
| Tool result clearing | Subagent results auto-clear after reporting | Heavy exploration |
| Semantic selection | Summarize findings, discard raw data | Research phases |

**Compaction triggers:**

- `strategic-compact`'s own hooks detect one (exploration→implementation, milestone reached, 50+ tool calls)
- After planning, before implementation
- After completing a feature or milestone
- When context exceeds 80% (set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`)
- Before switching task domains
- After heavy search/read operations

**PostCompact hook — Re-inject critical context:**
```json
{
  "hooks": {
    "PostCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "command",
            "command": "cat .claude/critical-context.md"
          }
        ]
      }
    ]
  }
}
```

Use this to ensure project rules, current task state, or architecture constraints survive every compaction.

### 4. Isolate — Partition Across Execution Spaces

Don't load everything into one context. Split work across independent execution spaces.

| Method | Isolation Level | Use When |
|--------|----------------|----------|
| Subagents | Forked context | Heavy exploration, test runs, doc generation |
| Worktrees (`claude -w`) | Full repo copy | Parallel features, competing approaches |
| `/btw` (built-in Claude Code) | Temporary overlay | Quick questions without entering conversation history |
| Agent teams | Independent sessions | Cross-layer changes, parallel reviews |
| Fresh session (no `/resume`) | Clean slate | Unrelated work, degraded context |

`/resume` is continuity, not isolation — it loads the original session's context back into memory
(see `session-kit`'s `session-resume`), so it carries degraded context forward rather than clearing
it. For a genuine clean slate, start a new session without `/resume`.

**Pattern — Subagent delegation:**
```text
Main session: planning, coordination, commits
Subagent 1: explore auth module, report findings
Subagent 2: run test suite, report failures
Subagent 3: generate migration script
```

Main context stays clean. Subagents handle the volume.

## Context Budget Planning

Example baseline (calibrate with `/context`): ~200K total window, ~20K overhead (CLAUDE.md, tool definitions, MCP schemas). Plan around **~180K usable** — actual budgets vary by model and configuration.

| Allocation | Budget | What Goes Here |
|------------|--------|----------------|
| Static context | 20-30K | CLAUDE.md, tool schemas, MCP definitions |
| Dynamic context | 150-180K | Code, conversation, tool results |

**Put static context first.** CLAUDE.md and tool definitions load before conversation. Keeping them stable maximizes prompt cache hits — saves cost and latency.

| Phase | Target Usage | Action If Over |
|-------|-------------|----------------|
| Planning | < 20% | Keep plans concise, write to scratchpad |
| Implementation | < 50% | Compact between files, delegate reads |
| Testing | < 70% | Delegate test runs to subagents |
| Review | < 85% | Start fresh session if degraded |

## When to /clear vs /compact vs Subagent

| Situation | Action |
|-----------|--------|
| Task boundary, want to keep learnings | `/compact` with focus |
| Context degraded, Claude repeating itself | `/compact`, then `/resume` if still bad |
| Starting unrelated work | `/clear` or new session |
| Heavy read/search operation | Delegate to subagent |
| Quick side question | `/btw` (doesn't pollute main context) |
| Exploring multiple approaches | Worktrees or agent teams |

## Anti-Patterns

- Loading entire files when you need one function
- Keeping MCP tool results in context after extracting what you need
- Running 15+ MCPs (each adds tool schema overhead to every request)
- Vague prompts that force Claude to search broadly ("fix the code")
- Never compacting until auto-compact triggers at 95%

## Add to CLAUDE.md

```markdown
## Context Engineering

Write working state that must survive compaction to a gitignored scratch file -- never bare at repo root.
Select with precision — grep first, read specific lines, never dump whole files.
Compact at 80% or task boundaries. Set CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80.
Isolate heavy work to subagents. Main session stays for coordination and commits.
```

## Related Skills

- `context-degradation` — diagnoses *which* pattern (lost-in-middle, poisoning, distraction, confusion,
  clash) is degrading a session and *when* it's active. Once diagnosed, apply the matching operation
  above. This skill owns the operations; `context-degradation` owns the diagnosis.
- `context-optimization` — @ mentions and semantic search are one specific instance of the "Select"
  operation above; see that skill for the detailed tactics.
- `strategic-compact` (this plugin, Wave 1) — the automatic, hook-driven layer that detects compaction
  moments; this skill is the manually-applied conceptual framework those hooks are informed by, not a
  duplicate of the automation itself.

## Testing & Validation

No `evals/context-engineering/evals.json` — this skill is a reference framework the model applies directly (choosing which of four operations fits a situation), not a deterministic tool with branching logic to eval. The structural claims this section documents (sole canonical-source ownership, cross-references resolving, sibling skills never restating the framework) are covered by the persisted `scripts/smoke_test.py`.

**Last dated run record:** `scripts/smoke_test.py` — 5/5 checks passing as of 2026-09-17.

**Verify this skill activates on:**
- "how should I manage context for this task"
- "should I write this to a scratchpad or keep it in context"
- "help me plan a context budget for this feature"

**Verify it does NOT activate on:**
- "why is the agent ignoring information I gave it earlier" (active failure, not planning) → `context-degradation`
- "how do I use @ mentions effectively" alone → `context-optimization`

**Quality gates:**
- [ ] Never duplicates `context-degradation`'s Four-Bucket Mitigation Framework — this skill is the single canonical source for Write/Select/Compress/Isolate
- [ ] The Compress section's compaction-strategy table and trigger list always name `strategic-compact` explicitly where its hooks are the mechanism, never a bare unnamed "strategic compact" phrase
- [ ] The Write operation's scratchpad guidance never presents a bare repo-root filename (e.g. `NOTES.md`) as the default location — it always points at a gitignored, project-scoped location instead, since a literal reader following this skill in a project with a no-root-scratch policy would otherwise leave untracked clutter at the repo root (found by a cross-model review pass, 2026-09-16)
- [ ] The Isolate table never labels `/resume` as a "clean slate" — `/resume` loads the prior session's context back into memory (continuity, not isolation); only a genuinely fresh session (no `/resume`) is a clean slate (this gate previously lived in `context-audit`'s own checklist, moved here 2026-09-17 since it's a fact about this skill's own content, not `context-audit`'s)
