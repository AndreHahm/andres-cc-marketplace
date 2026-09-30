# Advanced Patterns & Production Skills

## Table of Contents
- [Advanced Patterns from Production](#advanced-patterns-from-production)
- [Common Skill Archetypes](#common-skill-archetypes)

---

## Advanced Patterns from Production

These patterns emerge from real-world skill collections and production systems.

### Pattern 1: "THE EXACT PROMPT"

Encode reproducible prompts in all-caps sections for agent-to-agent handoff:

````markdown
## THE EXACT PROMPT — Plan Review

```
Carefully review this entire plan for me and come up with your best
revisions in terms of better architecture, new features...
```
````

**Why it works:**
- Prompts are copy-paste ready
- Stream Deck / automation friendly
- No ambiguity about phrasing
- Enables cross-model workflows (GPT Pro → Claude Code)

### Pattern 2: "Why This Exists" Section

Front-load motivation before instructions:

```markdown
## Why This Exists

Managing multiple AI coding agents is painful:
- **Window chaos**: Each agent needs its own terminal
- **Context switching**: Jumping between windows breaks flow
- **No orchestration**: Same prompt to multiple agents = manual copy-paste

This skill solves all of this...
```

Helps Claude understand when to apply the skill contextually.

### Pattern 3: Integration Sections

Complex tools should document ecosystem connections:

```markdown
## Integration with Ecosystem

| Tool | Integration |
|------|-------------|
| **Agent Mail** | Message routing, file reservations |
| **BV** | Work distribution, triage |
| **CASS** | Search past sessions |
```

### Pattern 4: Risk Tiering Tables

For safety/security skills, use explicit tier classifications:

```markdown
| Tier | Approvals | Auto-approve | Examples |
|------|-----------|--------------|----------|
| **CRITICAL** | 2+ | Never | `rm -rf /`, `DROP DATABASE` |
| **DANGEROUS** | 1 | Never | `git reset --hard` |
| **CAUTION** | 0 | After 30s | `rm file.txt` |
| **SAFE** | 0 | Immediately | `rm *.log` |
```

### Pattern 5: Robot Mode / Machine-Readable Output

For orchestration tools, document JSON/NDJSON APIs:

````markdown
## Robot Mode (AI Automation)

```bash
ntm --robot-status              # Sessions, panes, agent states
ntm --robot-snapshot            # Unified state: sessions + beads + mail
```

Output format:
```json
{"type":"request_pending","request_id":"abc123","tier":"dangerous"}
```
````

### Pattern 6: Exit Code Standardization

```markdown
## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error |
| `2` | Invalid arguments / Unavailable |
| `3` | Not found |
| `4` | Permission denied |
| `5` | Timeout |
```

### Pattern 7: ASCII State Diagrams

Visualize complex flows:

````markdown
### Processing Pipeline

```
┌─────────────────┐
│   Claude Code   │  Agent executes command
└────────┬────────┘
         │
         ▼ PreToolUse hook (stdin: JSON)
┌─────────────────┐
│      dcg        │
│  ┌──────────┐   │
│  │  Parse   │──▶│ Normalize ──▶ Quick Reject
│  └──────────┘   │
└────────┬────────┘
         │
         ▼ stdout: JSON (deny) or empty (allow)
```
````

### Pattern 8: Hierarchical Configuration Documentation

```markdown
## Configuration

Configuration precedence (lowest to highest):
1. Built-in defaults
2. User config (`~/.config/tool/config.toml`)
3. Project config (`.tool/config.toml`)
4. Environment variables (`TOOL_*`)
5. Command-line flags
```

### Pattern 9: Extended Thinking Signals

For complex prompts, append thinking mode instructions:

```markdown
...hyper-optimize for both separately to play to the specifics of
each modality. Use ultrathink.
```

Signals to Claude to use extended thinking for thorough analysis.

### Pattern 10: Iteration Protocols

For refinement workflows, specify iteration counts:

```markdown
### Repeat Until Steady-State

- Start fresh conversations for each round
- After 4-5 rounds, suggestions become very incremental
```

---

## Common Skill Archetypes

### CLI Reference Skill

**Examples:** github, gcloud, vercel skills

**Structure:**
```markdown
# Tool Name Skill

## Authentication
[auth commands]

## Core Operations
[main commands grouped by function]

## Common Workflows
[multi-step recipes]
```

**Token efficiency:** Pure reference, minimal prose. Claude already knows CLI semantics.

### Methodology Skill

**Examples:** planning-workflow, de-slopify

**Structure:**
```markdown
# Methodology Name

> **Core Philosophy:** [one-liner insight]

## Why This Matters
[brief motivation]

## THE EXACT PROMPT
[copy-paste ready prompt]

## Why This Prompt Works
[technical breakdown]

## Before/After Examples
[concrete demonstrations]
```

### Safety Tool Skill

**Examples:** dcg (Detection Control Guard), security tools

**Structure:**
```markdown
# Tool Name

## Why This Exists
[threat model]

## Critical Design Principles
[architecture decisions]

## What It Blocks / Allows
[tables of patterns]

## Modular System
[extensibility]

## Security Considerations
[limitations, threat model assumptions]
```

### Orchestration Tool Skill

**Examples:** ntm, agent-mail

**Structure:**
```markdown
# Tool Name

## Why This Exists
[pain points solved]

## Quick Start
[minimal viable usage]

## Core Commands
[organized by function]

## Robot Mode
[machine-readable APIs]

## Integration with Ecosystem
[connections to other tools]
```
