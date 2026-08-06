# Subagent Configuration Reference

Complete reference for all YAML frontmatter fields available when creating subagents. Use this to understand each field, its valid values, defaults, and effects on subagent behavior.

**R18 exception (recorded):** several examples below intentionally exceed the rulebook's 30-line code-block threshold — each is a complete, coherent agent configuration or field-combination example; splitting one would leave a non-functional fragment.

## Table of Contents

- [Frontmatter Overview](#frontmatter-overview)
- [Required Fields](#required-fields)
- [Optional Fields](#optional-fields)
- [Field Combinations & Constraints](#field-combinations--constraints)
- [Complete Example](#complete-example)
- [Validation Checklist](#validation-checklist)
- [Scope Storage](#scope-storage)
- [Troubleshooting Configuration](#troubleshooting-configuration)
- [Next Steps](#next-steps)

## Frontmatter Overview

Subagent files use YAML frontmatter (between `---` delimiters) to configure the subagent:

```yaml
---
name: subagent-name
description: What the subagent does and when to use it
model: sonnet
tools: Read, Write, Bash
permissionMode: default
disallowedTools: Edit
skills: skill-name-1, skill-name-2
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./validate.sh"
color: blue
---

[System prompt body follows below]
```

**Field-ordering rule:** every configuration field MUST appear between the opening and closing `---` delimiters, as valid YAML. Content placed after the closing `---` is the system prompt body — it is never parsed as frontmatter, no matter how field-like it looks. This plugin's own convention doesn't use `<example>` blocks inside frontmatter (trigger scenarios go in the body's `## When to invoke` section instead — see `references/delegation.md`), which sidesteps the specific upstream gotcha where fields placed after an `<example>` block silently stop being parsed as YAML. If you're porting an agent authored against the upstream `<example>`-in-frontmatter convention, watch for exactly this: any field appearing after an `<example>` block in the original file was likely never actually taking effect.

## Required Fields

### `name`

**Required.** Unique identifier for the subagent. Used internally for references and in CLI commands.

**Rules:**
- Lowercase letters and hyphens only (no spaces, underscores, numbers)
- Maximum 64 characters
- Should be descriptive and action-oriented (e.g., `db-analyzer`, `code-reviewer`)
- Must be unique within the scope (session, project, user, plugin)

**Examples:**
```yaml
name: db-analyzer        # ✅ Good
name: code-reviewer      # ✅ Good
name: Test_Runner        # ❌ Invalid (underscores, capitals)
name: database-query-execution-and-analysis-tool  # ❌ Too long
```

### `description`

**Required.** Natural language description that triggers Claude's delegation to this subagent. This is the PRIMARY signal Claude uses to decide when to delegate.

**Rules:**
- Maximum 1024 characters
- Should follow pattern: `[Action]. Use when [trigger contexts]. [Scope/constraints].`
- Must include 3+ specific trigger phrases (not vague language)
- Should be concrete and actionable
- No marketing language

**Good pattern:**
```yaml
description: >-
  Execute read-only database queries for data analysis. Use when analyzing
  data, generating reports, or exploring table structure. SELECT only;
  write operations blocked.
```

**Poor patterns:**
```yaml
description: Database query subagent              # Too vague
description: >-
  Execute database operations. Use when needed.   # "when needed" is vague
```

For detailed guidance on writing descriptions, see `delegation.md`.

## Optional Fields

### `model`

**Optional.** AI model for this subagent to use. Defaults to `inherit`.

**Valid values:**
- `inherit` - Use same model as parent conversation (default)
- `sonnet` - Balanced capability/speed
- `opus` - Most capable, slower (use for complex reasoning)
- `haiku` - Fast, cheaper (use for simple tasks)
- `fable` - Additional selectable model
- Full model ID strings (e.g. `claude-sonnet-4-5`) are also accepted

**Effects:**
- Determines reasoning power and response quality
- Affects latency and cost
- Inheriting is useful when subagent work depends on parent context

**Examples:**
```yaml
model: haiku              # Fast, read-only tasks
model: opus              # Complex analysis requiring deep reasoning
model: inherit           # Keep consistency with parent conversation
```

**When to choose:**
- **haiku**: Read-only analysis, fast iteration, cost-sensitive
- **sonnet**: General purpose, balanced (default)
- **opus**: Complex reasoning, multi-step logic, production systems
- **inherit**: Subagent work chains with parent (needs parent's reasoning level)

**Role-tier mapping (advisory, not a hard rule):** as a starting heuristic when a task-based choice above isn't obvious, map the agent's role to a tier — **orchestrator** agents (dispatch other agents, hold the `Agent` tool) → `haiku`; **implementer/worker** agents (do the actual read/write/analysis work) → `sonnet`; **quality-gate/advisor/reviewer** agents (this plugin's own `*-reviewer` family) → `opus`. This is guidance for judgment calls, not a requirement — `inherit` remains valid and is often the right choice regardless of role.

### `color`

**Optional.** Display color for the agent in the UI. Do not hardcode this list elsewhere — verify against current platform documentation before publishing. At last review, valid values were:

`red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan`

**Examples:**
```yaml
color: blue     # analysis/review agents
color: red      # critical/security agents
```

### `tools`

**Optional.** Allowlist of tools the subagent can use. If omitted, inherits all tools from parent conversation.

**Valid tool names:**
- `Read` - Read files
- `Write` - Write new files
- `Edit` - Edit existing files
- `Bash` - Execute bash commands
- `Grep` - Search file contents
- `Glob` - Find files by pattern
- `Agent` - Launch subagents (renamed from `Task` in Claude Code v2.1.63; `Task(...)` still works as a legacy alias)
- `AskUserQuestion` - Ask user for input
- `Skill` - Invoke skills
- And any MCP tools available in parent conversation

**Format:**
```yaml
tools: Read, Grep, Glob           # Comma-separated list
tools: Read, Write, Edit, Bash    # Spaces after commas
```

**Principle of least privilege:**
- Only grant tools the subagent actually needs
- More restrictive = more secure

**Examples:**

```yaml
# Read-only analysis
tools: Read, Grep, Glob, Bash

# Code editor
tools: Read, Write, Edit, Bash

# Database analyst
tools: Bash, Read

# Background researcher
tools: Read, Grep, Glob
```

**Unavailable regardless of `tools`:** `AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, and `WaitForMcpServers` are never available to subagents even if listed. `ExitPlanMode` is unavailable unless the subagent runs with `permissionMode: plan`.

**Note:** If both `tools` and `disallowedTools` are specified, `disallowedTools` is applied first, then `tools` is resolved against the remaining pool — a tool listed in both is removed.

### `disallowedTools`

**Optional.** Denylist of tools to block. Removes these from the inherited or allowlist.

**Format:**
```yaml
disallowedTools: Edit, Bash       # Comma-separated
```

**When to use:**
- Start with all tools inherited, block specific ones
- Useful when you want "most tools except X"

**Examples:**

```yaml
# Allow everything except Write and Edit
disallowedTools: Write, Edit

# Start with all, deny dangerous tools
disallowedTools: Bash, Agent
```

**Rules:**
- `disallowedTools` is applied first; `tools` is then resolved against the remaining pool
- If `tools` is omitted, `disallowedTools` removes from all inherited tools
- A tool listed in both `tools` and `disallowedTools` is removed
- Tool names must be exact (case-sensitive)

### `permissionMode`

**Optional.** Controls how the subagent handles permission prompts. Defaults to `default`.

**Valid values:**
- `default` - Standard permission checking; interactive prompts to user
- `manual` - Alias for `default` (Claude Code v2.1.200+)
- `acceptEdits` - Auto-accept file edits (Edit/Write); prompt for others
- `dontAsk` - Auto-deny interactive prompts; explicit tool access still works
- `auto` - Automated permission handling for unattended execution
- `bypassPermissions` - Skip all permission checks (use cautiously)
- `plan` - Read-only mode (blocks all write operations)

**Behavior by mode:**

| Mode | Permission Prompts | File Edits | Bash | Result |
|------|-------------------|------------|------|--------|
| `default` / `manual` | ✅ Show to user | Ask | Ask | Interactive |
| `acceptEdits` | ✅ (except edits) | Auto-accept | Ask | Edits auto-approved |
| `dontAsk` | ❌ Auto-deny | Auto-deny | Works | No interaction |
| `auto` | ❌ Auto-deny | Auto-deny | Works | Unattended |
| `bypassPermissions` | ❌ Skipped | Auto-allow | Works | No checks |
| `plan` | ❌ Auto-deny | Blocked | Works (RO) | Read-only |

**Examples:**

```yaml
# Interactive; user approves everything
permissionMode: default

# Auto-approve file edits; ask for other permissions
permissionMode: acceptEdits

# Background execution; no interactive prompts
permissionMode: dontAsk

# Read-only research
permissionMode: plan

# Complete trust (production subagents only)
permissionMode: bypassPermissions
```

See `permission-modes.md` for detailed behavior in foreground/background execution.

**Plugin-agent constraint:** `hooks`, `mcpServers`, and `permissionMode` are accepted by this schema but are not honored for plugin-scoped agents.

### `skills`

**Optional.** Load skill content into the subagent's context at startup. The full skill instruction set is injected into the subagent's prompt.

**Format:**
```yaml
skills: skill-name-1, skill-name-2
```

**When to use:**
- Subagent needs specific reusable instructions
- Want injected skill context without invoking the skill as a tool
- Skill content should be available in subagent's reasoning

**Examples:**

```yaml
# Load a skill for custom instructions
skills: code-review-standards

# Multiple skills
skills: security-analysis, performance-optimization
```

**Important:**
- Subagents do NOT inherit skills from parent conversation
- Explicitly list skills you want available
- Full skill content is loaded (not just name reference)
- Increases token usage (skills are loaded into context)

**Difference from `Agent` tool:**
- `skills` field: Skill content injected into context (direct access to instructions)
- `Agent` tool: Launch a specialized subagent (separate execution context)

### `hooks`

**Optional.** Define lifecycle hooks that run during the subagent's execution. Hooks enable conditional tool validation, lifecycle events, and integration with external systems.

**Supported hook events:**

| Event | When it fires | Input | Use case |
|-------|---------------|-------|----------|
| `PreToolUse` | Before tool execution | Tool name | Validate before execution |
| `PostToolUse` | After tool execution | Tool name | Run linters, formatters |
| `Stop` | When subagent finishes | (none) | Cleanup operations |

**Format:**

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
  Stop:
    - type: command
      command: "./scripts/cleanup.sh"
```

**Matcher syntax:**
- Single tool: `"Bash"`, `"Edit"`
- Multiple tools: `"Edit|Write"`, `"Read|Grep|Glob"`
- Wildcard: Not supported; list explicitly

**Examples:**

```yaml
# Validate SQL queries before execution
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"

# Run linter after code edits
hooks:
  PostToolUse:
    - matcher: "Edit"
      hooks:
        - type: command
          command: "eslint --fix"

# Cleanup database connection
hooks:
  Stop:
    - type: command
      command: "./scripts/cleanup-db.sh"
```

For detailed hook implementation, see `advanced-patterns.md` and `tool-scoping.md`.

**Plugin-agent constraint:** see the note under `permissionMode` above — `hooks` is accepted by this schema but not honored for plugin-scoped agents.

### `maxTurns`

**Optional.** Caps the number of agentic turns the subagent may take before it is stopped.

```yaml
maxTurns: 20
```

### `mcpServers`

**Optional.** Restricts or configures which MCP servers are available to the subagent. Not honored for plugin-scoped agents (see `permissionMode` note above).

### `memory`

**Optional.** Controls the subagent's memory scope. Valid values: `user`, `project`, `local`.

```yaml
memory: project
```

### `background`

**Optional.** Boolean. When `true`, hints that the subagent is intended for background/unattended execution.

### `effort`

**Optional.** Reasoning effort level for the subagent's model, where supported.

### `isolation`

**Optional.** Execution isolation mode. Valid value: `worktree` — runs the subagent in an isolated git worktree, giving it complete filesystem isolation on a fresh branch. The worktree auto-cleans if the agent makes no changes.

```yaml
isolation: worktree
```

**When to use:** multiple agents editing the same codebase in parallel where file conflicts are likely, or a competitive-implementation pattern (dispatch N agents at the same task, pick the best result).

**This is agent-level isolation — declared once in frontmatter, applied on every invocation of that agent.** It's a separate mechanism from **session-level** worktree isolation, which is requested ad hoc in natural language for the current session rather than declared on a specific agent:

```
"work in a worktree"
"start a worktree for this bug fix"
```

Session-level requests use the same underlying git-worktree isolation but apply to the whole session's work, not to a single agent dispatch — use `isolation: worktree` in an agent's frontmatter when the isolation need is intrinsic to that agent's role (e.g. a parallel-implementation agent), and a session-level request when the isolation need is specific to the current task rather than the agent's general design.

### `initialPrompt`

**Optional.** Seeds the subagent's first turn with a specific prompt, distinct from the system prompt.

### `prompt` (CLI/SDK-defined agents only)

**Not applicable to file-based agents.** For file-based agent files (`agents/*.md`), the Markdown body below the frontmatter IS the system prompt — do not add a `prompt` field to file-based agent frontmatter. `prompt` is only used when defining agents programmatically via the CLI or SDK, where there is no Markdown body to source it from.

## Field Combinations & Constraints

### Valid Combinations

```yaml
# Minimal (most permissive)
---
name: basic-agent
description: Does basic tasks
color: blue
---

# Tool-restricted, read-only
---
name: analyzer
description: Analyzes code
tools: Read, Grep, Glob
permissionMode: plan
model: haiku
color: blue
---

# Trusted editor
---
name: code-fixer
description: Fixes bugs
tools: Read, Edit, Write, Bash
permissionMode: acceptEdits
model: sonnet
color: blue
---

# Validated database access
---
name: db-reader
description: Read-only queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./validate-query.sh"
color: blue
---
```

### Invalid Combinations

```yaml
# ❌ Invalid tool name (case-sensitive)
tools: read, write, edit         # Should be: Read, Write, Edit

# ❌ Conflicting modes (if parent uses bypassPermissions)
permissionMode: plan             # Cannot override parent bypass

# ❌ Inconsistent constraints
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Edit"            # Edit not in tools list
      hooks: [...]
# This is OK actually (hook won't apply but no error)

# ❌ Invalid field names
permssion_mode: default          # Typo in field name
toolss: Read                     # Typo in field name
```

## Complete Example

```yaml
---
name: data-analyst
description: >-
  Execute read-only SQL queries to analyze data. Use when analyzing data
  patterns, generating reports, or exploring table structure. SELECT
  queries only; write operations blocked.
model: opus
tools: Bash, Read, Write
permissionMode: dontAsk
skills: data-analysis-standards
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-query.sh"
color: blue
---

You are a data analyst specializing in SQL analysis...

## When to invoke

Use when analyzing data patterns, generating reports, or exploring table structure — SELECT-only, write operations blocked.
```

## Validation Checklist

Before deploying, verify:

- [ ] `name` is lowercase-hyphen, ≤64 chars, unique
- [ ] `description` includes 3+ trigger phrases, ≤1024 chars
- [ ] `model` is sonnet/opus/haiku/fable/inherit/full model ID (or omitted)
- [ ] `color` (if present) is one of: red/blue/green/yellow/purple/orange/pink/cyan
- [ ] `tools` uses exact tool names (Read, Write, Edit, Bash, Grep, Glob, etc.)
- [ ] `permissionMode` is valid: default/manual/acceptEdits/dontAsk/auto/bypassPermissions/plan
- [ ] `hooks` matchers use exact tool names
- [ ] YAML syntax is valid (proper indentation, no typos in field names)
- [ ] File has frontmatter delimiters (`---` before and after)
- [ ] System prompt (body) follows frontmatter

See `validation.md` for full validation process.

## Scope Storage

Where to store subagent files (determines visibility):

| Location | Scope | Priority |
|----------|-------|----------|
| `.claude/agents/` | Current project | High (2) |
| `~/.claude/agents/` | All projects | Medium (3) |
| `--agents` CLI | Current session | Highest (1) |
| Plugin `agents/` | Where plugin installed | Low (4) |

When multiple subagents share the same name, higher priority location wins.

## Troubleshooting Configuration

### Subagent doesn't load
- Check YAML syntax (indentation, `---` delimiters)
- Verify `name` is lowercase-hyphen
- Ensure file is in correct directory

### Subagent doesn't delegate
- Check `description` for vague language
- Add 3+ specific trigger phrases to description
- Review `delegation.md` for better descriptions

### Tool access denied
- Verify tool is in `tools` list (case-sensitive)
- Check `disallowedTools` isn't blocking it
- Verify tool name is exact (Read, not read)

### Permissions prompting unexpectedly
- Check `permissionMode` setting
- Verify parent conversation permission context
- Use `permissionMode: dontAsk` for background execution

### Hooks not triggering
- Verify hook script is executable
- Check hook `matcher` uses exact tool names (case-sensitive)
- Ensure hook `command` path is correct

## Next Steps

- **Writing descriptions:** See `delegation.md`
- **Permission mode details:** See `permission-modes.md`
- **Tool access patterns:** See `tool-scoping.md`
- **Advanced hooks:** See `advanced-patterns.md`
- **Validation workflow:** See `validation.md`
