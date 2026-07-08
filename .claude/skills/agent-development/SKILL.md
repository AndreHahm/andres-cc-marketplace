---
name: agent-development
description: >-
  Creates, validates, and refines Claude Code plugin agents — covering frontmatter,
  system prompts, triggering conditions, tool scoping, permission modes, and hooks.
  Use when the user asks to create, build, develop, write, validate, or improve
  a plugin agent or agent file.
allowed-tools: Read Grep Glob Bash
---

# Agent Development for Claude Code Plugins

Agents are autonomous subprocesses with their own isolated context window that handle complex, multi-step tasks independently.

| Concept | Agent | Command |
|---------|-------|---------|
| **Trigger** | Claude decides based on description | User invokes with `/name` |
| **Purpose** | Autonomous work | User-initiated actions |
| **Context** | Isolated subprocess | Shared conversation |
| **File** | `agents/*.md` | `commands/*.md` |

## When to Use

- User asks to **create**, **write**, or **develop** a new agent for a plugin
- User asks to **validate**, **improve**, or **refine** an existing agent file
- User describes a task they want to automate with an autonomous agent
- User needs help with agent system prompts, trigger descriptions, or tool scoping

## When NOT to Use

- Creating a **skill** (slash command-like tools) → use `skill-development` instead
- Creating a **slash command** → use `command-development` instead
- Creating a **hook** (lifecycle automation) → use `hook-development` instead
- Running **plugin compliance checks** → use `plugin-rulebook` instead

## Quick Start

Before creating a new agent, confirm no built-in agent type (`Explore`, `Plan`, `general-purpose`) already meets the need.

Create a minimal agent in 5 steps:

1. Create `agents/agent-name.md`
2. Add frontmatter: `name`, `description`, `model: inherit`, `color: blue`
3. Write a one-sentence description: `Use this agent when [condition]. Typical triggers include [A], [B], and [C].`
4. Write the body: start with `You are [role]...` then add responsibilities, process steps, and output format
5. Add `## When to invoke` with 2–4 prose trigger scenarios

Validate: `scripts/validate-agent.sh agents/your-agent.md`

## Agent File Structure

See the full file template in [`references/templates.md`](references/templates.md) → **Plugin Agent Template**. Every agent file contains YAML frontmatter (`name`, `description`, `model`, `color`, optional `tools` / `permissionMode` / `hooks`) followed by a system prompt body opening with `You are [role]...` and a `## When to invoke` section with 2–4 prose trigger scenarios.

## Frontmatter Fields

This section covers the core fields. Modern optional fields (`disallowedTools`, `maxTurns`, `skills`, `mcpServers`, `memory`, `background`, `effort`, `isolation`, `initialPrompt`) are documented in full in [`references/configuration-reference.md`](references/configuration-reference.md).

### name (required)

**Format:** lowercase, numbers, hyphens · 3–50 characters · start and end with alphanumeric

| Valid | Invalid | Reason |
|-------|---------|--------|
| `code-reviewer` | `helper` | Too generic |
| `test-generator` | `-agent-` | Starts/ends with hyphen |
| `api-docs-writer` | `my_agent` | Underscores not allowed |
| `security-analyzer` | `ag` | Too short (< 3 chars) |
| `pr-quality-reviewer` | `MyAgent` | Uppercase not allowed |

### description (required)

**The most critical field** — loaded into parent context whenever the agent is registered so the harness can decide when to dispatch.

**Default Agent Standards:**

- Keep to **one sentence** — descriptions load into parent context; every token counts.
- **Do NOT add verbose `<example>` blocks** in description — they waste context tokens.
- Put detailed trigger scenarios in the agent body under a **`## When to invoke`** section as prose bullets (2–4 scenarios).

**Format:** `Use this agent when [conditions]. Typical triggers include [scenario 1] and [scenario 2].`

**Best practices:** Cover both proactive (assistant invokes itself) and reactive (user requests) triggering. Be specific about when NOT to use the agent.

### model (required)

| Value | Use Case |
|-------|----------|
| `inherit` | Same model as parent — recommended default |
| `haiku` | Fast, simple tasks |
| `sonnet` | Balanced performance |
| `opus` | Complex reasoning, maximum capability |
| `fable` | Additional selectable model |

Full model ID strings (e.g. `claude-sonnet-4-5`) are also accepted. Use `inherit` unless the agent requires specific model capabilities.

**Isolation vs. model choice:** for review, analysis, and exploration agents that must not pollute the main context window, rely on the agent's own isolated execution context to get that separation, not on model choice. Choose an explicit model only when the task has a clear capability, cost, or latency requirement — `inherit` is the official default and is never an anti-pattern.

### color (required)

**Values:** `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan` (`magenta` is deprecated — no longer listed in current platform docs; treat as non-standard, not invalid)

**Convention:** Blue/cyan = analysis/review · Green = success tasks · Yellow = validation · Red = critical/security · Purple/orange/pink = uncategorized/available for project-specific use. Use distinct colors for different agents in the same plugin.

### tools (optional)

Restrict to minimum needed (principle of least privilege). Default: all tools.

```yaml
tools: ["Read", "Grep", "Glob"]          # Read-only analysis
tools: ["Read", "Write", "Grep"]         # Code modification
tools: ["Read", "Bash", "Grep"]          # System operations
```

Read-only reviewer/analysis agents must not receive `Bash`, `Write`, or `Edit` — restrict to `Read`, `Grep`, `Glob` unless there is a specific, justified need.

`AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, and `WaitForMcpServers` are never available to subagents even if listed in `tools`; `ExitPlanMode` is also unavailable unless the subagent runs with `permissionMode: plan`. When both `tools` and `disallowedTools` are set, `disallowedTools` is applied first — a tool listed in both is removed. See `references/tool-scoping.md` for the full reference.

### permissionMode (optional)

Controls how the agent handles permission prompts. Default: `default`.

Values: `default` (prompt each time) · `acceptEdits` (auto-accept file edits) · `dontAsk` (auto-deny prompts, for background) · `bypassPermissions` (skip all checks) · `plan` (read-only mode). `manual` is an alias for `default` (Claude Code v2.1.200+).

See `references/permission-modes.md` for decision matrices and use-case matching.

### hooks (optional)

Lifecycle hooks: `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`. See `references/configuration-reference.md` for syntax and `references/advanced-patterns.md` for production patterns.

Plugin agents must not rely on `hooks`, `mcpServers`, or `permissionMode` — these fields are accepted by the schema but are not honored for plugin-scoped agents.

### skills (optional)

Preloads skill content into the agent's context at startup. This does **not** restrict which skills the agent can invoke — to prevent invocation, remove `Skill` from `tools` or add it to `disallowedTools`. See `references/configuration-reference.md`.

## System Prompt Design

The markdown body becomes the agent's system prompt. Write in second person, addressing the agent directly.

### Required Agent Sections (in order)

1. **Title** — `# <Role Title>` with strong identity statement
2. **Identity** — Quality expectations and motivation (consequences for poor work)
3. **Goal** — Clear single-paragraph objective
4. **Input** — What files/data the agent receives
5. **Load Context** — Explicit requirement to read ALL relevant files BEFORE analysis
6. **Process/Stages** — Step-by-step workflow

**Recommended baseline ordering:** Role → Process → Output Format. Use this simpler ordering when the full six-part structure above isn't needed — see `references/system-prompt-design.md`.

Agents that act as a pass/fail gate for another skill or workflow should emit structured YAML for programmatic consumption: `{pass: bool, issues: [...]}`.

### Process Stage Ordering

Self-critique always comes last. Always produce the full solution first, then evaluate.

```text
WRONG: Decompose → Self-Critique → Produce → Solve
RIGHT: Decompose → Solve → Produce Full Solution → Self-Critique → Output
```

### Decision Tables

Put the reasoning column **before** the decision column — forces the agent to explain why before committing.

```text
WRONG: | Section | Include? | Reasoning |
RIGHT: | Section | Reasoning | Include? |
```

**DO:** Write in second person · Be specific and actionable · Define output format · Address edge cases · Keep under 10,000 characters · Encourage parallel tool calls (e.g., "when reading N files, issue N Read calls in a single response")

**DON'T:** Write in first person · Be vague · Omit process steps · Leave output format undefined

See `references/system-prompt-design.md` for complete patterns and examples.

## Triggering Patterns

Agents trigger in four ways:

- **Explicit request** — user directly asks for the agent's function
- **Implicit need** — agent triggered by context, not an explicit request
- **Proactive trigger** — agent fires after completing relevant work without being asked
- **Tool usage pattern** — agent triggers based on what tools were used in the session

Write 2–4 trigger scenarios in the body's `## When to invoke` section to cover these axes. See `references/delegation.md` for description format, trigger phrase library, and debugging guidance.

## Agent Design Patterns

- **One agent, one job.** An agent's purpose should be describable in a single sentence; split multi-purpose agents into focused ones.
- **Fan-out (parallel) agents** must use a fixed-key, machine-mergeable output schema and avoid `Write`/`Edit`/`Bash` side effects.
- **Independent reviewer agents** running in parallel should state in the system prompt that they are one of several reviewers, to prevent inappropriate coordination assumptions.
- **Orchestrator agents** that dispatch other agents must declare the `Agent` tool and document which sub-agents they may dispatch.
- **Nested dispatch:** subagents may spawn further nested subagents if granted the `Agent` tool (fixed depth limit: 5 levels). `Agent(agent_type)` allowlists only filter nested spawning in main-thread agents — in a subagent definition, listing `Agent` permits all nested agent types.
- **Context isolation:** a regular subagent starts with an empty context window — no conversation history, invoked skills, or previously read files. Pass all required context explicitly; forked agents are the exception.
- Optional heuristic (not a hard rule): orchestrator agents → `haiku` (cost), implementer agents → `sonnet` (balance), quality-gate/advisor agents → `opus`.

See `references/advanced-patterns.md`, `references/delegation.md`, and `references/how-subagents-work.md` for full patterns and examples.

## Creating Agents

### Elite Agent Architect Process

1. **Extract Core Intent** — Identify fundamental purpose, key responsibilities, success criteria
2. **Design Expert Persona** — Create compelling expert identity with domain knowledge
3. **Architect Comprehensive Instructions** — Behavioral boundaries, methodologies, edge cases, output formats
4. **Optimize for Performance** — Decision frameworks, quality control, workflow patterns, fallback strategies
5. **Create Identifier** — Concise, descriptive, 2–4 words with hyphens (3–50 chars)
6. **Generate "When to Invoke" Examples** — 2–4 prose trigger scenarios for the body section

### Method 1: AI-Assisted Generation

Use the template at [`references/agent-creation-prompt-template.md`](references/agent-creation-prompt-template.md) with an AI assistant to generate agent configuration. The template instructs the AI to extract intent, design a persona, and return a JSON structure with `identifier`, `whenToUse`, and `systemPrompt` fields. See `references/agent-creation-system-prompt.md` for the exact Claude Code generation prompt.

### Method 2: Manual Creation

1. Choose identifier (3–50 chars, lowercase, hyphens)
2. Write one-sentence description with triggering conditions
3. Select model (`inherit` unless specific capability needed)
4. Choose color (distinct within the plugin)
5. Define tools (minimum needed)
6. Write system prompt following Required Agent Sections order
7. Add `## When to invoke` with 2–4 prose trigger scenarios
8. Save as `agents/agent-name.md`
9. Validate with `scripts/validate-agent.sh`
10. Test with real trigger scenarios

## Validation Rules

| Component | Rule | Valid | Invalid |
|-----------|------|-------|---------|
| Name | 3–50 chars, lowercase, hyphens | `code-reviewer` | `Code_Reviewer`, `ag` |
| Description | 10–5,000 chars · one sentence · starts "Use this agent when..." | correct | verbose list of phrases |
| Model | `inherit`, `sonnet`, `opus`, `haiku`, `fable`, or a full model ID string | `inherit` | `gpt-4` |
| Color | one of 8 allowed values (`magenta` deprecated) | `blue` | `teal` |
| System prompt | 20–10,000 chars (ideal: 500–3,000) | structured prompt | empty body |
| `<example>` in description | Avoid — use body "When to invoke" section instead | — | verbose blocks in frontmatter |

Run `scripts/validate-agent.sh agents/your-agent.md` to validate.

## Agent Organization

```
plugin-name/
└── agents/
    ├── analyzer.md
    ├── reviewer.md
    └── generator.md
```

All `.md` files in `agents/` are auto-discovered. Namespacing: single plugin → `agent-name`; subdirectories → `plugin:subdir:agent-name`.

After creating the first agent file in a new `agents/` directory, restart Claude Code — subsequent edits are picked up automatically unless the session was started with `--disable-slash-commands`.

**Scope:** Always work within the project directory. Never edit `~/.claude/agents/` (user-space) — those agents affect all Claude Code projects globally.

## Testing

1. Write the agent with specific trigger conditions in the "When to invoke" section
2. Use similar phrasing in test prompts to verify the agent fires correctly
3. Confirm the agent follows its process steps
4. Verify output format matches the specification
5. Test edge cases from the system prompt

## Validate & Refine

Run the 7-phase validation workflow (configuration → delegation signal → prompt quality → tool scoping → permission mode → hooks → real-world testing) from `references/validation.md`. The sign-off checklist is included at the end of that file.

If delegation doesn't fire, the description needs clearer trigger phrases — see `references/delegation.md` for the trigger phrase library and debugging guide.

Before finalizing, invoke `plugin-rulebook` to verify naming, tool-scoping, and formatting compliance.

## Quick Reference

### Minimal Agent

```markdown
---
name: simple-agent
description: Use this agent when [condition]. Typical triggers include [trigger 1] and [trigger 2].
model: inherit
color: blue
---
```

See [`references/templates.md`](references/templates.md) → **Plugin Agent Template** for the full version with body and trigger scenarios.

### Frontmatter Summary

| Field | Required | Format |
|-------|----------|--------|
| name | Yes | lowercase-hyphens, 3–50 chars |
| description | Yes | One sentence, "Use this agent when..." |
| model | Yes | `inherit` / `sonnet` / `opus` / `haiku` / `fable` / full model ID |
| color | Yes | `red` / `blue` / `green` / `yellow` / `purple` / `orange` / `pink` / `cyan` (`magenta` deprecated) |
| tools | No | Array of tool names (default: all) |

### Best Practices

**DO:** One-sentence description · Prose "When to invoke" body section (2–4 scenarios) · `inherit` model unless specific capability needed · Least-privilege tools · Required Agent Sections ordering · Self-critique last in multi-stage processes · Reasoning column before decision in tables

**DON'T:** Verbose `<example>` blocks in description · Generic triggering conditions · Same color for related agents · Unnecessary tool permissions · Vague system prompts · Skip testing

## Additional Resources

| Topic | File | Purpose |
|-------|------|---------|
| Trigger descriptions & delegation prompts | [`references/delegation.md`](references/delegation.md) | Description format, trigger phrase library, Agent() call patterns |
| Validation workflow & checklists | [`references/validation.md`](references/validation.md) | 7-phase validation with checklists and sign-off |
| System prompt patterns | [`references/system-prompt-design.md`](references/system-prompt-design.md) | Complete system prompt patterns and examples |
| Agent creation prompt | [`references/agent-creation-system-prompt.md`](references/agent-creation-system-prompt.md) | Exact AI-generation prompt from Claude Code |
| AI-assisted generation template | [`references/agent-creation-prompt-template.md`](references/agent-creation-prompt-template.md) | Step-by-step AI generation workflow with examples |
| Complete agent examples | [`references/complete-agent-examples.md`](references/complete-agent-examples.md) | Production-ready agents for common use cases |
| Validation script | [`scripts/validate-agent.sh`](scripts/validate-agent.sh) | Validate agent file structure |
| Trigger testing | [`scripts/test-agent-trigger.sh`](scripts/test-agent-trigger.sh) | Test agent triggering in real scenarios |
| Subagent architecture | [`references/how-subagents-work.md`](references/how-subagents-work.md) | Delegation mechanisms, execution models, hooks lifecycle |
| Templates | [`references/templates.md`](references/templates.md) | Copy-paste starting points for common agent types |
| Configuration reference | [`references/configuration-reference.md`](references/configuration-reference.md) | Complete YAML frontmatter field reference |
| Tool scoping | [`references/tool-scoping.md`](references/tool-scoping.md) | Allowlist/denylist patterns, principle of least privilege |
| Permission modes | [`references/permission-modes.md`](references/permission-modes.md) | Decision matrices for foreground vs background execution |
| Advanced patterns | [`references/advanced-patterns.md`](references/advanced-patterns.md) | Hook validation, chaining, background execution |
