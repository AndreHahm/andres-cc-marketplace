# Subagent Templates

Copy-paste starting points for common subagent patterns. Customize name, description, and prompt body for your use case.

**Plugin-scoped agents: `permissionMode` and `hooks:` in the templates below are not honored.** Every
template here that sets `permissionMode` or `hooks:` (e.g. the background/hook-gated templates) describes
behavior for a non-plugin (project-level) agent. If you're copying a template into a plugin's `agents/`
directory, those fields ship harmlessly but do nothing — the template's actual safety comes only from its
`tools` list. Narrow `tools` to match what the agent's body genuinely does; don't rely on `permissionMode`
or `hooks:` to contain a plugin-scoped agent copied from one of these templates.

**Long templates live in `assets/`:** the longer templates and examples below are stored as standalone agent files in this skill's `assets/` folder instead of inline code blocks, so each stays a complete, copy-paste-ready agent file without exceeding the rulebook's code-block size limit. Each section names its file.

## Table of Contents

- [Real-World Examples (Copy These)](#real-world-examples-copy-these)
- [Basic Template](#basic-template)
- [Read-Only Analysis Template](#read-only-analysis-template)
- [Code Review Template](#code-review-template)
- [Database Query Template](#database-query-template)
- [Code Fixing Template](#code-fixing-template)
- [Background Research Template](#background-research-template)
- [Common Frontmatter Options](#common-frontmatter-options)
- [Workflow Patterns](#workflow-patterns)
- [Customization Checklist](#customization-checklist)

## Real-World Examples (Copy These)

### Database Query Analyzer (Read-Only, Background)

Template file: `${CLAUDE_SKILL_DIR}/assets/example-db-analyzer.md`

**Validation Script** (`scripts/validate-readonly-query.sh`):
```bash
#!/bin/bash
# PreToolUse hook: blocks write operations for database safety

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if echo "$COMMAND" | grep -iE '\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE)\b' > /dev/null; then
  echo "Blocked: Write operations not allowed. Use SELECT queries only." >&2
  exit 2
fi

exit 0
```

### Code Review Agent (Interactive, Approval-Based)

Template file: `${CLAUDE_SKILL_DIR}/assets/example-code-reviewer.md`

### Background Analysis Task (Async, Autonomous)

Template file: `${CLAUDE_SKILL_DIR}/assets/example-log-analyzer.md`

---

## Basic Template

Use this when creating a simple subagent with standard configuration:

Template file: `${CLAUDE_SKILL_DIR}/assets/template-basic.md`

**Customize:**
- `name`: Your subagent name (lowercase-hyphen)
- `description`: Replace brackets with specific triggers and constraints
- `tools`: Keep only tools you need
- `permissionMode`: Choose based on foreground/background use
- Body sections: Fill in with your specific guidance

## Read-Only Analysis Template

For subagents that analyze data, search code, or research without modifying anything:

Template file: `${CLAUDE_SKILL_DIR}/assets/template-read-only-analysis.md`

## Code Review Template

For subagents that review code but don't modify it:

Template file: `${CLAUDE_SKILL_DIR}/assets/template-code-review.md`

## Database Query Template

For subagents that execute read-only database queries with validation:

Template file: `${CLAUDE_SKILL_DIR}/assets/template-database-query.md`

See "Database Query Analyzer" in Real-World Examples above for the complete validation script.

## Code Fixing Template

For subagents that modify code based on analysis or requirements:

Template file: `${CLAUDE_SKILL_DIR}/assets/template-code-fixing.md`

## Background Research Template

For lightweight subagents that run in background while main conversation continues:

Template file: `${CLAUDE_SKILL_DIR}/assets/template-background-research.md`

## Common Frontmatter Options

### Models

| Model | Use When |
|-------|----------|
| `sonnet` (default) | Balanced capability and speed; general purpose |
| `opus` | Complex reasoning, detailed analysis, careful decisions |
| `haiku` | Fast, simple tasks, background processing, cost-sensitive |
| `inherit` | Consistency with parent conversation |

### Tool Sets

**Read-only research:**
```yaml
tools: Read, Grep, Glob
```

**Code analysis & review:**
```yaml
tools: Read, Grep, Glob, Bash
```

**Code modification:**
```yaml
tools: Read, Write, Edit, Bash, Grep, Glob
```

**Database (validated):**
```yaml
tools: Bash
# Plus hooks for validation
```

### Permission Modes

**Interactive (foreground):**
```yaml
permissionMode: default
# User confirms each operation
```

**Trusted editing:**
```yaml
permissionMode: acceptEdits
# Auto-approve edits, ask for other operations
```

**Background processing:**
```yaml
permissionMode: dontAsk
# Auto-deny prompts, but tool access still works
```

**Read-only analysis:**
```yaml
permissionMode: plan
# Block all writes, reads allowed
```

## Workflow Patterns

### Simple Analysis

```
1. Understand request
2. Find relevant files
3. Analyze
4. Report findings
```

### Problem Investigation

```
1. Identify problem
2. Reproduce issue
3. Locate code
4. Analyze root cause
5. Suggest fix
```

### Code Modification

```
1. Understand requirements
2. Analyze existing code
3. Implement changes
4. Test changes
5. Report modifications
```

### Parallel Research (Background)

```
1. Identify topic
2. Find relevant code
3. Quick analysis
4. Report summary
```

## Customization Checklist

When adapting a template:

- [ ] Change `name` to your subagent name
- [ ] Rewrite `description` with YOUR specific triggers
- [ ] Select `model` based on task complexity
- [ ] Select `tools` based on what's needed
- [ ] Select `permissionMode` based on use case
- [ ] Customize prompt body for your domain
- [ ] Add hooks if validation is needed
- [ ] Test with real requests before deploying

---

## Plugin Agent Template

For creating a standalone `agents/*.md` file in a Claude Code plugin (distinct from the inline Agent() call subagents above):

Template file: `${CLAUDE_SKILL_DIR}/assets/template-plugin-agent.md`

**Customize:**
- `name`: Agent identifier (3–64 chars, lowercase-hyphens)
- `description`: One sentence, starts "Use this agent when [condition]."
- `tools`: Restrict to minimum needed (principle of least privilege)
- Body: Replace all `[...]` placeholders with specific content for your domain
