# Plugin Directory Structure Reference

This guide documents the standard plugin directory layout, file organization patterns, and structure requirements.

## Table of Contents

- [Standard Plugin Layout](#standard-plugin-layout)
- [Directory Organization Rules](#directory-organization-rules)
  - [Required: .claude-plugin/ Directory](#required-claude-plugin-directory)
  - [Optional: skills/ Directory](#optional-skills-directory)
  - [Optional: agents/ Directory](#optional-agents-directory)
  - [Optional: hooks/ Directory](#optional-hooks-directory)
  - [Optional: scripts/ Directory](#optional-scripts-directory)
  - [Optional: bin/ Directory](#optional-bin-directory)
  - [Optional: .mcp.json File](#optional-mcpjson-file)
  - [Optional: .lsp.json File](#optional-lspjson-file)
  - [Optional: output-styles/ Directory](#optional-output-styles-directory)
  - [Optional: themes/ Directory](#optional-themes-directory)
  - [Optional: monitors/ Directory](#optional-monitors-directory)
  - [Optional: assets/ Directory](#optional-assets-directory)
  - [Optional: README.md](#optional-readmemd)
  - [Optional: CHANGELOG.md](#optional-changelogmd)
  - [Optional: LICENSE](#optional-license)
- [File Locations Reference Table](#file-locations-reference-table)
- [Common Plugin Patterns](#common-plugin-patterns)
- [Structure Validation Checklist](#structure-validation-checklist)
- [Size and Performance Considerations](#size-and-performance-considerations)
- [Migration from Old Structure](#migration-from-old-structure)
- [See Also](#see-also)

## Standard Plugin Layout

**R18 exception (recorded):** the tree below intentionally exceeds the rulebook's 30-line code-block threshold — a whole-tree illustration where splitting would remove the pedagogical value of seeing the complete standard layout in one place.

A complete, production-ready plugin follows this structure:

```
my-plugin/
├── .claude-plugin/                 # Metadata directory (required)
│   └── plugin.json                # Plugin manifest (required)
├── skills/                          # Agent Skills (optional, can be user or auto-invoked)
│   ├── code-analyzer/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── guide.md
│   ├── pdf-processor/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── process.py
│   └── formatter/
│       └── SKILL.md
├── agents/                          # Custom agents (optional)
│   ├── security-reviewer.md
│   ├── performance-tester.md
│   └── compliance-checker.md
├── hooks/                           # Hook configurations (optional)
│   └── hooks.json
├── .mcp.json                        # MCP server definitions (optional)
├── .lsp.json                        # LSP server configs (optional)
├── scripts/                         # Utility scripts (optional)
│   ├── security-scan.sh
│   ├── format.py
│   └── deploy.js
├── output-styles/                   # Response-formatting styles (optional)
│   └── terse.md
├── themes/                          # Color theme presets (optional)
│   └── dracula.json
├── monitors/                        # Background monitor configs (optional)
│   └── monitors.json
├── assets/                          # Static assets (optional)
│   ├── icon.png
│   ├── logo.svg
│   └── templates/
│       └── report.html
├── LICENSE                          # License file (recommended)
├── CHANGELOG.md                     # Version history (recommended)
└── README.md                        # Plugin documentation (recommended)
```

## Directory Organization Rules

### Required: .claude-plugin/ Directory

**Purpose:** Contains plugin metadata

**Must contain:**
- `.claude-plugin/plugin.json` — Plugin manifest (only required file)

**Important:**
- Only `plugin.json` belongs in `.claude-plugin/`
- All other components (`commands/`, `agents/`, etc.) must be in plugin root
- Don't put commands or agents inside `.claude-plugin/`

✅ **Correct:**
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          ← Only manifest here
├── commands/                ← Components at root
└── agents/
```

❌ **Wrong:**
```
my-plugin/
├── .claude-plugin/
│   ├── plugin.json
│   ├── commands/            ← Don't put here
│   └── agents/              ← Don't put here
```

### Optional: agents/ Directory

**Purpose:** Custom agents that Claude invokes for specialized tasks

**Structure:**
```
agents/
├── security-reviewer.md     # Custom agent 1
├── performance-tester.md    # Custom agent 2
└── compliance-checker.md    # Custom agent 3
```

**Rules:**
- Each agent is a `.md` file
- Filename doesn't matter; use `name` field in frontmatter
- Must include `capabilities` array describing what agent can do
- Can include context, examples, and detailed expertise description

**File format:**
```markdown
---
description: What this agent specializes in
capabilities: ["code-review", "security-audit", "compliance-check"]
---

# Security Reviewer Agent

Detailed description of agent expertise, when to invoke it, and capabilities.

## Capabilities
- Security vulnerability detection
- Compliance verification
- Access control analysis

## Examples
Provide examples of tasks this agent excels at.
```

### Optional: skills/ Directory

**Purpose:** Agent Skills that Claude uses automatically for specialized tasks

**Structure:**
```
skills/
├── code-analyzer/
│   ├── SKILL.md             # Skill definition
│   ├── references/          # Supporting docs (optional)
│   │   └── patterns.md
│   └── scripts/             # Utility scripts (optional)
│       └── analyze.py
└── pdf-processor/
    ├── SKILL.md
    └── references/
        └── ocr-guide.md
```

**Rules:**
- Each skill is a directory with `SKILL.md` file
- Directory name is skill name
- Can include `references/` and `scripts/` subdirectories
- Keep SKILL.md body <500 lines (move detailed content to references/)

**SKILL.md format:**
```yaml
---
name: skill-name
description: >-
  What the skill does. Use when [trigger context].
allowed-tools: Read,Write,Bash
disable-model-invocation: false  # Allow Claude auto-invoke
user-invocable: true              # Allow user /skill-name invocation
---

# Skill Name

Instructions for Claude to follow when invoking this skill.

## Quick Start
Essential execution steps.

## Key Notes
Important constraints and edge cases.
```

**Frontmatter fields for invocation control:**
- `disable-model-invocation: true` - Only user can invoke (for side-effect operations like deploy, commit)
- `user-invocable: false` - Only Claude can invoke (for background knowledge skills)
- Default (or omitted) - Both Claude auto-invoke and user invocation enabled

### Optional: hooks/ Directory

**Purpose:** Event handlers that respond to Claude Code events

**Structure:**
```
hooks/
└── hooks.json               # Hook configuration

# Or reference in plugin.json directly:
"hooks": "./hooks.json"
```

**File format (hooks.json):**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
          }
        ]
      }
    ]
  }
}
```

### Optional: scripts/ Directory

**Purpose:** Utility scripts used by hooks, MCP servers, or skills

**Structure:**
```
scripts/
├── format.sh                # Bash script for hooks
├── lint.sh
├── process.py               # Python script
├── deploy.js                # Node script
└── README.md                # Script documentation
```

**Rules:**
- Scripts must be executable: `chmod +x script.sh`
- Include shebang: `#!/bin/bash` or `#!/usr/bin/env bash`
- Reference with `${CLAUDE_PLUGIN_ROOT}` variable in hooks/MCP

### Optional: bin/ Directory

**Purpose:** Executables the plugin exposes as commands

**Structure:**
```
bin/
├── my-plugin-cli               # Executable added to PATH
└── my-plugin-helper
```

**Rules:**
- Files in `bin/` are added to the Bash tool's `PATH` while the plugin is enabled
- Treat every file in `bin/` as privileged runtime code — it requires the same review, permissioning, and testing as hook scripts and MCP server binaries
- Must be executable (`chmod +x`)

### Optional: .mcp.json File

**Purpose:** Model Context Protocol server definitions

**Location:** Plugin root (not in subdirectory)

**File format:**
```json
{
  "database-server": {
    "command": "python",
    "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/database.py"],
    "env": {
      "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
    }
  },
  "api-client": {
    "command": "node",
    "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/api-client.js"]
  }
}
```

### Optional: .lsp.json File

**Purpose:** Language Server Protocol definitions for code intelligence

**Location:** Plugin root (not in subdirectory)

**File format:**
```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  },
  "python": {
    "command": "pyright",
    "args": ["--stdio"],
    "extensionToLanguage": {
      ".py": "python"
    }
  }
}
```

### Optional: output-styles/ Directory

**Purpose:** Adjust Claude's response formatting (terseness, structure, verbosity) — not visual/CSS styling. Output styles surface in `/output-style` once the plugin is enabled.

**Structure:**
```
output-styles/
└── terse.md                 # Markdown file with name/description frontmatter
```

**File format (`output-styles/terse.md`):**
```markdown
---
name: terse
description: Short, direct answers. Skip explanations unless asked.
---

Answer in the fewest words that convey the result. Skip preambles like
"Sure, I'll" — go straight to the answer or the diff.
```

**Rules:**
- Files are Markdown with `name` + `description` frontmatter, not CSS
- Focus the body on *what to say and when*, not visual formatting
- A custom `"outputStyles"` value in `plugin.json` **replaces** the default `output-styles/` directory

See `references/output-styles.md` for the complete component reference.

### Optional: themes/ Directory

**Purpose:** Bundle color presets that appear in `/theme` alongside built-in and user themes.

**Structure:**
```
themes/
└── dracula.json              # One JSON file per theme
```

**File format (`themes/dracula.json`):**
```json
{
  "name": "Dracula",
  "base": "dark",
  "overrides": {
    "accent": "#bd93f9",
    "error": "#ff5555"
  }
}
```

**Rules:**
- `base` inherits from a built-in preset (`"dark"` or `"light"`); `overrides` is a sparse map of color tokens
- A custom `"themes"` value in `plugin.json` **replaces** the default `themes/` directory
- Plugin themes are read-only in `/theme` — the user copies one to `~/.claude/themes/` to edit it

See `references/themes.md` for the complete component reference.

### Optional: monitors/ Directory

**Purpose:** Background watchers Claude Code starts automatically when the plugin is active — each runs a shell command for the session's lifetime and streams stdout lines to Claude as notifications.

> **Version:** Requires Claude Code v2.1.105 or later.

**Structure:**
```
monitors/
└── monitors.json             # Array of monitor entries
```

**File format (`monitors/monitors.json`):**
```json
[
  {
    "name": "error-log",
    "command": "tail -F ./logs/error.log",
    "description": "Application error log"
  }
]
```

**Rules:**
- `name`, `command`, and `description` are required per entry
- A custom `"monitors"` value in `plugin.json` **replaces** the default `monitors/monitors.json`

See `references/monitors.md` for the complete component reference.

### Optional: assets/ Directory

**Purpose:** Static files like icons, images, templates

**Structure:**
```
assets/
├── icon.png                 # Plugin icon (128x128 recommended)
├── logo.svg
├── templates/
│   ├── report.html
│   └── email.txt
└── images/
    ├── screenshot1.png
    └── screenshot2.png
```

### Optional: README.md

**Purpose:** Plugin documentation for users and developers

**Suggested sections:**
- Overview (what the plugin does)
- Installation (how to install)
- Usage (how to use each command)
- Configuration (any setup needed)
- Troubleshooting
- Contributing guidelines
- License

### Optional: CHANGELOG.md

**Purpose:** Version history and release notes

**Format:**
```markdown
# Changelog

## [2.1.0] - 2024-01-15
### Added
- New security-audit command
- Support for custom rule files

### Fixed
- Performance issue with large files

## [2.0.0] - 2024-01-01
### Changed
- Breaking change: restructured command output
```

### Optional: LICENSE

**Purpose:** License terms for the plugin

**Examples:**
- `LICENSE` (MIT license text)
- `.license/` (multiple license files)
- License identifier in `plugin.json`: `"license": "MIT"`

## File Locations Reference Table

| Component | Default Location | Type | Required? | Purpose |
|-----------|------------------|------|-----------|---------|
| **Manifest** | `.claude-plugin/plugin.json` | File | ✅ Yes | Plugin configuration |
| **Skills** | `skills/` | Directory | ❌ No | Agent Skills (auto + user-invoked) |
| **Agents** | `agents/` | Directory | ❌ No | Custom agents |
| **Hooks** | `hooks/hooks.json` or inline | File/Config | ❌ No | Event handlers |
| **MCP servers** | `.mcp.json` or inline | File/Config | ❌ No | External service integration |
| **LSP servers** | `.lsp.json` or inline | File/Config | ❌ No | Code intelligence |
| **Scripts** | `scripts/` | Directory | ❌ No | Utility scripts |
| **Bin** | `bin/` | Directory | ❌ No | Executables added to `PATH` (privileged) |
| **Output Styles** | `output-styles/` | Directory | ❌ No | Response-formatting styles (Markdown) |
| **Themes** | `themes/` | Directory | ❌ No | Color theme presets (JSON) |
| **Monitors** | `monitors/monitors.json` | File | ❌ No | Background watcher configs (v2.1.105+) |
| **Assets** | `assets/` | Directory | ❌ No | Static files, images |
| **Docs** | `README.md`, `CHANGELOG.md` | Files | ❌ No | User documentation |
| **License** | `LICENSE` | File | ❌ No | License terms |

## Common Plugin Patterns

### Simple Plugin (Single Skill)

```
simple-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── formatter/
│       └── SKILL.md
└── README.md
```

### Multi-Skill Plugin

```
code-tools-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── validator/
│   │   └── SKILL.md
│   ├── formatter/
│   │   └── SKILL.md
│   ├── analyzer/
│   │   └── SKILL.md
│   └── reporter/
│       └── SKILL.md
└── README.md
```

### Plugin with Skills and References

```
analyzer-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── code-analyzer/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── patterns.md
│   └── pattern-detector/
│       ├── SKILL.md
│       └── scripts/
│           └── detect.py
└── README.md
```

### Plugin with MCP Integration

```
database-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── query-builder/
│   │   └── SKILL.md
│   └── schema-analyzer/
│       └── SKILL.md
├── .mcp.json
├── mcp/
│   └── database.py
└── README.md
```

### Complete Enterprise Plugin

**R18 exception (recorded):** the tree below intentionally exceeds the rulebook's 30-line code-block threshold — a whole-tree illustration where splitting would remove the pedagogical value of seeing a complete real-world layout in one place.

```
enterprise-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── deploy-coordinator/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── deployment-checklist.md
│   ├── status-monitor/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── check-health.py
│   ├── kubernetes-deployment/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── kubectl-guide.md
│   └── aws-integration/
│       ├── SKILL.md
│       └── scripts/
│           └── sync.py
├── agents/
│   ├── deployment-manager.md
│   └── security-auditor.md
├── hooks/
│   └── hooks.json
├── .mcp.json
├── .lsp.json
├── scripts/
│   ├── pre-deploy.sh
│   ├── post-deploy.sh
│   └── health-check.py
├── output-styles/
│   └── deployment-brief.md
├── assets/
│   ├── icon.png
│   └── templates/
│       └── status-report.html
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## Structure Validation Checklist

Before installing or distributing your plugin:

- [ ] `.claude-plugin/plugin.json` exists at correct location
- [ ] `plugin.json` is valid JSON (validate with `jq .`)
- [ ] Required fields in manifest: `name`, `description`
- [ ] Component directories at plugin root (not in `.claude-plugin/`)
- [ ] Skill directories contain `SKILL.md` with required frontmatter (name, description)
- [ ] Skill frontmatter includes invocation control (disable-model-invocation, user-invocable)
- [ ] Skill names are lowercase-hyphen
- [ ] Agent files have required `description` and `capabilities`
- [ ] All paths in `plugin.json` use `./` prefix
- [ ] Hook scripts are executable (`chmod +x`)
- [ ] Hook scripts have shebang line
- [ ] MCP/LSP paths use `${CLAUDE_PLUGIN_ROOT}` variable
- [ ] No components inside `.claude-plugin/` directory
- [ ] Directory depth appropriate (not overly nested)
- [ ] No circular references or dependencies
- [ ] `commands/` is deprecated in favor of `skills/` for new work — supported for backward compatibility, not forbidden

## Size and Performance Considerations

**Plugin size guidelines:**
- Keep total plugin <50MB for fast downloads
- Move large assets to separate directories
- Consider lazy-loading for optional components
- Document external dependencies

**Performance considerations:**
- Limit number of commands (10-20 is reasonable)
- Keep hooks lightweight (short scripts)
- Avoid spawning many subprocesses
- Cache expensive operations where possible

## Migration from Old Structure

If you have an older plugin structure:

**Old structure:**
```
plugin/
├── plugin.json              ← At root
├── commands/
└── agents/
```

**New structure:**
```
plugin/
├── .claude-plugin/
│   └── plugin.json          ← Moved here
├── commands/
└── agents/
```

**Migration steps:**
1. Create `.claude-plugin/` directory
2. Move `plugin.json` to `.claude-plugin/plugin.json`
3. Reinstall plugin: `claude plugin uninstall && claude plugin install`

## See Also

- [Plugin manifest schema](plugin-json-schema.md) — Configuration options
- [Plugin caching](plugin-caching.md) — How plugins are installed
- [Debugging and troubleshooting](troubleshooting-and-production.md) — Fix structural issues
- [Slash commands](slash-command-format.md) — Command file format
- [Hooks](hooks.md) — Hook configuration patterns
