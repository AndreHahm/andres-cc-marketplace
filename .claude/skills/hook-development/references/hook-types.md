# Hook Types

Full field reference and example configuration for each hook action type. For which type to pick, see the "Type decision" table in `SKILL.md`'s Hook Types section. For the `mcp_tool` type specifically, see `references/mcp-tools.md` — it has its own dedicated, more detailed reference.

## Prompt-Based (Recommended)

LLM-driven decision making for context-aware validation:

```json
{
  "type": "prompt",
  "prompt": "Evaluate if this tool use is appropriate: $TOOL_INPUT",
  "timeout": 30
}
```

Best for: flexible logic, edge cases, natural language reasoning, easy maintenance.

## Command

Bash execution for deterministic checks:

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
  "timeout": 60
}
```

Best for: fast deterministic validations, file system checks, external tool integrations.

## Agent-Based

Multi-turn subagent with Read/Grep/Glob/Bash access for checks requiring file inspection:

```json
{
  "type": "agent",
  "prompt": "Verify all unit tests pass. Run the test suite and check results. $ARGUMENTS",
  "timeout": 120
}
```

Returns `{"ok": true}` or `{"ok": false, "reason": "..."}`. Default timeout: 60s; up to 50 tool-use turns.

## HTTP

Posts event data to a webhook endpoint:

```json
{
  "type": "http",
  "url": "https://example.com/hook",
  "timeout": 10
}
```

Cannot block via a non-2xx status code — to block, the endpoint must return `2xx` with a valid JSON decision body (see `references/exit-code-behavior.md`).

## MCP Tool

Calls an installed MCP server tool as the hook action. Requires `server` and `tool` — see `references/mcp-tools.md` for the full field reference, JSON example, and how it differs from *matching* MCP tool calls with `matcher`.
