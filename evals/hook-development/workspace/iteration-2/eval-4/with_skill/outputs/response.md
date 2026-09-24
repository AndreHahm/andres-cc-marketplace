## hooks/hooks.json entry

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
            "timeout": 10,
            "onError": "fail"
          }
        ]
      }
    ]
  }
}
```

Notes on this entry:
- `matcher: "Bash"` is an exact tool-name match, so it fires before every `Bash` call.
- `${CLAUDE_PLUGIN_ROOT}` is used for the script path so the reference stays portable across installs.
- `timeout: 10` gives a script expected to finish in ~5 seconds a safety margin (roughly 2x) without leaving it able to hang for anywhere near the 600-second command default — if `validate.sh` should hard-block execution when it fails, `onError: "fail"` (or `exit 2` from the script itself) is the correct way to actually deny the `Bash` call; `onError: "warn"` would only log a non-blocking warning instead.

## What unit does `timeout` use?

Seconds.

## Default timeout value, per hook type

| Hook type | Default timeout |
|---|---|
| `command` | 600s |
| `http` | 600s |
| `mcp_tool` | 600s |
| `prompt` | 30s |
| `agent` | 60s |

Values outside the 1–600s range should be treated as suspect/likely misconfigured.

## Does any specific hook event override those defaults?

Yes. The 600s default for `command`/`http`/`mcp_tool` hooks is not uniform across every event — Claude Code lowers it in a few specific cases:

- On `UserPromptSubmit`, `PreModelSwitch`, and `PostModelSwitch`, the `command`/`http`/`mcp_tool` default is lowered from 600s to **30s**.
- On `MessageDisplay`, it's lowered to **10s**.
- `SessionEnd` hooks don't get an individual per-hook default at all — all `SessionEnd` hooks sharing that event instead share a single **1.5-second total budget**.

Outside of these named exceptions, the general per-type defaults in the table above apply.

## Are there hook configurations where the timeout value is not actually enforced?

Yes — one specific case: an **async command hook** (`"async": true`). For those, `timeout` is not enforced at all — the background process is not killed if it runs long. Setting `async: true` removes both the blocking wait on the hook's completion *and* the timeout guarantee together; the two are tied to the same mechanism, so you can't keep timeout enforcement while also running the hook in the background. This only applies to command hooks, since `async` is a command-hook-only field. Because of this, async hooks can't be used for anything that needs to return a decision or reliably bound how long it runs — they're appropriate only for fire-and-forget side effects (logging, metrics, webhooks, notifications) where an unbounded run time is acceptable.

For every other (non-async) hook configuration, the `timeout` field is enforced as a normal wall-clock limit: the hook is canceled once it's exceeded, subject to the default (or event-override) values above.
