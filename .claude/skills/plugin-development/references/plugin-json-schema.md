# plugin.json Schema Reference

Terse, example-first field reference for Claude Code plugin manifests — for the complete field-by-field reference (including `defaultEnabled`, `dependencies`, version-resolution fallback chain, and path-resolution rules), see `manifest-reference.md`.

## Location

`.claude-plugin/plugin.json` (required file)

## Required Fields

### name

**Type**: string
**Required**: Yes
**Format**: kebab-case (lowercase with hyphens)

Plugin identifier used for installation.

```json
{
  "name": "my-plugin"
}
```

**Rules**:
- Must be unique
- Use lowercase
- Use hyphens (not underscores or spaces)
- No special characters

## Recommended Fields

### version

**Type**: string
**Format**: Semantic versioning (MAJOR.MINOR.PATCH)

```json
{
  "version": "1.2.3"
}
```

Examples: `1.0.0`, `2.1.3-beta`, `3.0.0-rc.1`

### description

**Type**: string
**Recommended length**: Under 200 characters

Brief explanation of plugin functionality.

```json
{
  "description": "Development and deployment tools for teams"
}
```

### author

**Type**: object

Plugin creator information.

```json
{
  "author": {
    "name": "Your Name",
    "email": "you@example.com",
    "url": "https://example.com"
  }
}
```

Fields:
- `name` (string): Author name
- `email` (string, optional): Contact email
- `url` (string, optional): Website or profile URL

## Optional Fields

### homepage

**Type**: string (URL)

Plugin documentation or homepage.

```json
{
  "homepage": "https://github.com/user/plugin"
}
```

### repository

**Type**: string (URL)

Source code repository.

```json
{
  "repository": "https://github.com/user/plugin"
}
```

### license

**Type**: string (SPDX identifier)

License identifier.

```json
{
  "license": "MIT"
}
```

Common: `MIT`, `Apache-2.0`, `GPL-3.0`, `BSD-3-Clause`

### keywords

**Type**: array of strings

Searchability and discoverability tags.

```json
{
  "keywords": ["deployment", "ci-cd", "automation"]
}
```

## Component Path Fields

### skills

**Type**: string or array

Path to skills directory or specific skill files.

```json
{
  "skills": "./skills/"
}
```

Or multiple paths:
```json
{
  "skills": ["./skills/", "./custom-skills/"]
}
```

### commands

**Type**: string or array

Path to slash command files.

```json
{
  "commands": "./commands/"
}
```

### agents

**Type**: string or array

Path to agent markdown files.

```json
{
  "agents": "./agents/"
}
```

### hooks

**Type**: string or object

Path to hooks configuration or inline hooks.

```json
{
  "hooks": "./hooks/hooks.json"
}
```

Or inline:
```json
{
  "hooks": {
    "pre_request": "validate_request.sh"
  }
}
```

### mcpServers

**Type**: string or object

Path to MCP server config or inline config.

```json
{
  "mcpServers": "./mcp-config.json"
}
```

## Path Rules

**All paths must**:
- Be relative (not absolute)
- Start with `./`
- Use forward slashes (cross-platform)

**Variable**: `${CLAUDE_PLUGIN_ROOT}` resolves to plugin absolute path

## Complete Example

```json
{
  "$schema": "https://anthropic.com/schemas/plugin.json",
  "name": "enterprise-toolkit",
  "version": "2.1.0",
  "description": "Deployment and automation suite for enterprise teams",
  "author": {
    "name": "DevOps Team",
    "email": "devops@company.com",
    "url": "https://company.com/devops"
  },
  "homepage": "https://github.com/company/enterprise-toolkit",
  "repository": "https://github.com/company/enterprise-toolkit",
  "license": "Apache-2.0",
  "keywords": ["deployment", "ci-cd", "automation", "enterprise"],
  "skills": "./skills/",
  "commands": ["./commands/", "./specialized/deploy.md"],
  "agents": "./custom-agents/"
}
```

## Validation

Use `validate_plugin.py` to check:
- JSON syntax
- Required fields present
- Field format correctness
- Path validity

```bash
python scripts/validate_plugin.py my-plugin/
```
