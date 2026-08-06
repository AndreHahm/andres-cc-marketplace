# Plugin Structure Reference

## Directory Hierarchy

See `directory-structure.md`'s "Standard Plugin Layout" for the complete canonical directory tree — not repeated here to avoid drift.

## Plugin Manifest (`plugin.json`)

**Location:** `.claude-plugin/plugin.json` (must be in this directory)

**Required fields:**

- `name`: Unique identifier (kebab-case)

**Standard metadata:**

- `version`: Semantic versioning (e.g., "1.0.0")
- `description`: Plugin purpose
- `author`: Object with name, email, url
- `homepage`: URL
- `repository`: URL
- `license`: SPDX identifier
- `keywords`: Array of search terms

**Component paths (optional):**

- `commands`: Path to commands directory
- `agents`: Path to agents directory
- `hooks`: Path to hooks configuration
- `mcpServers`: Path to MCP configuration

### Example plugin.json

```json
{
  "name": "example-plugin",
  "version": "1.0.0",
  "description": "Example plugin for demonstration",
  "author": {
    "name": "Plugin Creator",
    "email": "creator@example.com"
  },
  "keywords": ["example", "demo"]
}
```

## Component Types

### Commands

**Location:** `commands/` directory
**Format:** Markdown files with frontmatter
**Naming:** Subdirectories create namespaces via `:`

```
commands/
├── simple.md              # Invoked as /simple
└── namespace/
    └── command.md         # Invoked as /namespace:command
```

### Agents

**Location:** `agents/` directory
**Format:** Markdown files describing agent capabilities

### Skills

**Location:** `skills/` directory
**Format:** Subdirectories with `SKILL.md` file
**Structure:** See skills documentation

### Hooks

**Location:** `hooks/hooks.json` or path specified in manifest
**Events:** the full, current event list evolves across releases — see `hook-development/references/event-reference.md` for the authoritative list and event/type compatibility matrix rather than a fixed enumeration here

### MCP Servers

**Location:** `.mcp.json` at plugin root
**Purpose:** External tool integrations

## Path Requirements

- All paths relative to plugin root
- Start with `./` for custom paths
- Use `${CLAUDE_PLUGIN_ROOT}` for dynamic resolution in hooks/MCP
- Components must be at plugin root, not inside `.claude-plugin/`
