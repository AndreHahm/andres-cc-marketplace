# Plugin Development Toolkit

A comprehensive toolkit for developing Claude Code plugins — skills for building agents, commands, hooks, MCP integrations, rule pipelines, and full plugin structure guidance, plus reviewer agents that check the components you build against the plugin's own rulebook.

## Overview

`plugin-dev` ships **32 skills**, **23 agents**, **16 commands**, and `PreToolUse`/`Stop`/`PostToolUse` hooks. Skills fall into six broad groups:

| Group | Skills |
|---|---|
| **Component authoring** | `agent-development`, `command-development`, `hook-development`, `skill-development`, `workflow-skill-development`, `mcp-integration` |
| **Plugin structure & governance** | `plugin-development`, `plugin-rulebook`, `upstream-sources-registry`, `plugin-settings`, `plugin-evaluation`, `marketplace-development`, `plugin-documentation` |
| **Skill quality & lifecycle** | `skill-refiner-interactive`, `skill-improver-loop`, `skill-tester`, `skill-security`, `skill-stocktake`, `skill-maintenance` |
| **Plugin lifecycle** | `plugin-lifecycle-upstream`, `plugin-lifecycle-downstream`, `plugin-lifecycle-maintenance` |
| **Planning & analysis** | `plugin-ideation`, `plugin-planning`, `plugin-comparison`, `plugin-grader`, `analyzing-sessions` |
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
| `upstream-sources-registry` | Tracking official Claude Code sources (docs, changelog, informal GitHub signals) with classification, derived re-check priority, and freshness state, consulted by the dev-rules commands instead of ad-hoc web search |
| `plugin-settings` | Adding per-project configuration via `.claude/plugin-name.local.md` |
| `plugin-evaluation` | Designing a rubric or LLM-judge methodology to evaluate agents/commands |
| `marketplace-development` | Converting a skills-only repo (no `plugin.json`) into a publishable marketplace |
| `plugin-documentation` | Authoring or updating a plugin's human-facing docs (README, CONTRIBUTING, CHANGELOG, and more) from its actual current state, then invoking `human-doc-reviewer` for QA |

### Skill Quality & Lifecycle

| Skill | Use when |
|---|---|
| `skill-refiner-interactive` | Interactively refining an existing skill for clarity, token efficiency, production readiness |
| `skill-improver-loop` | Running automated fix-review cycles on a skill until it clears `skill-reviewer` |
| `skill-tester` | Empirically benchmarking a skill against a baseline (timing, token metrics) |
| `skill-security` | Auditing a skill for permission risk, prompt injection, or PII leakage |
| `skill-stocktake` | Auditing all skills/commands in a project for quality, staleness, and overlap |
| `skill-maintenance` | Deciding whether and how to propagate a change across plugin-dev's own components |

### Plugin Lifecycle

| Skill | Use when |
|---|---|
| `plugin-lifecycle-upstream` | Creating a new plugin/component end-to-end — Ideate, Plan, Design, Build, Test, Commit, Document, Handoff |
| `plugin-lifecycle-downstream` | QA-ing an existing plugin — Validate, Audit+Report, optional Fix, and Document |
| `plugin-lifecycle-maintenance` | Evolving an already-built plugin — retro-driven improvement, comparison-driven enhancement, keeping plugin-dev's own rules current against official docs, or plugin-dev's own on-demand self-service checks against itself |

### Planning & Analysis

| Skill | Use when |
|---|---|
| `plugin-ideation` | Brainstorming a new plugin or component from a rough idea into a Concept Card |
| `plugin-planning` | Turning an accepted concept into a concrete component inventory and build plan |
| `plugin-comparison` | Comparing a plugin/component in this repo against another internal, installed, local, or GitHub-hosted target |
| `plugin-grader` | Scoring a plugin or component on a weighted rubric with SWOT and prioritized next steps |
| `analyzing-sessions` | Running a post-session retrospective — SWOT, self-critique, and improvement suggestions across every component used |

### `.claude/rules/` Pipeline

| Skill | Use when |
|---|---|
| `rule-development` | Writing or validating a single `.claude/rules/` file with contrastive examples |
| `rules-extract` | Mining a codebase, PR, or conversation for project-specific rules |
| `rules-merge` | Consolidating extracted rules from multiple repos into a shared, portable set |
| `rules-apply` | Applying merged org-wide rules to a project and cleaning up local overrides |
| `rules-review` | Checking a diff's changed files against applicable rules |

## Agents

Twenty-three specialized agents, seventeen of which are quality-gate reviewers cross-checked by `plugin-validator`:

| Agent | Purpose |
|---|---|
| `plugin-validator` | Validates overall plugin structure, manifest, and component wiring |
| `plugin-rulebook-checker` | Isolated, Agent-dispatchable R1-R26 compliance checker for plugin-rulebook -- full-plugin batch sweep or fast targeted delta re-check, without a general-purpose Agent's tool-schema and full-SKILL.md-reading overhead |
| `skill-reviewer` | Reviews skill files for structure and best-practice adherence |
| `hook-reviewer` | Reviews hook configurations for safety and correctness before deployment |
| `rule-reviewer` | Reviews `.claude/rules/` files before they load into every session |
| `subagent-reviewer` | Reviews agent/subagent definition files for quality before deployment |
| `command-reviewer` | Reviews slash-command files for quality and best-practice compliance |
| `claudemd-reviewer` | Reviews CLAUDE.md files for budget, separation of concerns, and actionability |
| `human-doc-reviewer` | Reviews README/CONTRIBUTING/CHANGELOG and other human-facing docs for completeness and accuracy |
| `language-reviewer` | Reviews a plugin and its surrounding project for English-language and Unicode-integrity compliance |
| `external-references-reviewer` | Detects and classifies references to external companies, orgs, and repos |
| `consistency-reviewer` | Reviews data, governance, functionality, and capability consistency across related components |
| `completeness-reviewer` | Finds open items, missing documentation, missing test/eval evidence, and stale claims |
| `scripts-reviewer` | Reviews shell/Python scripts for correctness bugs and code smells |
| `activation-reviewer` | Reviews activation-description quality and detects overlapping/ambiguous triggers between skills/agents |
| `skilldir-reviewer` | Deep-audits a skill's non-SKILL.md files (references/scripts/assets/workflows/examples) for staleness and duplication |
| `dependency-reviewer` | Reviews the Skill()/Agent() call graph across components for circular/bidirectional dependencies and required-vs-optional classification |
| `security-reviewer` | Audits a component for permission risk, prompt-injection surface, and PII/credential-leakage patterns beyond plugin-validator's basic check |
| `permission-reviewer` | Computes a component's or plugin's effective permission by reconciling frontmatter against plugin-level settings.json/hook rules |
| `agent-creator` | Generates new agent configurations from a described need |
| `plugin-inspector` | Inspects a plugin or component and produces a structured capability portfolio |
| `enhancement-suggestor` | Turns review/validation/comparison/test findings into a classified WHAT/WHY/HOW improvement plan |
| `build-handoff-writer` | Writes/updates the build handoff report combining narrative, commits, and open items for a pipeline run |

## Commands

**Plugin/skill workflow:**

| Command | Purpose |
|---|---|
| `/create-plugin` | Guided end-to-end workflow: design, build, and validate a new plugin |
| `/create-command` | Scaffold a new slash command with full feature support |
| `/skill-improver` | Iteratively review and fix a skill until it passes quality standards |
| `/cancel-skill-improver` | Stop an in-progress skill-improvement loop, keeping changes made so far |
| `/implemented` | Check whether one or more stated requirements are implemented, partial, or open in the current plugin, verified fresh against actual files and official docs |

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

**Maintenance:**

| Command | Purpose |
|---|---|
| `/trim-permissions` | Consolidate `.claude/settings.local.json`'s permission allowlist -- exact duplicates, wildcard-subsumed entries, and one-off literal commands, tiered by confidence |

## Hooks

`hooks/hooks.json` registers:

- **`PreToolUse`** (matcher `Bash`) → `security-precommit-check.sh` — log-only, deterministic security pre-commit check run before `git commit` executes
- **`Stop`** → `stop-hook.sh` — drives the iterative skill-improvement loop's stop-cycle logic
- **`PostToolUse`** (matcher `Write|Edit`) → `rulebook-check.sh` — enforces `plugin-rulebook` compliance on edited components; `hooks-schema-check.sh` — validates any edited `hooks.json` against its schema
- **`PostToolUse`** (matcher `^(Agent|Skill)$`) → `r26-expensive-action-check.sh` — log-only, best-effort runtime check for R26 (Expensive-Action Opt-In) violations on Agent/Skill dispatches

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
