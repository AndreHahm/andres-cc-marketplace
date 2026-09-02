---
name: session-memory
description: >-
  Lists and summarizes all Claude Code memories across projects (no keyword
  required). Use when the user asks what memories exist, wants to see stored
  knowledge, asks "what do you remember", or wants an overview of their memory
  files. Also triggered by: "list memories", "show memories", "what's in my
  memory". For finding memories by keyword/content, use session-memory-search
  instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory_scanner.py":*)
---

# Session Memory

List and summarize all memory files across projects.

## When to Use

- Wants an overview/listing of stored memories (no keyword needed)
- "what do you remember", "list memories", "show memories"

## When NOT to Use

- Finding memories by keyword/content → use `session-memory-search` instead
- Health-checking memories (staleness, broken links, duplicates) → use `session-memory-audit` instead

## Step 1: Scan all memories

Run the memory scanner to discover all memory files across projects:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory_scanner.py" scan
```

This command always prints JSON — no `--format` flag needed.

Optional filters — add based on user request:
- `--type user|feedback|project|reference` — filter by memory type
- `--project FILTER` — filter by project name (substring match)

## Step 2: Present the results

Parse the JSON output and present as a **grouped-by-project** table:

**For each project that has memories, show:**

| # | Name | Type | Age | Indexed |
|---|------|------|-----|---------|
| 1 | Memory name | `type` | Nd | yes/no |

**At the top, show the summary line:**
> Found **N memories** across **M projects** — N user, N feedback, N project, N reference

**Highlight issues if visible:**
- If any memory has `indexed: false`, note it: "N memories not indexed in MEMORY.md — run the `session-memory-audit` skill to fix"
- If any memory has `has_frontmatter: false`, note it: "N memories missing frontmatter"

## Step 3: Suggest follow-ups

Based on what was found, suggest relevant next steps:
- The `session-memory-audit` skill — to health-check and fix issues
- The `session-memory-search` skill — to search across memory content

## Testing & Validation

**Verify this skill activates on:**
- "what do you remember"
- "list my memories"
- "show me what's in my memory"

**Verify it does NOT activate on:**
- "search my memories for X" → `session-memory-search`
- "check my memory health" → `session-memory-audit`

**Quality gates:**
- [ ] Follow-up suggestions name the sibling skill, never a `/slash-command` that doesn't exist in this plugin
