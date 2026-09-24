# `hooks/hooks.json` — PreToolUse Bash validation hook

```json
{
  "description": "Validate Bash commands before execution",
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

Notes on this entry:

- The event is `PreToolUse` so the hook runs **before** the `Bash` tool call executes and can block it (exit code `2`).
- `matcher` is the exact tool name `"Bash"` (case-sensitive) — this runs the hook before every Bash call, not a regex subset of commands.
- The script path uses `${CLAUDE_PLUGIN_ROOT}` for a portable, distributable reference rather than a hardcoded path.
- `timeout: 10` — for a script that should normally complete in ~5 seconds, a value of roughly double the expected runtime (here, 10s) is the reasonable choice: it's comfortably above the expected 5s so normal runs never get killed by transient slowness, while still being far below the 600s default so a genuinely hung/broken script is caught quickly rather than stalling the tool call for ten minutes. Per the skill's own guidance, timeout values should be flagged as suspect outside the 1–600 second range, and a timeout that's needlessly far beyond what the script actually needs is itself a smell to avoid.
- `onError: "warn"` is included so a validation failure is surfaced without crashing the whole plugin (adjust to `"block"`-style handling via exit code 2 if this hook should actually deny the Bash call on failure, per the hook's own logic).

## `timeout` field: unit and defaults

**Unit:** the `timeout` field is expressed in **seconds** (not milliseconds).

**Default value per hook type:**

| Hook type | Default timeout |
|---|---|
| `command` | 600s |
| `http` | 600s |
| `mcp_tool` | 600s |
| `prompt` | 30s |
| `agent` | 60s (also caps at up to 50 tool-use turns) |

Values well outside the 1–600 second range should be treated as suspect regardless of hook type.

## Event-specific overrides

Yes — several specific hook events override the general `command`/`http`/`mcp_tool` default of 600s:

- **`UserPromptSubmit`, `PreModelSwitch`, and `PostModelSwitch`** — Claude Code lowers the `command`/`http`/`mcp_tool` default timeout to **30 seconds** for hooks on these events.
- **`MessageDisplay`** — lowers the `command`/`http`/`mcp_tool` default timeout to **10 seconds**.
- **`SessionEnd`** — hooks on this event don't get their own individual default; instead, all `SessionEnd` hooks collectively share a single **1.5-second total budget**.

So a hook's effective default timeout depends on both its `type` and the specific `event` it's attached to — the general per-type table above is the baseline, and these four events are the documented exceptions to it.
