---
name: context-optimization
description: >-
  Effective use of @ mentions and semantic search for targeted context retrieval. Use when deciding
  whether to @-mention a specific file vs. let the agent search, choosing between @ mentions and
  grep/Glob, or running a natural-language semantic search over an unfamiliar codebase.
allowed-tools: Read
---

# Context Optimization

Strategies for effective context management: @ mentions, context window optimization, and semantic search.

## When to Use

Use this skill when:
- Deciding whether to @-mention a specific file/folder vs. let the agent search for it
- Choosing between @ mentions, grep/Glob, and semantic search for a given lookup
- Running a natural-language semantic search over an unfamiliar codebase
- Reviewing whether @ mention usage in a task is over- or under-used

## When NOT to Use

- Planning a broader context budget, or deciding between Write/Select/Compress/Isolate for a whole task — use `context-engineering` instead; this skill covers one instance of its "Select" operation
- A context failure is already happening (lost-in-middle, confusion) — use `context-degradation` to diagnose it first

## @ Mentions

- **@Files & Folders**: Reference files or directories
- **@Code**: Reference specific code sections
- **@Docs**: Reference documentation

**Use @ mentions for:**
- Specific examples to follow
- Related code patterns
- Configuration files
- Cross-referencing

**Let the agent search instead for:**
- General questions
- Broad exploration
- Discovery tasks
- Understanding flows

## Context Window Management

1. Use @ mentions selectively — reference files, don't paste their contents
2. Let the agent search automatically for broad/discovery tasks
3. Reference files instead of copying content into the conversation
4. Break large tasks into chunks
5. Use Plan Mode for complex features

## Semantic Search

Natural-language, meaning-based code discovery — complementary to `grep`'s exact-match search.

**Query strategies:**
- Ask natural-language questions, as you would ask a colleague ("How does authentication work in this codebase?", "Where is memory extraction handled?")
- Be specific about context ("authentication in backend" vs. just "authentication")
- Start broad, then narrow down — build understanding incrementally
- Combine with `grep` for verification once semantic search narrows the area
- Review multiple results for the full picture

**Use semantic search for:**
- Finding code by functionality
- Discovering related code
- Understanding implementations
- Finding similar patterns
- Exploring unfamiliar code

**Use `grep` for:**
- Exact string matches
- Specific function names
- Exact error messages
- File patterns

## Related Resources

- `context-engineering` — the broader Write/Select/Compress/Isolate framework this skill's "Select" tactics (@ mentions, semantic search) are one instance of.

## Testing & Validation

No `evals/context-optimization/evals.json` — this skill is guidance the model applies directly when choosing a retrieval strategy, not a deterministic tool with branching logic to eval. The structural claims this section documents (sibling cross-reference resolving, no restated framework headers) are covered by the persisted `scripts/smoke_test.py`.

**Last dated run record:** `scripts/smoke_test.py` — 4/4 checks passing as of 2026-09-17.

**Verify this skill activates on:**
- "should I @-mention this file or let you search for it"
- "how do I search this codebase by meaning, not exact text"
- "when should I use grep vs semantic search here"

**Verify it does NOT activate on:**
- "what's my overall context budget for this task" (broader planning) → `context-engineering`
- "the agent is ignoring context I gave it earlier" (active failure) → `context-degradation`

**Quality gates:**
- [ ] Never duplicates `context-engineering`'s full Write/Select/Compress/Isolate framework — only the "Select" tactics specific to @ mentions and semantic search
