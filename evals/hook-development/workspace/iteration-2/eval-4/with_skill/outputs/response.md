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
- `command` uses `${CLAUDE_PLUGIN_ROOT}` so the path to `scripts/validate.sh` resolves correctly wherever the plugin is installed.
- `timeout: 10` gives a script expected to finish in ~5 seconds a reasonable safety margin (2x) without allowing a hang to block the session for long — well within the valid 1-600s range.

## Timeout Field: Unit and Defaults

- **Unit:** seconds (not milliseconds) — it is the number of seconds Claude Code waits before canceling the hook.
- **Defaults**, which apply when `timeout` is omitted, vary by hook type:
  - `command` hooks: **600** seconds
  - `prompt` hooks: **30** seconds
  - `agent` hooks: **60** seconds
- Values outside the 1-600 second range should be treated as suspect/invalid.

Since `scripts/validate.sh` is expected to complete in about 5 seconds, an explicit `timeout` of `10` is appropriate here — it overrides the much larger 600-second command-hook default while still leaving headroom above the script's expected runtime.
