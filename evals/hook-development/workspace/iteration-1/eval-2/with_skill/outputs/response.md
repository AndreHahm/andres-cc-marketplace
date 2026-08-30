# hooks/hooks.json — Bash guard hook

Since your plugin has `.claude-plugin/plugin.json`, the hook config goes at
**`hooks/hooks.json`** (plugin root), **not** `.claude-plugin/hooks.json`.

## File: `hooks/hooks.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/guard-bash.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

Key points:

- **Event:** `PreToolUse` — fires before the `Bash` tool call executes, so the hook can block it.
- **Matcher:** `"Bash"` — restricts this hook to the Bash tool only (not every tool call).
- **Nested `"hooks": [...]` array:** required inside each matcher entry — this is the #1 JSON
  structural mistake to avoid.
- **`${CLAUDE_PLUGIN_ROOT}`:** always reference the script this way rather than a relative or
  hardcoded path, so the hook resolves correctly regardless of where the plugin is installed.
- **`timeout`:** 5000ms is a reasonable guard for a fast validation script; adjust if
  `guard-bash.sh` needs longer.

## Script contract: `scripts/guard-bash.sh`

The hook only wires the script in — it doesn't validate anything itself. `guard-bash.sh` must:

1. **Read the event data from stdin as JSON** (not environment variables — this is the #1 reason
   command hooks silently do nothing):

   ```bash
   #!/bin/bash
   INPUT=$(cat)
   COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')
   ```

2. **Decide if the command is dangerous** (e.g. pattern-match `COMMAND` against a denylist such as
   `rm -rf /`, `git push --force`, `:(){ :|:& };:`, etc. — implement whatever "dangerous" means for
   your use case).

3. **Block via exit code, not stdout text:**
   - **Exit code `0`** — allow the command to proceed.
   - **Exit code `2`** — block the tool call. Claude Code reads `stderr` as the reason shown back
     to the model/user, so write the block reason there:

     ```bash
     if is_dangerous "$COMMAND"; then
       echo "Blocked: command matches a dangerous pattern ($COMMAND)" >&2
       exit 2
     fi

     exit 0
     ```
   - Any other non-zero exit code is treated as a non-blocking error (shown as a warning, but the
     tool call still proceeds) — for a hard block, exit code `2` specifically is what you want.

4. Make the script executable (`chmod +x scripts/guard-bash.sh`) so it can run directly.

## Resulting layout

```
your-plugin/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
└── scripts/
    └── guard-bash.sh
```

## Before finalizing

- Validate the JSON structure (`jq . hooks/hooks.json` or `scripts/validate-hook-schema.sh` if
  available in this repo's plugin-devkit tooling).
- Test the hook end-to-end with `scripts/test-hook.sh` (or a manual `echo '<fake event json>' |
  scripts/guard-bash.sh; echo $?`) to confirm it exits `2` for a dangerous command and `0` for a
  safe one.
- Run `shellcheck scripts/guard-bash.sh` to catch quoting/parsing bugs in the script itself.
