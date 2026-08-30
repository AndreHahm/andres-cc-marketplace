# Plugin Paths and Variables

Understanding plugin paths is critical for scripts, hooks, and external service integrations that need to reference plugin files.

## Table of Contents

- [Path Rules Overview](#path-rules-overview)
- [Relative Paths in plugin.json](#relative-paths-in-pluginjson)
- [${CLAUDE_PLUGIN_ROOT} Variable](#claude_plugin_root-variable)
- [Installation Path Behavior](#installation-path-behavior)
- [${CLAUDE_PLUGIN_DATA} Variable](#claude_plugin_data-variable)
- [${CLAUDE_PROJECT_DIR} Variable](#claude_project_dir-variable)
- [${CLAUDE_SKILL_DIR} Variable](#claude_skill_dir-variable)
- [Choosing the Right Variable](#choosing-the-right-variable)
- [Common Path Issues](#common-path-issues)
- [Real-World Examples](#real-world-examples)
- [Testing Paths During Development](#testing-paths-during-development)
- [Path Resolution Summary](#path-resolution-summary)

## Path Rules Overview

**Critical rule:** All paths in `plugin.json` are relative to plugin root and must start with `./`

| Context | Path Type | Example | Notes |
|---------|-----------|---------|-------|
| **plugin.json fields** | Relative, with `./` | `"./commands/"` | Must start with `./` |
| **Hooks, scripts, services** | Variable + relative | `"${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"` | Use variable for absolute paths |
| **User filesystem** | Installation scope path | `~/.claude/skills/my-plugin/` | Where plugin lives after install |

## Relative Paths in plugin.json

All paths in `plugin.json` are relative to the plugin root directory and MUST start with `./`

### Correct Path Format

```json
{
  "commands": "./commands/",
  "agents": "./agents/",
  "skills": ["./skills/", "./vendor/skills/"],
  "hooks": "./hooks.json",
  "mcpServers": "./.mcp.json",
  "lspServers": "./.lsp.json",
  "outputStyles": "./styles/"
}
```

### Plugin Directory Structure Example

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Paths are relative to my-plugin/
├── commands/
│   └── validate.md
├── agents/
│   └── analyzer.md
├── skills/
│   └── code-review/
│       └── SKILL.md
├── hooks.json
├── .mcp.json
├── scripts/
│   └── format.sh
└── styles/
    └── custom.css
```

**In plugin.json:**
- `"commands": "./commands/"` → points to `my-plugin/commands/`
- `"scripts": "./scripts/format.sh"` → points to `my-plugin/scripts/format.sh`
- `"styles": "./styles/"` → points to `my-plugin/styles/`

## ${CLAUDE_PLUGIN_ROOT} Variable

Use this variable in **hooks, scripts, and MCP server configurations** to get the absolute path to the plugin root.

### Why This Variable Exists

When a plugin is installed, Claude Code copies it to a cache location. The absolute path depends on:
- Installation scope (`~/.claude/skills/` for user, `.claude/skills/` for project)
- Plugin name
- System environment

**Without the variable:** Hard-coded paths would break after installation
**With the variable:** Claude Code expands it to the correct absolute path at runtime

### Where to Use ${CLAUDE_PLUGIN_ROOT}

**Use in these contexts:**
- Hook command paths
- MCP server startup commands
- LSP server commands
- Script references in hooks or inline configurations
- External processes that need absolute paths

**Don't use in:**
- Regular `plugin.json` fields (`commands`, `agents`, `skills`, etc.)
- Internal file references (use relative `./` paths instead)

### Examples with ${CLAUDE_PLUGIN_ROOT}

#### Hooks Example

```json
{
  "hooks": {
    "PostToolUse": [
      {
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

When installed to `~/.claude/skills/my-plugin/`, the variable expands to:
```
${CLAUDE_PLUGIN_ROOT} = ~/.claude/skills/my-plugin
```

Full path becomes: `~/.claude/skills/my-plugin/scripts/format.sh`

#### MCP Server Example

```json
{
  "python-mcp": {
    "command": "python",
    "args": ["${CLAUDE_PLUGIN_ROOT}/mcp_servers/file_handler.py"],
    "env": {
      "PLUGIN_ROOT": "${CLAUDE_PLUGIN_ROOT}"
    }
  }
}
```

The server is launched with:
```bash
python ~/.claude/skills/my-plugin/mcp_servers/file_handler.py
```

#### Skill/Agent Frontmatter Hooks Example (caveat)

`${CLAUDE_PLUGIN_ROOT}` above is documented for a plugin's own `hooks/hooks.json`. It is not confirmed
available inside a SKILL.md/agent frontmatter-embedded `hooks:` block specifically, and a bare relative
path is unsafe there too (hook handlers run in the session's cwd, not the skill's own directory) — see
`hook-development/references/component-scoped-hooks.md`'s "Environment Variables Available" section for
the confirmed-broken case (a project-level skill, no enclosing plugin) and the recommended fix
(`${CLAUDE_PROJECT_DIR}` with the full path from the project root).

#### LSP Server Example

```json
{
  "go": {
    "command": "${CLAUDE_PLUGIN_ROOT}/bin/gopls",
    "args": ["serve"]
  }
}
```

## Installation Path Behavior

After installation, plugins are copied to scope-specific locations. The `${CLAUDE_PLUGIN_ROOT}` variable expands to these paths:

### User Scope (`--scope user`)

**Installation path:** `~/.claude/skills/my-plugin/`

```bash
# Variable expands to:
${CLAUDE_PLUGIN_ROOT} = ~/.claude/skills/my-plugin
```

**Available in:** All projects, all sessions

### Project Scope (`--scope project`)

**Installation path:** `.claude/skills/my-plugin/`

```bash
# Variable expands to:
${CLAUDE_PLUGIN_ROOT} = /full/path/to/project/.claude/skills/my-plugin
```

**Available in:** This project only

### Local Scope (`--scope local`)

**Installation path:** `.claude/skills/my-plugin/`

```bash
# Variable expands to:
${CLAUDE_PLUGIN_ROOT} = /full/path/to/project/.claude/skills/my-plugin
```

**Available in:** This project only (not shared)

### Managed Scope (Marketplace)

**Installation path:** System cache (Claude Code manages this)

```bash
# Variable expands to:
${CLAUDE_PLUGIN_ROOT} = /system/managed/cache/my-plugin
```

**Available in:** All projects (read-only)

## ${CLAUDE_PLUGIN_DATA} Variable

Use this variable for **persistent plugin state that must survive plugin updates** — installed dependencies (`node_modules`, Python virtualenvs), caches, generated code, logs, or databases.

### Why This Variable Exists

`${CLAUDE_PLUGIN_ROOT}` changes every time the plugin updates (the previous version's directory is kept for about seven days before cleanup, then removed). Anything written there is lost on update. `${CLAUDE_PLUGIN_DATA}` resolves to a separate, stable directory that outlives plugin version changes — the right place for state that shouldn't be reinstalled or regenerated every update.

### Resolution

```
${CLAUDE_PLUGIN_DATA} = ~/.claude/plugins/data/{id}/
```

`{id}` is the plugin identifier with any character outside `a-z`, `A-Z`, `0-9`, `_`, `-` replaced by `-`. A plugin installed as `formatter@my-marketplace` resolves to `~/.claude/plugins/data/formatter-my-marketplace/`.

The directory is created automatically the first time this variable is referenced — no setup step needed.

### Example: Persisting Installed Dependencies

```json
{
  "mcpServers": {
    "routines": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server.js"],
      "env": {
        "NODE_PATH": "${CLAUDE_PLUGIN_DATA}/node_modules"
      }
    }
  }
}
```

Because the data directory outlives any single plugin version, a directory-existence check alone can't detect a manifest change on update. Compare the bundled manifest against a copy stored in the data directory, and reinstall when they differ:

```bash
diff -q "${CLAUDE_PLUGIN_ROOT}/package.json" "${CLAUDE_PLUGIN_DATA}/package.json" >/dev/null 2>&1 \
  || (cd "${CLAUDE_PLUGIN_DATA}" && cp "${CLAUDE_PLUGIN_ROOT}/package.json" . && npm install) \
  || rm -f "${CLAUDE_PLUGIN_DATA}/package.json"
```

### Uninstall Behavior

Uninstalling from the last remaining scope deletes `${CLAUDE_PLUGIN_DATA}` by default. Use `--keep-data` to preserve it — for example, when reinstalling after testing a new version.

## ${CLAUDE_PROJECT_DIR} Variable

The project root directory — the same value hooks and MCP servers receive as the `CLAUDE_PROJECT_DIR` environment variable. Use this to reference project-local scripts or config files, independent of where the plugin itself is installed.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PROJECT_DIR}\"/scripts/lint.sh"
          }
        ]
      }
    ]
  }
}
```

Also valid inside a skill's `allowed-tools` frontmatter, so a permission rule and the skill body can reference the identical path: `Bash(${CLAUDE_PROJECT_DIR}/scripts/lint.sh *)`.

**Requires Claude Code v2.1.196 or later.**

## ${CLAUDE_SKILL_DIR} Variable

The directory containing the skill's own `SKILL.md` file. For a plugin skill, this is the **skill's subdirectory within the plugin — not the plugin root**. This is the key difference from `${CLAUDE_PLUGIN_ROOT}`: a plugin can bundle many skills, and `${CLAUDE_SKILL_DIR}` always resolves to the one currently executing, without hardcoding that skill's directory name.

```yaml
---
name: codebase-visualizer
---

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/visualize.py .` to generate the diagram.
```

Works identically whether the skill is installed at the personal, project, or plugin level.

**Scope note:** unlike `${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_DATA}`/`${CLAUDE_PROJECT_DIR}`, this variable is a skill-content substitution only — it is not available in `hooks.json`, MCP server configs, or LSP server configs, since those aren't scoped to a single skill file.

## Choosing the Right Variable

| Need | Variable |
|---|---|
| Reference a script/binary bundled anywhere in the plugin, from a hook/MCP/LSP config | `${CLAUDE_PLUGIN_ROOT}` |
| Reference a file bundled with *this specific skill*, from inside that skill's own SKILL.md/references | `${CLAUDE_SKILL_DIR}` |
| Persist installed dependencies, caches, or generated files across plugin updates | `${CLAUDE_PLUGIN_DATA}` |
| Reference a project-local script or config file, independent of plugin install location | `${CLAUDE_PROJECT_DIR}` |

## Common Path Issues

### Issue 1: Hard-coded Absolute Paths

❌ **WRONG:**
```json
{
  "command": "/Users/jane/projects/my-plugin/scripts/format.sh"
}
```

Why this breaks:
- Path is specific to Jane's machine
- Path doesn't work for other users
- Path doesn't work after installation

✅ **CORRECT:**
```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
}
```

### Issue 2: Relative Paths Without ./

❌ **WRONG (in plugin.json):**
```json
{
  "commands": "commands/",
  "agents": "agents/"
}
```

Why this breaks:
- Claude Code expects paths to start with `./`
- Plugin won't be recognized

✅ **CORRECT:**
```json
{
  "commands": "./commands/",
  "agents": "./agents/"
}
```

### Issue 3: Using ${CLAUDE_PLUGIN_ROOT} in plugin.json

❌ **WRONG:**
```json
{
  "commands": "${CLAUDE_PLUGIN_ROOT}/commands/"
}
```

Why this breaks:
- plugin.json fields don't support variable expansion
- Claude Code handles these paths specially

✅ **CORRECT:**
```json
{
  "commands": "./commands/"
}
```

### Issue 4: Symlinks After Installation

❌ **WRONG:**
```json
{
  "command": "./scripts/../actual-scripts/format.sh"
}
```

Why this breaks:
- Symlinks may not work after plugin is cached/copied
- Plugin root changes on installation

✅ **CORRECT:**
```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
}
```

## Real-World Examples

### Example 1: Python MCP Server

Plugin structure:
```
my-plugin/
├── .claude-plugin/plugin.json
├── mcp_servers/
│   └── database.py
└── requirements.txt
```

Plugin.json MCP configuration:
```json
{
  "mcpServers": {
    "database": {
      "command": "python",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/mcp_servers/database.py"
      ]
    }
  }
}
```

When installed to `~/.claude/skills/my-plugin/`, expands to:
```bash
python ~/.claude/skills/my-plugin/mcp_servers/database.py
```

### Example 2: Bash Script in Hooks

Plugin structure:
```
my-plugin/
├── .claude-plugin/plugin.json
├── hooks.json
└── scripts/
    ├── format.sh
    └── lint.sh
```

Plugin.json hooks configuration:
```json
{
  "hooks": "./hooks.json"
}
```

hooks.json content:
```json
{
  "PostToolUse": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
        },
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/lint.sh"
        }
      ]
    }
  ]
}
```

Hooks execute at:
- User scope: `~/.claude/skills/my-plugin/scripts/format.sh`
- Project scope: `.claude/skills/my-plugin/scripts/format.sh`

### Example 3: Multiple Path Types

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — the section's own point is showing regular, MCP, and LSP path conventions together in one plugin.json; splitting would defeat that.

```json
{
  "name": "code-tools",
  "description": "Multi-tool plugin...",

  // Regular plugin.json paths (relative, with ./)
  "commands": ["./commands/", "./lib/commands/"],
  "agents": "./agents/",
  "skills": "./skills/",
  "hooks": "./hooks.json",

  // MCP configuration with ${CLAUDE_PLUGIN_ROOT}
  "mcpServers": {
    "file-tools": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/file_tools.py"]
    },
    "database": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/database.js"]
    }
  },

  // LSP configuration with ${CLAUDE_PLUGIN_ROOT}
  "lspServers": {
    "go": {
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/gopls",
      "args": ["serve"]
    }
  }
}
```

## Testing Paths During Development

Use `--plugin-dir` to test before installation:

```bash
# Test with relative paths (plugin-dir mode)
claude --plugin-dir /path/to/my-plugin

# Test with installed version
claude plugin install ./my-plugin --scope local
```

During development with `--plugin-dir`:
- `${CLAUDE_PLUGIN_ROOT}` expands to the directory you passed
- Relative paths work from plugin root
- Scripts/hooks execute with correct paths

## Path Resolution Summary

| Path Type | Where Used | Format | Expansion |
|-----------|-----------|--------|-----------|
| **component paths** | plugin.json | `./relative/path` | Plugin root + relative path |
| **script paths** | hooks, MCP | `${CLAUDE_PLUGIN_ROOT}/path` | Installation path + relative path |
| **variable** | runtime | `${CLAUDE_PLUGIN_ROOT}` | Absolute path to plugin (system-dependent) |
| **persistent data** | runtime | `${CLAUDE_PLUGIN_DATA}` | `~/.claude/plugins/data/{id}/` (survives plugin updates) |
| **project-local paths** | hooks, MCP, skill body/allowed-tools | `${CLAUDE_PROJECT_DIR}/path` | Project root + relative path (requires v2.1.196+) |
| **skill-bundled paths** | skill body only | `${CLAUDE_SKILL_DIR}/path` | This skill's own directory + relative path |
| **symlinks** | not recommended | — | Use `${CLAUDE_PLUGIN_ROOT}` instead |
