---
name: plugin-development
description: >-
  Create, convert, validate, and publish Claude Code plugins with Agent Skills,
  hooks, agents, and servers. Use when building plugins from scratch, converting
  projects to plugins, improving plugin structure, publishing a plugin (with
  plugin.json) to marketplace, or packaging existing skill collections into
  distributable plugins. Also use when understanding plugin directory structure,
  component organization, auto-discovery, manifest configuration, file naming
  conventions, or Claude Code plugin architecture. Component-specific work delegates
  to hook-creator, subagent-creator, and skill-creator skills. For skills-repo
  marketplace publishing (no individual plugin.json per skill), use
  marketplace-development instead.
allowed-tools: Read Write Edit Glob Bash(jq:*) Bash(python:*) Bash(claude:*) Skill
---

# Plugin Development

**Dual purpose:** Create plugins from scratch OR transform existing projects into well-structured plugins.

## Quick Routing

Ask the user what they want to do using AskUserQuestion — see `references/routing-patterns.md` for the full block. Options: **Create a new plugin**, **Convert a project to plugin**, **Validate a plugin**, **Publish to marketplace**. Then proceed to the appropriate section below.

---

## When to Use

- Building a plugin from scratch (manifest, directory structure, components)
- Converting an existing project into a Claude Code plugin
- Validating or improving an existing plugin's structure
- Publishing a plugin with `plugin.json` to a marketplace
- Packaging standalone `.claude/skills/` directories into distributable plugin format

## When NOT to Use

- Skills-repo marketplace publishing without individual `plugin.json` — use `marketplace-development` instead
- Creating individual skills, hooks, or subagents — use `skill-creator`, `hook-creator`, `subagent-creator` instead
- Debugging plugin runtime behavior or writing plugin application code

## Slash Commands Deprecated

**Slash commands** (via `commands/` directory) are legacy compatibility, merged into skills. Both `commands/` and `skills/` create slash-command entries. For new plugin work, always use Agent Skills (`skills/` directory); `commands/` remains supported for backward compatibility only. A plugin must not define a legacy command and a skill with the same effective slash-command name unless the duplication is intentional and documented.

---

## How Plugins Work

Plugin activation is pure LLM reasoning on manifest metadata — the `plugin.json` description is your activation signal (vague = never activated; specific = reliably activated). Plugin name becomes the skill namespace (`/plugin-name:skill-name`). For directory structure, token loading hierarchy, and auto-discovery sequence, see `references/plugin-architecture.md`.

---

## Quick Start

1. **Create a new plugin** — Answer the Quick Routing question above, then complete the New Plugin Creation Interview section below to gather all manifest fields before writing any files.
2. **Validate an existing plugin** — Run `claude plugin validate /path/to/plugin`. Check `references/validation-checklist.md` for detailed best practices.
3. **Convert a project** — Audit components, create `.claude-plugin/plugin.json`, migrate to `skills/`/`agents/`/`commands/` — see `references/workflows.md` (Workflow 2).
4. **Publish to marketplace** — Create `.claude-plugin/marketplace.json` using the template in the Workflow Sections → Publishing section below, then see `references/marketplace-reference.md` for full schema.

For bash scaffolding commands and `init_plugin.py`, see `references/quick-start-guide.md`.

---

## New Plugin Creation Interview

After the user selects "Create a new plugin" from Quick Routing, conduct this structured interview to gather all manifest fields **before** file creation. Ask one question at a time (progressive disclosure):

1. **Plugin name** — "What's the plugin name?" (lowercase-hyphen, 1-64 chars)
   - Maps to: `plugin.json` → `name`; Example: `code-reviewer`, `pdf-processor`

2. **Purpose/description** — "What does the plugin do? Describe its main purpose and capabilities."
   - Maps to: `plugin.json` → `description` (1-1024 chars)

3. **Version** — "What version? (semantic format: MAJOR.MINOR.PATCH)"
   - Default if not specified: `1.0.0`

4. **Author information** — "Who is the author? (name, optional: email, URL)"
   - Maps to: `plugin.json` → `author.name`

5. **Optional metadata** — "Any additional metadata? (license, repository, homepage)"
   - Example: `"MIT"`, `"https://github.com/user/plugin"`

6. **Components (BATCH 1)** — Use AskUserQuestion with **predefined options** (multiSelect: true):

```
questions: [
  {
    question: "Which core components will the plugin include?",
    header: "Core Components",
    options: [
      { label: "Skills", description: "Agent Skills (recommended)" },
      { label: "Agents", description: "Subagents for complex workflows" },
      { label: "Hooks", description: "Event handlers and automation" },
      { label: "MCP servers", description: "Model Context Protocol servers" }
    ],
    multiSelect: true
  }
]
```

7. **Components (BATCH 2)** — Then use AskUserQuestion for optional server support:

```
questions: [
  {
    question: "Include Language Server Protocol (LSP) support?",
    header: "LSP Servers",
    options: [
      { label: "Yes", description: "Add language-specific code intelligence" },
      { label: "No", description: "Skip LSP servers" }
    ],
    multiSelect: false
  }
]
```

⏸️ Wait for both batch responses before proceeding.

8. **Distribution scope** — Use AskUserQuestion with **predefined options**:

```
questions: [
  {
    question: "What's the distribution scope for this plugin?",
    header: "Distribution",
    options: [
      { label: "Personal", description: "Personal use only" },
      { label: "Team-shared", description: "Share with team members" },
      { label: "Marketplace", description: "Publish to plugin marketplace for community" }
    ],
    multiSelect: false
  }
]
```

### Manifest Field Mapping Reference

| Interview Question | Maps to | Type | Required | Notes |
|---|---|---|---|---|
| Plugin name | `plugin.json` → `name` | string | Yes | kebab-case, 1-64 chars |
| Purpose/description | `plugin.json` → `description` | string | Yes | 1-1024 chars |
| Version | `plugin.json` → `version` | string | No | Default: 1.0.0 |
| Author name | `plugin.json` → `author.name` | string | Yes | Must be object property |
| Author email | `plugin.json` → `author.email` | string | No | Optional |
| License | `plugin.json` → `license` | string | No | e.g., "MIT" |
| Repository | `plugin.json` → `repository` | string | No | GitHub URL |
| Distribution scope | `marketplace.json` | string | No | personal / team / marketplace |

### Common Manifest Generation Failures (Prevention)

**`author` is string instead of object**
- ❌ `"author": "John Doe"` → ✅ `"author": {"name": "John Doe"}`

**Missing required fields** — always check `name`, `description`, `author.name` are present before writing.

**Incorrect marketplace.json schema:**
- `owner` MUST be object: `{"name": "username"}` (not a string)
- `plugins` MUST be array: `[{...}]`
- `source` paths MUST start with `./`

---

## Workflow Sections

### 1. Creating a New Plugin from Scratch
Interview → create structure → add components → `claude plugin validate` → test locally.
See `references/workflows.md` (Workflow 1) for complete step-by-step procedures.

### 2. Converting an Existing Project to a Plugin
Identify components → create plugin structure → migrate metadata → validate.
See `references/workflows.md` (Workflow 2).

### 3. Validating or Improving Existing Plugins
Run `claude plugin validate /path/to/plugin` directly. Then check `references/validation-checklist.md` for best practices. For scanner-based automated scanning, see `references/workflows.md` (Workflow 3).

### 4. Publishing to Marketplace

> **Skills repo without plugin.json?** Use the **`marketplace-development`** skill — it handles `strict: false`, cache footprint validation, and schema anti-patterns.

**Create `.claude-plugin/marketplace.json`:**

```json
{
  "name": "your-plugin-name",
  "owner": { "name": "github-username-or-org" },
  "plugins": [
    {
      "name": "your-plugin-name",
      "source": "./",
      "description": "What the plugin does"
    }
  ]
}
```

`owner` MUST be object. `plugins` MUST be array. `source` MUST start with `./`. See `references/marketplace-reference.md` for full schema and distribution setup.

---

## Manifest Generation Best Practices

**Official schema vs. internal policy:** `plugin.json` is optional, and when present only `name` is officially required by the platform. Requiring `description`, `version`, `author`, README, and marketplace metadata below is this project's internal publishing policy for distributable plugins, not a platform requirement — do not present them to the user as officially mandatory.

**Before generating, verify you have:** name (kebab-case, 1-64 chars), description (1-1024 chars), author name (object), version (default: 1.0.0).

**Never generate with incomplete data** — incomplete manifests cause validation failures. Run the interview flow first.

**2025 Schema Compliance:** All packaged skills must have `allowed-tools` in their SKILL.md frontmatter. Audit with `python scripts/validate_plugin.py --check 2025`.

---

## Automation Scripts

| Script | Purpose | Key Flags |
|---|---|---|
| `scripts/init_plugin.py` | Scaffold plugin structure (directories + plugin.json) | `--components skills,agents` |
| `scripts/create_plugin.py` | Scaffold + register in marketplace.json | `--marketplace-root /path` |
| `scripts/generate_manifest.py` | Generate schema-compliant plugin.json | `--template minimal\|standard\|complete` |
| `scripts/validate_plugin.py` | Validate structure, manifest, 2025 compliance | `--check 2025 --verbose` |
| `scripts/package_skills.py` | Copy `.claude/skills/` into plugin format | `--validate --dry-run` |
| `scripts/bump_version.py` | Bump version in plugin.json + marketplace.json atomically | `major\|minor\|patch` |
| `scripts/scan-plugin.sh` | Scan plugin and output JSON validation report | `/path/to/plugin /tmp/report.json` |

Templates in `templates/`: `plugin.json.minimal`, `plugin.json.standard`, `plugin.json.complete`, `marketplace.json.minimal`, `marketplace.json.multi`. See `templates/README.md` for template usage guide.

See `references/workflows.md` for complete development workflows using these scripts.

---

## Component Overview

| Component | Use Case |
|-----------|----------|
| **Agent Skills** (`skills/`) | Capabilities Claude uses automatically or via `/skill-name` (recommended) |
| **Subagents** (`agents/`) | Isolated execution with custom prompts and permissions (use `subagent-creator`) |
| **Hooks** (`hooks/hooks.json`) | Event handlers: tool use, permissions, sessions (use `hook-creator`) |
| **MCP Servers** (`.mcp.json`) | External service integration (APIs, databases) |
| **LSP Servers** (`.lsp.json`) | Language-specific code intelligence |
| **Commands** (`commands/`) | DEPRECATED: Use Agent Skills instead |

See `references/quick-reference.md` for component templates and metadata requirements.

---

## File Naming Conventions

| Component | Convention | Example |
|-----------|------------|---------|
| Commands | kebab-case `.md` → becomes slash command | `code-review.md` → `/code-review` |
| Agents | kebab-case `.md` describing role | `test-generator.md` |
| Skills | kebab-case directory name | `api-testing/`, `error-handling/` |
| Scripts | kebab-case + extension | `validate-input.sh`, `process-data.py` |
| Config | Standard names only | `hooks.json`, `.mcp.json`, `plugin.json` |

---

## Common Mistakes

| Mistake | Wrong | Correct |
|---------|-------|---------|
| Components inside `.claude-plugin/` | `my-plugin/.claude-plugin/skills/` | `my-plugin/skills/` (at plugin root) |
| Absolute paths in manifests | `"skills": "/Users/me/plugin/skills"` | `"skills": "./skills"` |
| Non-kebab plugin name | `"name": "My_Plugin"` | `"name": "my-plugin"` |
| `author` as string | `"author": "John Doe"` | `"author": {"name": "John Doe"}` |
| Missing `allowed-tools` in SKILL.md | No frontmatter field | `allowed-tools: Read Write Bash` |
| No README.md | (missing) | Always include install + usage instructions |

For debugging, common issues, and production checklist, see `references/troubleshooting-and-production.md`.

---

## Key Notes

**Description formula (activation signal):**
```
[Action]. [Brief description of purpose]. [Components/scope].
```
Example: "Review code for best practices. Includes validate, report, and export commands."

For plugin naming, paths, CLI commands, and installation scopes, see the Reference Guide below.

---

## Testing & Validation

After creating or modifying a plugin:

1. **JSON syntax** — `jq empty .claude-plugin/plugin.json && echo "Valid"` before anything else
2. **Schema validation** — `claude plugin validate /path/to/plugin` (or `python scripts/validate_plugin.py`)
3. **2025 compliance** — `python scripts/validate_plugin.py --check 2025` for `allowed-tools` audit
4. **Local test** — `claude --plugin-dir /path/to/plugin` — verify components appear and activate correctly
5. **Marketplace test** — if publishing: `claude plugin marketplace add . && claude plugin install <name>`

**Quality gates:**
- [ ] `claude plugin validate` reports no errors
- [ ] `author` is an object (`{"name": "..."}`) not a string
- [ ] All manifest paths use `./` (no absolute paths)
- [ ] All packaged skills have `allowed-tools` in frontmatter
- [ ] Plugin activates correctly under `claude --plugin-dir /path`
- [ ] README.md exists with installation instructions
- [ ] Manifest/component changes were verified against the current official plugin reference, not cached assumptions

---

## Packaging & Scope Notes

- **CLAUDE.md is not project context here:** a `CLAUDE.md` at the plugin root is NOT loaded as project context. Deliver runtime instructions through skills, agents, hooks, or other plugin components instead (see `references/plugin-architecture.md` and `references/claudemd-guidelines.md`).
- **Reload behavior:** skill `SKILL.md` changes take effect immediately; changes to other components (hooks, agents, `.mcp.json`, output-styles) require `/reload-plugins` or a restart (see `references/local-development.md`).
- **Scope selection:** choose `user` (personal, cross-project), `project` (team-shared, version-controlled), `local` (private, machine-specific), or `managed` (org-controlled) intentionally — for team-shared settings, hooks, MCP servers, and plugins prefer `project`; reserve `local` for personal overrides (see `references/installation-and-cli.md`).
- **`defaultEnabled`:** set `defaultEnabled: false` for plugins that add cost, contact external services, start background services, or broaden tool scope (see `references/manifest-reference.md`).
- **`bin/` is privileged:** plugin executables in `bin/` are added to `PATH` when the plugin is enabled — review and test them like hook scripts and MCP server binaries (see `references/directory-structure.md`).
- **Plugin `settings.json`:** only a limited set of keys is supported — validate against `references/manifest-reference.md` before adding new ones.
- **Dependencies:** declare plugin dependencies explicitly; they are validated during install, enable, update, disable, and prune workflows (see `references/manifest-reference.md`).
- **MCP servers:** define plugin MCP servers in plugin-root `.mcp.json` or inline in `plugin.json`; use `${CLAUDE_PLUGIN_ROOT}` for bundled server commands and config files (see `references/mcp-servers.md`).
- **Version bumps:** bump `plugin.json` version and `marketplace.json` for releases intended for users, and sync the README version on distribution-ready releases (see `references/versioning-and-distribution.md`); specific commit-per-bump requirements are project-internal policy, not a platform rule.

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/plugin-architecture.md` | How plugins load, token costs, architecture overview |
| `references/directory-structure.md` | Standard directory layout |
| `references/plugin-structure.md` | Structure overview + common plugin patterns |
| `references/plugin-json-schema.md` | Complete plugin.json field reference |
| `references/manifest-reference.md` | Manifest field examples |
| `references/quick-start-guide.md` | 5-minute setup commands and bash scaffolding |
| `references/quick-reference.md` | Component templates, formats, metadata requirements |
| `references/workflows.md` | Create, convert, validate, distribute — complete procedures, patterns, and automated scanning |
| `references/components-in-plugins.md` | Component packaging and path guidance |
| `references/component-patterns.md` | Component design patterns |
| `references/hooks.md` | Hook patterns and examples |
| `references/validation-checklist.md` | Comprehensive best practices checklist |
| `references/validation-rules.md` | 2025 compliance rules |
| `references/marketplace-reference.md` | marketplace.json schema, distribution methods, team setup, versioning, troubleshooting |
| `references/versioning-and-distribution.md` | Semver, changelog, distribution |
| `references/plugin-paths-variables.md` | $CLAUDE_PLUGIN_ROOT and path portability |
| `references/plugin-caching.md` | Caching behavior and implications |
| `references/installation-and-cli.md` | Scopes and CLI commands |
| `references/troubleshooting-and-production.md` | Debugging, common issues, production checklist |
| `references/local-development.md` | Local debugging and testing |
| `references/mcp-servers.md` | MCP server configuration |
| `references/claudemd-guidelines.md` | Writing and maintaining a project's CLAUDE.md |
| `references/lsp-servers.md` | LSP integration |
| `references/slash-command-format.md` | Legacy command support (backward compatibility) |
| `references/output-styles.md` | Output formatting guidance |
| `templates/README.md` | Overview and usage guide for template files |
| `examples/minimal-plugin.md` | Minimal working plugin example |
| `examples/standard-plugin.md` | Standard plugin with common components |
| `examples/advanced-plugin.md` | Full-featured plugin with all component types |
| `plugin-rulebook` | Plugin-level rules — invoke before finalizing any component to check naming, language, formatting, tool-scoping, and external-reference compliance |
