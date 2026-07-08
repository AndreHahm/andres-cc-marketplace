# Plugin Development Toolkit

A comprehensive toolkit for developing Claude Code plugins — skills for building agents, commands, hooks, MCP integrations, rule pipelines, and full plugin structure guidance, plus reviewer agents that check the components you build against the plugin's own rulebook.

## Overview

`plugin-dev` ships **21 skills**, **13 agents**, **14 commands**, and a `Stop`/`PostToolUse` hook pair. Skills fall into four broad groups:

| Group | Skills |
|---|---|
| **Component authoring** | `agent-development`, `command-development`, `hook-development`, `skill-development`, `workflow-skill-development`, `mcp-integration` |
| **Plugin structure & governance** | `plugin-development`, `plugin-rulebook`, `plugin-settings`, `plugin-evaluation`, `marketplace-development` |
| **Skill quality & lifecycle** | `skill-refiner-interactive`, `skill-improver-loop`, `skill-tester`, `skill-security`, `skill-stocktake` |
| **`.claude/rules/` pipeline** | `rule-development`, `rules-extract`, `rules-merge`, `rules-apply`, `rules-review` |

Each skill follows progressive disclosure: a lean `SKILL.md`, detailed `references/`, working `examples/`, and utility `scripts/` where relevant.

## Installation

```bash
/plugin install plugin-dev@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/plugin-dev
```

## Skills

### Component Authoring

| Skill | Use when |
|---|---|
| `agent-development` | Creating or validating a plugin agent file — frontmatter, system prompt, tool scoping, triggers |
| `command-development` | Creating a slash command — frontmatter fields, arguments, bash execution, file references |
| `hook-development` | Adding a hook — any event, any hook type (command/prompt/agent/http/mcp_tool), validation |
| `skill-development` | Creating, testing, evaluating, repairing, or consolidating a skill |
| `workflow-skill-development` | Building a multi-phase skill with sub-agent orchestration or decision trees |
| `mcp-integration` | Wiring an MCP server (stdio/SSE/HTTP/WebSocket) into a plugin |

### Plugin Structure & Governance

| Skill | Use when |
|---|---|
| `plugin-development` | Creating, converting, or publishing a plugin end-to-end (delegates component work to the skills above) |
| `plugin-rulebook` | Checking naming, language, formatting, and tool-scoping compliance on any component |
| `plugin-settings` | Adding per-project configuration via `.claude/plugin-name.local.md` |
| `plugin-evaluation` | Designing a rubric or LLM-judge methodology to evaluate agents/commands |
| `marketplace-development` | Converting a skills-only repo (no `plugin.json`) into a publishable marketplace |

### Skill Quality & Lifecycle

| Skill | Use when |
|---|---|
| `skill-refiner-interactive` | Interactively refining an existing skill for clarity, token efficiency, production readiness |
| `skill-improver-loop` | Running automated fix-review cycles on a skill until it clears `skill-reviewer` |
| `skill-tester` | Empirically benchmarking a skill against a baseline (timing, token metrics) |
| `skill-security` | Auditing a skill for permission risk, prompt injection, or PII leakage |
| `skill-stocktake` | Auditing all skills/commands in a project for quality, staleness, and overlap |

### `.claude/rules/` Pipeline

| Skill | Use when |
|---|---|
| `rule-development` | Writing or validating a single `.claude/rules/` file with contrastive examples |
| `rules-extract` | Mining a codebase, PR, or conversation for project-specific rules |
| `rules-merge` | Consolidating extracted rules from multiple repos into a shared, portable set |
| `rules-apply` | Applying merged org-wide rules to a project and cleaning up local overrides |
| `rules-review` | Checking a diff's changed files against applicable rules |

## Agents

Thirteen specialized agents, eleven of which are quality-gate reviewers cross-checked by `plugin-validator`:

| Agent | Purpose |
|---|---|
| `plugin-validator` | Validates overall plugin structure, manifest, and component wiring |
| `skill-reviewer` | Reviews skill files for structure and best-practice adherence |
| `hook-reviewer` | Reviews hook configurations for safety and correctness before deployment |
| `rule-reviewer` | Reviews `.claude/rules/` files before they load into every session |
| `subagent-reviewer` | Reviews agent/subagent definition files for quality before deployment |
| `command-reviewer` | Reviews slash-command files for quality and best-practice compliance |
| `claudemd-reviewer` | Reviews CLAUDE.md files for budget, separation of concerns, and actionability |
| `language-reviewer` | Reviews a plugin and its surrounding project for English-language and Unicode-integrity compliance |
| `external-references-reviewer` | Detects and classifies references to external companies, orgs, and repos |
| `consistency-reviewer` | Reviews data, governance, functionality, and capability consistency across related components |
| `completeness-reviewer` | Finds open items, missing documentation, missing test/eval evidence, and stale claims |
| `scripts-reviewer` | Reviews shell/Python scripts for correctness bugs and code smells |
| `agent-creator` | Generates new agent configurations from a described need |

## Commands

**Plugin/skill workflow:**

| Command | Purpose |
|---|---|
| `/create-plugin` | Guided end-to-end workflow: design, build, and validate a new plugin |
| `/create-command` | Scaffold a new slash command with full feature support |
| `/skill-improver` | Iteratively review and fix a skill until it passes quality standards |
| `/cancel-skill-improver` | Stop an in-progress skill-improvement loop, keeping changes made so far |

**Rules pipeline:**

| Command | Purpose |
|---|---|
| `/extract-rules` | Extract project rules from a codebase, PRs, or conversation |
| `/merge-rules` | Merge multiple projects' extracted rules into one portable set |
| `/apply-rules` | Apply merged org-wide rules to the current project |
| `/review-rules` | Check a diff's changed files against applicable rules |

**Dev-rules reporting** (plugin-dev's own internal rule tracking):

| Command | Purpose |
|---|---|
| `/find-dev-rule` | Locate a plugin-dev rule everywhere it's defined; check against official docs (read-only) |
| `/report-dev-rules` | Generate a rules report at marketplace, plugin, or component level |
| `/verify-dev-rules` | Cross-check a rules report against official docs to produce a verified gap report |
| `/plan-dev-rules` | Turn a verified gap report into a file-by-file implementation plan |
| `/implement-dev-rules` | Execute a verified plan file-by-file, verifying each change |
| `/update-dev-rule` | Update a stale rule and everything it affects, then report the changes |

## Hooks

`hooks/hooks.json` registers:

- **`Stop`** → `stop-hook.sh` — drives the iterative skill-improvement loop's stop-cycle logic
- **`PostToolUse`** (matcher `Write|Edit`) → `rulebook-check.sh` — enforces `plugin-rulebook` compliance on edited components; `hooks-schema-check.sh` — validates any edited `hooks.json` against its schema

## Quick Start

1. **Building a component?** Ask directly — "create a hook that validates file writes," "add an MCP server for Postgres," "write a rule about early returns" — the matching skill activates automatically.
2. **Reviewing what you built?** Invoke the matching reviewer agent, or run `plugin-validator` for a full structural pass.
3. **Iterating on a skill?** Use `/skill-improver` for an automated fix-review loop, or `skill-refiner-interactive` for operator-guided refinement.
4. **Rolling out org-wide conventions?** `rules-extract` → `rules-merge` → `rules-apply`.

## Contributing

This plugin is part of the `andres-cc-marketplace`. To contribute:

1. Fork the marketplace repository
2. Make changes under `plugins/plugin-dev/`
3. Test locally with `cc --plugin-dir`
4. Run `plugin-validator` and the relevant reviewer agent(s) before opening a PR

## License

Apache License 2.0 — see `LICENSE` for details.

## Author

Andre Hahm
