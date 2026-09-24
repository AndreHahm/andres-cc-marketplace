# hooks/hooks.json — PreToolUse validation before every Bash call

```json
{
  "description": "Validate every Bash call before it runs",
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

Notes on this example:
- `matcher: "Bash"` restricts the hook to the `Bash` tool only (exact tool-name match, case-sensitive).
- `${CLAUDE_PLUGIN_ROOT}` is used for the script path so it resolves correctly wherever the plugin is installed.
- `timeout: 10` — set to roughly 2x the script's expected ~5s runtime rather than exactly 5s, so normal variance (slow disk, cold cache, etc.) doesn't trip a false timeout on a script that's merely "about 5 seconds," not a hard-capped 5.000s. Anything under the ~600s command default but comfortably above the expected runtime is reasonable; 10s is a sensible choice here.
- `onError: "warn"` is a reasonable default for a validation gate that shouldn't hard-fail the whole session on an unexpected non-zero/non-two exit; adjust to `"fail"` if this check must be strictly enforced.

---

## Answers

**(1) What unit does the `timeout` field use?**

Seconds. (Not milliseconds — this is worth calling out explicitly because the `Bash` *tool's own* `tool_input.timeout` field, which a command hook might read from stdin, is in milliseconds; the hook handler's own `timeout` field is a different field, in seconds.)

**(2) Default value for every hook type:**

| Hook type | Default timeout |
|---|---|
| `command` | 600 seconds |
| `http` | 600 seconds |
| `mcp_tool` | 600 seconds |
| `prompt` | 30 seconds |
| `agent` | 60 seconds |

**(3) Does any specific hook event override those defaults?**

Yes. Claude Code lowers the `command`/`http`/`mcp_tool` default of 600s in a few specific cases:
- `UserPromptSubmit`, `PreModelSwitch`, and `PostModelSwitch` — default lowered to 30 seconds.
- `MessageDisplay` — default lowered to 10 seconds.
- `SessionEnd` — hooks share a combined 1.5-second **total** budget (not a per-hook 1.5s each).

These are event-specific overrides of the type-level defaults in (2), not changes to the `prompt`/`agent` defaults.

**(4) Does an explicit `timeout` value always apply, or is there a hook configuration where Claude Code doesn't enforce it at all?**

An explicit `timeout` is always enforced, including for `async: true` command hooks. Async hooks run in the background and don't block Claude Code's execution or return a decision, but the skill's own reference material states explicitly: "Timeout still enforced but doesn't slow Claude Code" — the process is still killed if it exceeds the configured timeout; the difference is only that the *caller* doesn't wait on it synchronously. So there is no documented hook configuration in this skill's references where the timeout is simply not enforced at all — the caveat with async hooks is about blocking behavior, not about the timeout being skipped.

One related caveat worth noting: on timeout, the process is killed and the outcome is treated as exit code 2 (blocking error) specifically for `PreToolUse`, and as a non-blocking error for other events — so "the timeout applies" doesn't always mean "the action gets blocked," only that the hook process itself is terminated and reported.
