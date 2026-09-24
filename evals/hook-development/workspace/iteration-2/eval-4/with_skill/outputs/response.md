## hooks/hooks.json — PreToolUse command hook for Bash

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

The `matcher` is set to `Bash` (exact tool name, case-sensitive) so the hook only fires before `Bash` tool calls, and the handler is a `command` type pointing at `scripts/validate.sh` via `${CLAUDE_PLUGIN_ROOT}` (portable for a distributed plugin). `timeout` is set to `10` seconds: the script itself should complete in about 5 seconds, so 10 gives a reasonable buffer above the expected runtime without leaving it so high that a genuinely hung script blocks the tool call for a long time.

## What unit does `timeout` use?

Seconds.

## Default `timeout` value per hook type

| Hook type | Default timeout |
|---|---|
| `command` | 600 seconds |
| `http` | 600 seconds |
| `mcp_tool` | 600 seconds |
| `prompt` | 30 seconds |
| `agent` | 60 seconds |

`command`, `http`, and `mcp_tool` share the same general default (600s); `prompt` defaults to 30s; `agent` defaults to 60s (with up to 50 tool-use turns).

## Does any specific hook event override those defaults?

Yes. The 600-second `command`/`http`/`mcp_tool` default is not universal — Claude Code lowers it for certain events:

- On `UserPromptSubmit`, `PreModelSwitch`, and `PostModelSwitch`, the `command`/`http`/`mcp_tool` default is lowered from 600s to **30 seconds**.
- On `MessageDisplay`, it's lowered further, to **10 seconds**.
- `SessionEnd` hooks don't get an individual per-hook default at all — they share a **1.5-second total budget** across the event.

The `prompt` (30s) and `agent` (60s) defaults aren't documented as having per-event overrides of this kind.

## Are there hook configurations where the `timeout` value is not actually enforced?

Yes, one specific case: a **command hook running in plain background mode** — `async: true` set, and `asyncRewake` either omitted or `false`. In that configuration, Claude Code does not enforce the configured `timeout` at all; the hook can run indefinitely in the background without being killed, and it delivers its output on a later turn rather than blocking the current one. Because of this, a plain async hook must never be relied on for a safety gate, and if the script itself needs a runtime cap, that cap has to be implemented inside the script (e.g. a `timeout` shell wrapper), not via the hook's own `timeout` field.

This exception is narrow and doesn't apply to:
- A normal synchronous hook (no `async`) — `timeout` is enforced as usual; the process is killed if it exceeds the value.
- A hook with `async: true` **and** `asyncRewake: true` — it still runs in the background (non-blocking, output delivered later, and it can wake Claude when it exits with code 2), but Claude Code *does* still enforce `timeout` on it and will kill it if it runs past that value.

So the distinguishing factor isn't "is it async" by itself — it's specifically plain `async: true` without `asyncRewake: true` that drops timeout enforcement; adding `asyncRewake: true` restores it while keeping the background/non-blocking behavior.
