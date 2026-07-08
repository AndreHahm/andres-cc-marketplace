---
name: command-development
description: >-
  Creates slash commands for Claude Code. Covers slash command structure, YAML
  frontmatter fields, $ARGUMENTS and positional args, bash execution, @file
  references, AskUserQuestion patterns, plugin features, and multi-step workflows.
  Use when creating slash commands, adding commands to a plugin, writing custom
  commands, defining command arguments, using command frontmatter, organizing
  commands, creating commands with file references, or writing interactive commands.
allowed-tools: Read Write Edit Glob Skill
---

# Command Development for Claude Code

> **Note:** `.claude/commands/` is a legacy format — still supported, but now functionally equivalent to skills, and both create slash-command entries. For all new plugin work, prefer `.claude/skills/<name>/SKILL.md`. Commands are user-triggered by typing `/command-name`; skills add Claude's context-matching activation on the description field on top of that same slash-command entry. See `skill-development` for the skill format.

## Quick Start

1. **Identify the category** — planning / implementation / analysis / workflow / utility
2. **Read existing commands** in the same category before writing a new one
3. **Choose location** — project (`.claude/commands/`), personal (`~/.claude/commands/`), or plugin (`commands/`)
4. **Write the body** as instructions FOR Claude (not a message to the user — see below)
5. **Add frontmatter** for tool restrictions, model selection, or argument hints
6. **Test** with `/command-name [args]`

## When NOT to Use

- **Building a skill** (SKILL.md format) — use `skill-development`; skills are activated by context-matching, not user-typed commands
- **Creating hooks** — use `hook-development`; hooks respond to events, not slash commands
- **Adding MCP servers** — use `mcp-integration`

## Commands are Instructions FOR Claude

**Write commands as directives to Claude, not descriptions for the user.**

```
✅ Review this code for SQL injection, XSS attacks, and authentication issues.
   Provide specific line numbers and severity ratings.

❌ This command will review your code for security issues.
   You'll receive a report with vulnerability details.
```

The first tells Claude what to do. The second tells the user what will happen — Claude won't execute it as a task.

## Command Locations

| Location | Path | Scope |
|----------|------|-------|
| **Project** | `.claude/commands/` | Current project, shared with team |
| **Personal** | `~/.claude/commands/` | All projects (user-only) |
| **Plugin** | `<plugin-name>/commands/` | Available when plugin installed |

Project commands take precedence over personal commands with the same name.

## File Format

Commands are `.md` files. No frontmatter is required for simple commands:

```markdown
Review this code for security vulnerabilities including SQL injection,
XSS attacks, and authentication bypass. Provide specific line numbers.
```

**Frontmatter must be the very first content** — no blank lines before `---`, one blank line after the closing `---` before the body:

```markdown
---
description: Review code for security issues
allowed-tools: Read, Grep, Bash(git:*)
---

Command body starts here.
```

## Frontmatter Fields

| Field | Purpose | Default |
|-------|---------|---------|
| `description` | Shown in `/help` — keep under 60 chars | First line of prompt |
| `allowed-tools` | Tools the command may use (`Read`, `Bash(git:*)`, `*`) | Inherits from conversation |
| `model` | Model override (`haiku`, `sonnet`, `opus`) | Inherits from conversation |
| `argument-hint` | Autocomplete hint (e.g. `[pr-number] [priority]`), 0-based order matching body usage — plugin-rulebook R22 | None |
| `disable-model-invocation` | Prevent programmatic invocation | `false` |

For full field specifications, syntax variants, and validation rules, see `references/frontmatter-reference.md`.

## Dynamic Arguments

### `\$ARGUMENTS` — all args as one string

```markdown
---
argument-hint: [issue-number]
---
Fix issue #\$ARGUMENTS following our coding standards.
```

`/fix-issue 123` → `Fix issue #123 following our coding standards.`

### Positional — `\$0`, `\$1`, `\$2` (0-based: `\$0` is the *first* argument)

```markdown
---
argument-hint: [pr-number] [priority] [assignee]
---
Review PR #\$0 with priority \$1. Assign to \$2 for follow-up.
```

`/review-pr 123 high alice` → `Review PR #123 with priority high. Assign to alice for follow-up.`

## File References

Use `@path` to inject file content before Claude processes the command:

```markdown
---
argument-hint: [file-path]
---
Review @\$0 for code quality and potential bugs.
```

`/review-file src/api/users.ts` — Claude reads the file first, then processes the command.

**Multiple files:** `Compare @src/old.js with @src/new.js for breaking changes.`

**Static files:** `Review @package.json and @tsconfig.json for build consistency.`

## Bash Execution

Commands can run bash inline to gather context before Claude processes the prompt:

```markdown
---
allowed-tools: Bash(git:*)
---
Files changed: !`git diff --name-only`

Review each changed file for code quality and test coverage.
```

Use `Bash(git:*)` not `Bash(*)` — scope as narrowly as possible. For complete bash syntax, patterns, and examples, see `references/plugin-features-reference.md`.

## Plugin Features

Plugin commands have access to `${CLAUDE_PLUGIN_ROOT}` — an env var resolving to the plugin's absolute installation path:

```markdown
---
allowed-tools: Bash(node:*)
---
Run analysis: !`node ${CLAUDE_PLUGIN_ROOT}/scripts/analyze.js \$0`
Load config: @${CLAUDE_PLUGIN_ROOT}/config/settings.json
```

Use `${CLAUDE_PLUGIN_ROOT}` for all plugin file references to keep commands portable across installations. For agent/skill/hook integration patterns and multi-component workflows, see `references/plugin-features-reference.md`.

## Command Organization

**Flat** (5–15 commands, no clear categories):
```
.claude/commands/
├── build.md / test.md / deploy.md / review.md
```

**Namespaced** (15+ commands, clear categories):
```
.claude/commands/
├── ci/build.md     # /build (project:ci)
├── ci/test.md      # /test (project:ci)
└── git/pr.md       # /pr (project:git)
```

Subdirectory names appear as namespace labels in `/help`.

## Best Practices

- **Single responsibility:** one command, one task
- **Verb-noun naming:** `review-pr`, `fix-issue`, `deploy-app`
- **Always add `argument-hint`** for commands that take arguments
- **Scope Bash access:** `Bash(git:*)` not `Bash(*)`
- **Validate early:** check required args and file existence before doing work
- **Confirm before destructive actions:** ask before irreversible operations
- **Avoid name collisions:** a plugin must not define a legacy command and a skill with the same effective slash-command name unless the duplication is intentional and documented
- **Output file policy:** commands that write output files must state an explicit update policy; the default is full regeneration from current sources on every invocation — append-only behavior requires an explicit statement in the command body
- **Skill/command distinction:** multi-step commands with descriptive bodies can be mistaken for skills and invoked via `Skill()` — which silently fails. Add an invocation note at the top of the body for any command complex enough to cause this confusion: `> **Invocation:** Run as /command-name in the Claude Code prompt. This command cannot be invoked via Skill() — it must be triggered as a slash command or followed manually.`
- **Thinking mode:** add a `Think step-by-step` instruction or `## Analysis` section header in the command body to trigger extended reasoning before Claude acts (e.g. `Think through all edge cases before making any changes.`)

For complete patterns, multi-step workflows, and templates, see `references/advanced-workflows.md`, `references/interactive-commands.md`, and `examples/`.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Command not appearing | `.md` extension? File in the right directory? Restart Claude Code. |
| Arguments not substituted | `\$1` / `\$ARGUMENTS` syntax correct? No extra spaces? |
| Bash not executing | `allowed-tools` includes `Bash`? Command valid in terminal? |
| File reference not working | `@` syntax correct? File path valid? `Read` in `allowed-tools`? |

## Testing & Validation

After writing or modifying a command:

1. **Invoke it** — run `/command-name` with typical arguments and observe behavior
2. **Argument substitution** — verify `\$1`, `\$2`, `\$ARGUMENTS` expand as expected
3. **File references** — confirm `@path` files are read before the prompt is processed
4. **Bash execution** — test inline bash snippets in the terminal before embedding them
5. **Tool scoping** — confirm `allowed-tools` contains only what the command actually uses

**Quality gates:**
- [ ] Command body gives Claude directives, not user-facing descriptions
- [ ] `argument-hint` documents every argument the command accepts, in the same order the body consumes them — remember `\$0` is the *first* argument, not `\$1` (see plugin-rulebook R22 for the full missing/stale/wrong-position check)
- [ ] `allowed-tools` is set and scoped as narrowly as possible
- [ ] Destructive operations request confirmation before executing
- [ ] Commands that write output files declare an explicit update policy (default: full regeneration)
- [ ] Multi-step commands include an invocation note clarifying they cannot be invoked via `Skill()`

## Reference Guide

| Resource | Contents |
|----------|---------|
| `references/frontmatter-reference.md` | Full field specs, syntax, edge cases |
| `references/plugin-features-reference.md` | `${CLAUDE_PLUGIN_ROOT}`, agent/skill/hook integration, bash patterns |
| `references/advanced-workflows.md` | Multi-step patterns, complex workflows |
| `references/interactive-commands.md` | `AskUserQuestion` patterns, user interaction |
| `references/testing-strategies.md` | Validation patterns, argument/file/resource checks |
| `references/documentation-patterns.md` | Documentation command patterns |
| `references/marketplace-considerations.md` | Publishing and distribution |
| `references/slash-command-template.md` | Ready-to-use command template |
| `examples/simple-commands.md` | 10 concrete simple command examples |
| `examples/plugin-commands.md` | 10 concrete plugin command examples |
| `plugin-rulebook` | Plugin-level rules — invoke before finalizing any command to check naming, language, formatting, tool-scoping, and external-reference compliance |
