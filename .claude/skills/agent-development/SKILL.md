---
name: agent-development
description: >-
  Creates, validates, and refines Claude Code plugin agents — covering frontmatter,
  system prompts, triggering conditions, tool scoping, permission modes, and hooks.
  Use when the user wants to understand agent structure, hand-author or edit an agent
  file's fields directly, or validate/refine an existing agent against the spec. For
  one-shot generation of a brand-new agent from a described need, use the agent-creator
  agent instead; for a structured quality review of an existing agent, use subagent-reviewer.
allowed-tools: Read Grep Glob Skill Bash(scripts/validate-agent.sh:*) Bash(scripts/test-agent-trigger.sh:*)
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
- Generating a complete new agent end-to-end from a description → use `agent-creator` instead
- Structured quality review of an existing agent (tool scoping, prompt quality, checklist compliance) → use `subagent-reviewer` instead

## Finding-ID Fix Mode

When invoked with a bounded finding-ID list (e.g. from `plugin-lifecycle-downstream`'s Phase
4/6/8), follow `plugin-rulebook/references/finding-id-fix-contract.md` instead of this
skill's normal open-ended workflow: touch only the named findings' files, report per-ID
`applied`/`deferred`/`failed` status, and never mark a fix verified — that stays the
originating checker's job.

## Quick Start

Before creating a new agent, confirm no built-in agent type (`Explore`, `Plan`, `general-purpose`) already meets the need.

Create a minimal agent in 5 steps:

1. Create `agents/agent-name.md`
2. Add frontmatter: `name`, `description`, `model: inherit`, `color: blue`, `tools` (default `Read, Grep, Glob` — least privilege; widen only if the agent's process genuinely needs more)
3. Write a one-sentence description: `Use this agent when [condition]. Typical triggers include [A], [B], and [C].`
4. Write the body: start with `You are [role]...` then add responsibilities, process steps, and output format
5. Add `## When to invoke` with 2–4 prose trigger scenarios

Validate: `scripts/validate-agent.sh agents/your-agent.md`

## Agent File Structure

See the full file template in [`references/templates.md`](references/templates.md) → **Plugin Agent Template**. Every agent file contains YAML frontmatter (`name`, `description`, `model`, `color`, optional `tools` / `permissionMode` / `hooks`) followed by a system prompt body opening with `You are [role]...` and a `## When to invoke` section with 2–4 prose trigger scenarios.

## Frontmatter Fields

This section covers the core fields. Modern optional fields (`disallowedTools`, `maxTurns`, `skills`, `mcpServers`, `memory`, `background`, `effort`, `isolation`, `initialPrompt`) are documented in full in [`references/configuration-reference.md`](references/configuration-reference.md).

### name (required)

**Format:** lowercase, numbers, hyphens · 3–64 characters · start and end with alphanumeric

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

Values: `default` (prompt each time) · `acceptEdits` (auto-accept file edits) · `auto` (background classifier reviews commands and protected-directory writes, for unattended execution) · `dontAsk` (auto-deny prompts, for background) · `bypassPermissions` (skip all checks) · `plan` (read-only mode). `manual` is an alias for `default` (Claude Code v2.1.200+).

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

**Structured Output Mode recommendation:** when designing an agent whose job is to deliver findings/results back to a caller (a reviewer, validator, or any agent another skill or agent might parse programmatically), ask the user via `AskUserQuestion` — "Will this agent's output be parsed programmatically by another skill or agent, or only read by a person?" — rather than deciding unilaterally. If yes, add an optional, orthogonal **Structured Output Mode**: the agent's default output stays a human-readable narrative report, and a separate invocation-mode flag (`--yaml`/"structured output"/"machine-readable") switches to YAML-only output for that one invocation — see `plugins/plugin-devkit/agents/skill-reviewer.md` or `plugins/plugin-devkit/agents/rule-reviewer.md` for worked examples, and load the shared `action` enum from `plugin-rulebook/assets/settings.json → structured_output.action_enum` rather than hardcoding a new one (extend it per-agent under `structured_output.per_agent_extensions` only if the agent's domain genuinely needs an action value the shared list doesn't cover). Do not add a Structured Output Mode speculatively — if the caller's need is unconfirmed, ship without one and add it later once an actual consumer exists (this project's own precedent: `skill-reviewer` and `subagent-reviewer` got theirs only after a caller was confirmed via research, not by default).

**Delta Mode recommendation:** when designing an agent whose default Process reads or re-verifies a whole component, a whole plugin, or a set of multiple components as its normal invocation scope (a "whole-surface" reviewer, as opposed to a narrowly-scoped single-check agent), ask the user via `AskUserQuestion` — "Will this agent often be asked about just one specific, already-known change, rather than a full sweep every time?" — rather than deciding unilaterally. If yes, add an optional, orthogonal **Delta mode** (`--delta`, or the caller names the specific fact/section/edge that changed): skip the agent's most expensive step(s) and check only the named thing instead of re-verifying the whole scope, stating plainly in the report header what was skipped — see `plugins/plugin-devkit/agents/permission-reviewer.md` or `plugins/plugin-devkit/agents/consistency-reviewer.md` for worked examples. This exists because a whole-surface reviewer with no cheaper path costs the same whether the actual question is "did this two-line diff need anything" or "audit everything" — `permission-reviewer`'s own missing Delta mode once cost ~70k tokens answering the former. Do not add a Delta mode speculatively — if the agent's typical invocation is already narrowly scoped (a single named target, not a whole plugin/set), there's nothing further to cut and it isn't needed.

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
- **Never ask a subagent to verify something it can't access.** A dispatch prompt must not say "confirm this yourself against X" or "double-check the conversation" when the subagent has no tool access to X (no `Bash`, no transcript path, no memory of the parent conversation). Resolve the ambiguous or uncertain fact in the calling context first and hand the subagent a flat, resolved statement instead. A real instance: a same-day dispatch to `build-handoff-writer` (whose own tools are `Read`-only) asked it to "confirm this yourself against the conversation context" — a fact it structurally could not check — and that dispatch cost roughly 3x the wall-clock time of a comparable one for a similar token count.
- **Checkpoint large, precisely-itemized batch edits — don't dispatch them as one uninterrupted unit.** A single dispatch applying many independent edits across many files has no visible progress marker if it fails partway through (a session-limit error, a tool rejection) — the calling context is left needing a full `git diff` audit just to determine what actually landed before it can safely proceed or retry. For a batch above roughly 5-6 edits or files, either split it into 2-3 smaller sub-dispatches with a real handoff point between them, or instruct the agent to explicitly announce each numbered edit's start/completion as it works, so a mid-run failure's blast radius is immediately knowable without forensic file inspection. A real instance: a 9-edit-across-8-files single dispatch failed mid-verification with a session-limit error; all 9 edits had in fact landed correctly, but confirming that required a full `git diff` review rather than reading the agent's own progress trail, because none existed.
- Optional heuristic (not a hard rule): orchestrator agents → `haiku` (cost), implementer agents → `sonnet` (balance), quality-gate/advisor agents → `opus`.

See `references/advanced-patterns.md`, `references/delegation.md`, and `references/how-subagents-work.md` for full patterns and examples.

## Creating Agents

### Elite Agent Architect Process

1. **Extract Core Intent** — Identify fundamental purpose, key responsibilities, success criteria
2. **Design Expert Persona** — Create compelling expert identity with domain knowledge
3. **Architect Comprehensive Instructions** — Behavioral boundaries, methodologies, edge cases, output formats
4. **Optimize for Performance** — Decision frameworks, quality control, workflow patterns, fallback strategies
5. **Create Identifier** — Concise, descriptive, 2–4 words with hyphens (3–64 chars)
6. **Generate "When to Invoke" Examples** — 2–4 prose trigger scenarios for the body section

### Method 1: AI-Assisted Generation

Use the template at [`references/agent-creation-prompt-template.md`](references/agent-creation-prompt-template.md) with an AI assistant to generate agent configuration. The template instructs the AI to extract intent, design a persona, and return a JSON structure with `identifier`, `whenToUse`, and `systemPrompt` fields. See `references/agent-creation-system-prompt.md` for the exact Claude Code generation prompt.

### Method 2: Manual Creation

1. Choose identifier (3–64 chars, lowercase, hyphens)
2. Write one-sentence description with triggering conditions
3. Select model (`inherit` unless specific capability needed)
4. Choose color (distinct within the plugin)
5. Define tools (minimum needed)
6. Write system prompt following Required Agent Sections order
7. If the agent delivers findings/results to a caller, ask via `AskUserQuestion` whether a Structured Output Mode is needed now (see "Structured Output Mode recommendation" above) — don't add one speculatively
8. If the agent's default scope is a whole component/plugin/set rather than a single narrowly-named target, ask via `AskUserQuestion` whether a Delta mode is needed now (see "Delta Mode recommendation" above) — don't add one speculatively
9. Add `## When to invoke` with 2–4 prose trigger scenarios
10. Save as `agents/agent-name.md`
11. Validate with `scripts/validate-agent.sh`
12. Test with real trigger scenarios

## Validation Rules

| Component | Rule | Valid | Invalid |
|-----------|------|-------|---------|
| Name | 3–64 chars, lowercase, hyphens | `code-reviewer` | `Code_Reviewer`, `ag` |
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

**Data-dependency timing check:** when a new step reads data another step is supposed to have produced (a prior-run marker, a lookup result from an earlier phase), confirm that data actually exists at the point in execution order it's read — not just that the reference is written correctly. Two sibling command files in this plugin (`verify-dev-rules.md`, `update-dev-rule.md`) each shipped a new "intentional divergence carry-forward" step that referenced prior-run data a *later* step actually loaded, making the new step dead code on a first pass through the document. The bug shape recurring in two independently-written files is the signal to check for this generically, not just fix it once.

Before finalizing, invoke `plugin-rulebook` to verify naming, tool-scoping, and formatting compliance.

## Quick Reference

### Minimal Agent

```markdown
---
name: simple-agent
description: Use this agent when [condition]. Typical triggers include [trigger 1] and [trigger 2].
model: inherit
color: blue
tools: ["Read", "Grep", "Glob"]
---
```

See [`references/templates.md`](references/templates.md) → **Plugin Agent Template** for the full version with body and trigger scenarios.

### Frontmatter Summary

| Field | Required | Format |
|-------|----------|--------|
| name | Yes | lowercase-hyphens, 3–64 chars |
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
| Structural smoke test | [`scripts/smoke_test.py`](scripts/smoke_test.py) | Frontmatter validity, Bash-grant usage, referenced-file existence, frontmatter-field documentation cross-check |
| Subagent architecture | [`references/how-subagents-work.md`](references/how-subagents-work.md) | Delegation mechanisms, execution models, hooks lifecycle |
| Templates | [`references/templates.md`](references/templates.md) | Copy-paste starting points for common agent types |
| Configuration reference | [`references/configuration-reference.md`](references/configuration-reference.md) | Complete YAML frontmatter field reference |
| Tool scoping | [`references/tool-scoping.md`](references/tool-scoping.md) | Allowlist/denylist patterns, principle of least privilege |
| Permission modes | [`references/permission-modes.md`](references/permission-modes.md) | Decision matrices for foreground vs background execution |
| Advanced patterns | [`references/advanced-patterns.md`](references/advanced-patterns.md) | Hook validation, chaining, background execution |
| Agent Teams (experimental) | [`references/agent-teams.md`](references/agent-teams.md) | When multi-session peer-to-peer collaboration fits better than a subagent |
