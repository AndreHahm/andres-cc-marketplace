---
name: mcp-integration
description: >-
  Configures and integrates MCP servers in Claude Code plugins. Covers server
  types (stdio, SSE, HTTP, WebSocket), .mcp.json and plugin.json setup,
  CLAUDE_PLUGIN_ROOT path handling, MCP tool naming, pre-allowing tools in
  commands, OAuth and token authentication, and integration testing with /mcp
  and claude --debug. Use when adding an MCP server to a plugin, integrating
  MCP into Claude Code, configuring .mcp.json, setting up Model Context Protocol,
  or connecting an external service via stdio, SSE, HTTP, or WebSocket.
allowed-tools: Read Write Edit Glob
---

# MCP Integration for Claude Code Plugins

Model Context Protocol (MCP) enables Claude Code plugins to integrate with external
services and APIs by providing structured tool access. Use MCP integration to expose
external service capabilities as tools within Claude Code.

**Key capabilities:**
- Connect to external services (databases, APIs, file systems)
- Provide 10+ related tools from a single service
- Handle OAuth and complex authentication flows
- Bundle MCP servers with plugins for automatic setup

## Quick Start

1. **Choose server type** — stdio (local process) or SSE/HTTP/WS (hosted service)
2. **Create `.mcp.json`** at plugin root with server configuration (use `$CLAUDE_PLUGIN_ROOT` for all paths)
3. **Document required env vars** in plugin README
4. **Test locally** — run `/mcp` to verify server appears, then test a tool call
5. **Pre-allow MCP tools** in relevant command frontmatter using exact tool names from `/mcp`
6. **Test error cases** — connection failure and auth failure before publishing

## When to Use

- Adding a new MCP server to a Claude Code plugin
- Connecting to an external API, database, or hosted service
- Exposing 10+ related tools from a single backend service
- Implementing OAuth or token-based authentication flows

## When NOT to Use

- For simple bash scripts or file operations — use command hooks instead
- When fewer than 3–4 tools are needed — inline `allowed-tools: Bash(cmd:*)` is simpler
- For read-only reference data — use `@file` injection in commands instead

---

## MCP Server Configuration Methods

Plugins can bundle MCP servers in two ways: plugin-root `.mcp.json` or inline in `plugin.json`. Both auto-start when the plugin is enabled — use `${CLAUDE_PLUGIN_ROOT}` for all bundled server commands and configuration file paths.

### Method 1: Dedicated .mcp.json (Recommended)

Create `.mcp.json` at plugin root:

```json
{
  "database-tools": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
    "env": {
      "DB_URL": "${DB_URL}"
    }
  }
}
```

Best for multiple servers; clearer separation of concerns; easier to maintain.

### Method 2: Inline in plugin.json

Add `mcpServers` field to plugin.json:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

Best for simple single-server plugins where one config file is preferred.

---

## MCP Server Types

| Type | Transport | Best For | Auth |
|------|-----------|----------|------|
| stdio | Process stdin/stdout | Local tools, custom servers | Env vars |
| SSE | HTTP streaming | Hosted services, cloud APIs | OAuth |
| HTTP | REST | API backends, token auth | Tokens |
| ws | WebSocket | Real-time, streaming | Tokens |

### stdio (Local Process)

Execute local MCP servers as child processes. Claude Code spawns, manages, and
terminates the process; communicates via stdin/stdout.

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": { "LOG_LEVEL": "debug" }
  }
}
```

### SSE (Server-Sent Events)

Connect to hosted MCP servers. OAuth flows handled automatically by Claude Code —
user authenticates in browser on first use.

```json
{
  "asana": {
    "type": "sse",
    "url": "https://mcp.asana.com/sse"
  }
}
```

### HTTP (REST API)

Connect with token authentication via request headers.

```json
{
  "api-service": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}"
    }
  }
}
```

### WebSocket (Real-time)

For persistent connections with real-time data streaming.

```json
{
  "realtime-service": {
    "type": "ws",
    "url": "wss://mcp.example.com/ws",
    "headers": {
      "Authorization": "Bearer ${TOKEN}"
    }
  }
}
```

For per-type deep dives, config fields, and edge cases, see `references/server-types.md`.
For OAuth, token, and environment variable auth patterns, see `references/authentication.md`.

---

## Environment Variable Expansion

All MCP configurations support environment variable substitution:

- **`${CLAUDE_PLUGIN_ROOT}`** — always use for plugin file references in JSON configs (portability across installations). In shell environments, `$CLAUDE_PLUGIN_ROOT` is equivalent.
- **User env vars** — e.g., `"API_KEY": "${MY_API_KEY}"` — passed from user's shell environment

Document all required environment variables in the plugin README.

---

## MCP Tool Naming

Tools from MCP servers are automatically prefixed:

**Format:** `mcp__plugin_<plugin-name>_<server-name>__<tool-name>`

**Example:**
- Plugin: `asana`, Server: `asana`, Tool: `create_task`
- **Full name:** `mcp__plugin_asana_asana__asana_create_task`

Run `/mcp` after connecting to see exact tool names.

**Use the full name everywhere** — permission rules, skill `allowed-tools`, and agent `tools` — not just command frontmatter.

### Pre-allowing in Commands

```markdown
---
allowed-tools: [
  "mcp__plugin_asana_asana__asana_create_task",
  "mcp__plugin_asana_asana__asana_search_tasks"
]
---
```

**Wildcard (use sparingly):** `"mcp__plugin_asana_asana__*"` — prefer explicit tool names for security.

For patterns using MCP tools in commands and agents, see `references/tool-usage.md`.

---

## Lifecycle Management

1. Plugin loads → MCP configuration parsed
2. Server process started (stdio) or connection established (SSE/HTTP/WS)
3. Tools discovered and registered as `mcp__plugin_...__...`
4. Tools available in commands and agents

**Notes:**
- Use `/mcp` to see all registered servers and their tools
- Restart Claude Code after configuration changes
- stdio servers terminate when Claude Code exits

---

## Integration Patterns

### Pattern 1: Simple Tool Wrapper

Command with validation before MCP call:

```markdown
---
allowed-tools: ["mcp__plugin_name_server__create_item"]
---
Gather item details from user, validate inputs, then use mcp__plugin_name_server__create_item.
```

### Pattern 2: Autonomous Agent

Agent using MCP tools in a multi-step workflow without user interaction:

```markdown
---
name: db-insights
description: Use when the user asks to "generate database report" or "analyze query data"
model: inherit
---

Query recent data via mcp__plugin_myplug_database__query using the filters
provided. Analyze the results for trends and anomalies. Generate a structured
insights report with findings and recommendations. Present a summary to the user.
```

### Pattern 3: Multi-Server Plugin

Integrate multiple hosted services in one plugin's `.mcp.json`:

```json
{
  "github": { "type": "sse", "url": "https://mcp.github.com/sse" },
  "jira":   { "type": "sse", "url": "https://mcp.jira.com/sse" }
}
```

Command that uses tools from both servers:

```markdown
---
allowed-tools: [
  "mcp__plugin_devtools_github__create_pull_request",
  "mcp__plugin_devtools_jira__create_issue"
]
---
Create a GitHub PR for the staged changes, then open a linked Jira issue for
tracking. Use mcp__plugin_devtools_github__create_pull_request with branch
details, then mcp__plugin_devtools_jira__create_issue with the PR URL in the
description field.
```

---

## Security Best Practices

**DO:**
- Use `${CLAUDE_PLUGIN_ROOT}` for all plugin file path references
- Use environment variables for tokens: `"Authorization": "Bearer ${API_TOKEN}"`
- Use HTTPS/WSS for all remote connections
- Pre-allow specific MCP tools in commands (not wildcards)
- Document all required env vars in README

**DON'T:**
- Hardcode tokens or credentials in configuration files
- Commit credentials to git
- Use `http://` or `ws://` for remote MCP servers
- Use `mcp__plugin_...__*` wildcards unless truly necessary

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Server not connecting | URL correct? Server running (stdio)? Network accessible? |
| Tools missing from `/mcp` | Server connected? Restart Claude Code after config change. |
| Auth failing | Env vars set? Token scope correct? Clear cached OAuth tokens and retry. |
| `${CLAUDE_PLUGIN_ROOT}` not expanding | `.mcp.json` at plugin root? Plugin installed (not just cloned)? |
| Tool call errors | Validate inputs. Check rate limits / quotas. Review `claude --debug` logs. |

Enable debug logging with `claude --debug` — look for MCP server connection, tool discovery, and auth flow log entries.

---

## Testing & Validation

After configuring MCP integration:

1. **JSON syntax** — `jq empty .mcp.json && echo "Valid"` before testing anything else
2. **Server registration** — run `/mcp`; confirm server name and all expected tools appear
3. **Tool call test** — invoke a command that uses an MCP tool; verify it succeeds end-to-end
4. **Auth test** — for OAuth: trigger first-use browser flow; for tokens: confirm env var is read
5. **Error case** — stop the server (stdio) or use a bad URL; confirm a clear failure message

**Quality gates:**
- [ ] `/mcp` shows server and all expected tools
- [ ] At least one tool call succeeds end-to-end
- [ ] Required env vars documented in README
- [ ] No hardcoded credentials in `.mcp.json` or `plugin.json`
- [ ] HTTPS/WSS used for all remote servers (not HTTP/WS)
- [ ] Specific tools pre-allowed in commands (not wildcards)

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/server-types.md` | Deep dive on each server type — config fields, edge cases |
| `references/authentication.md` | OAuth, token, and env var auth patterns |
| `references/tool-usage.md` | Using MCP tools in commands and agents |
| `examples/stdio-server.json` | Working stdio server configuration |
| `examples/sse-server.json` | Working SSE server with OAuth |
| `examples/http-server.json` | Working HTTP server with token auth |
