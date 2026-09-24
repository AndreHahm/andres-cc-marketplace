# PreToolUse Bash Validation Hook

`hooks/hooks.json`:

```json
{
  "description": "Validate before every Bash call",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
            "timeout": 10,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

Notes on this configuration:
- `matcher: "Bash"` scopes the hook to only the `Bash` tool (exact tool name match), so it fires before every Bash call rather than every tool call.
- `command` uses `${CLAUDE_PLUGIN_ROOT}` so the path to `scripts/validate.sh` resolves correctly wherever the plugin is installed, regardless of where the hook actually runs from.
- `timeout: 10` gives a script expected to finish in ~5 seconds a reasonable safety margin (2x) without allowing a hang to block the session for long — well within the valid 1-600s range, and an explicit override of the much larger 600-second command-hook default described below.

## Timeout Field: Unit and Defaults

- **Unit:** seconds (not milliseconds) — it is the number of seconds Claude Code waits before canceling the hook and treating it as timed out.
- **Default value, per hook type**, which applies whenever `timeout` is omitted from a handler:
  - `command` hooks: **600** seconds
  - `http` hooks: **600** seconds
  - `mcp_tool` hooks: **600** seconds
  - `prompt` hooks: **30** seconds
  - `agent` hooks: **60** seconds
- Values outside the 1-600 second range should be treated as suspect/invalid.

### Event-specific overrides of those defaults

Yes — for `command`/`http`/`mcp_tool` hooks (whose baseline default is 600s), certain hook events lower that default:
- `UserPromptSubmit`, `PreModelSwitch`, and `PostModelSwitch` hooks: default lowered to **30** seconds.
- `MessageDisplay` hooks: default lowered to **10** seconds.
- `SessionEnd` hooks: no single per-hook default — instead, all `SessionEnd` hooks together share a combined **1.5-second total budget**.

These are defaults only; an explicit `timeout` field on a given handler (as used above, `10`) always overrides whatever the type/event default would otherwise be.

Since `scripts/validate.sh` is expected to complete in about 5 seconds, an explicit `timeout` of `10` is appropriate here — it overrides the much larger 600-second command-hook default for `PreToolUse` (which has no lower event-specific override) while still leaving reasonable headroom above the script's expected runtime.
