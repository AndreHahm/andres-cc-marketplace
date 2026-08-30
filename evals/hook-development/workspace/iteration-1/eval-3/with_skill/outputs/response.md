# Why your hook never fires / never gets the right data

You've actually got two separate bugs, both covered directly by the `hook-development` skill's "CRITICAL" callouts. Either one alone would break the hook; together they guarantee it does nothing useful.

## Bug 1: Wrong file location — `.claude-plugin/hooks.json`

This is the single most common mistake in plugin hook setup, and it's likely why the hook **never fires at all**.

- `.claude-plugin/` is reserved for `plugin.json` only.
- Your `hooks.json` must live at **`hooks/hooks.json`**, relative to the plugin root — a sibling of `.claude-plugin/`, not inside it.

```
your-plugin/
├── .claude-plugin/
│   └── plugin.json        ✅ belongs here
├── hooks/
│   └── hooks.json         ✅ hooks.json belongs HERE
```

Claude Code's plugin loader only looks for hook configuration at `hooks/hooks.json`. A file sitting in `.claude-plugin/hooks.json` is simply never read — there's no error, no warning, it's just silently ignored. That matches your symptom of the hook "never firing."

(This location rule is specific to **plugin** projects — i.e. any project that has a `.claude-plugin/plugin.json`. If you were instead configuring hooks for a regular, non-plugin project, the correct file would be `.claude/hooks.json` — but since you're inside a plugin, `hooks/hooks.json` is the one you need.)

**Fix:** move the file:
```bash
mkdir -p hooks
git mv .claude-plugin/hooks.json hooks/hooks.json
```
(or just create it fresh at `hooks/hooks.json` and delete the old one.)

## Bug 2: Reading `$FILE_PATH` as an environment variable

Even once the file is in the right place, your script itself has a second, independent bug. Claude Code does **not** inject event data (like the file path) as environment variables into your hook command. There's no `${arguments.file_path}`-style substitution and no `$FILE_PATH` env var set for you.

```json
// ❌ WRONG — this does nothing; there is no such env-var substitution mechanism
{ "env": {"FILE_PATH": "${arguments.file_path}"} }
```

Instead, **all event data is passed as a single JSON blob on stdin.** Your PostToolUse script needs to read stdin, parse it as JSON, and pull the fields it needs out of that structure — typically with `jq`.

```bash
#!/bin/bash
INPUT=$(cat)                                          # read the full JSON event payload
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

# ... now use $FILE_PATH / $TOOL_NAME as normal
```

For a `PostToolUse` hook specifically, the relevant path is nested under `tool_input` (and for some tools, also worth checking `tool_response`) — so `jq -r '.tool_input.file_path'` is the right extraction, not a bare env var lookup.

**Fix:** rewrite your script to `cat` stdin, parse it with `jq`, and pull `file_path` (and anything else you need, like `tool_name`) out of the parsed JSON rather than expecting an environment variable.

## Summary — two independent fixes needed

| Problem | Symptom | Fix |
|---|---|---|
| `hooks.json` at `.claude-plugin/hooks.json` | Hook never fires at all | Move to `hooks/hooks.json` |
| Script reads `$FILE_PATH` as an env var | Even if it fired, it would never get the right data | `cat` stdin, parse JSON with `jq`, e.g. `jq -r '.tool_input.file_path'` |

Once the file is relocated to `hooks/hooks.json` **and** the script is switched to reading stdin/JSON instead of an env var, the PostToolUse hook should both trigger correctly and receive the correct `file_path`.

## Suggested verification

After making both fixes, use the skill's validation tooling to confirm before relying on it in real sessions:
- `scripts/validate-hook-schema.sh` — checks `hooks/hooks.json` structure is well-formed.
- `scripts/test-hook.sh` — simulates an event and confirms your script reads stdin correctly and produces the expected output.
- `scripts/hook-linter.sh` / `shellcheck` on the hook script itself — catches other shell-scripting issues (quoting, `jq` error handling, etc.) before it runs for real.
