# PreToolUse Hook: Python validation on Write/Edit

Plan (per `hook-development`'s Quick Start / Implementation Workflow):
1. Detect project type → has a plugin, so hooks go in `hooks/hooks.json` at the plugin root.
2. Event: `PreToolUse` (blocks before the tool runs) → matcher `^(Write|Edit)$`.
3. Hook type: `command` (deterministic Python script, not LLM reasoning).
4. Use the nested `"hooks": [...]` array (required structure).
5. Script reads all event data from stdin as JSON (never env vars).
6. Per Pattern 11 (Cross-Platform Python Hook) in `references/patterns-and-templates.md`, any
   hook invoked via a bare `hooks.json` command path must use the `uv` → `python3` → `python`
   runner fallback with graceful degradation — this is required, not optional. Picked the
   **inline `command` cascade** shape (not the two-file `.sh` wrapper) since this is a single,
   straightforward script with no extra wrapper-level logic needed.
7. File references use `${CLAUDE_PLUGIN_ROOT}`.
8. Exit code contract: `0` = pass, `2` = block (stderr shown to Claude).

---

## File: `hooks/hooks.json`

```json
{
  "description": "Validation hooks for this plugin",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "if command -v uv >/dev/null 2>&1; then exec uv run --no-project \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; elif command -v python3 >/dev/null 2>&1; then exec python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; elif command -v python >/dev/null 2>&1; then exec python \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; else exit 0; fi",
            "timeout": 5,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

Notes on this entry:
- The nested `"hooks": [...]` array inside the matcher object is required — omitting it produces
  `"Expected array, but received undefined"`.
- The `command` string is the inline fallback cascade from Pattern 11: try `uv run --no-project`
  first, then `python3`, then `python`, and `exit 0` (pass through, don't crash) if none of the
  three interpreters exist on `PATH`. Using `exec` replaces the shell process so stdin passes
  through to the Python script automatically — no manual buffering needed.
- `timeout: 5` follows the Performance & Safety guidance ("each hook should complete in under 5
  seconds").
- `onError: "warn"` means an unexpected script crash (not an intentional `exit 2`) is logged as a
  warning rather than treated as a hard hook failure — this does not affect the script's own
  `exit 2` blocking path, which is handled by the Exit Codes contract regardless of `onError`.
- Matcher `^(Write|Edit)$` matches exactly the `Write` or `Edit` tool names, per the Common
  Matcher Patterns table.

---

## File: `scripts/my-hook.py`

```python
#!/usr/bin/env python3
"""PreToolUse hook: validates Write/Edit calls before they run.

Reads the full event JSON from stdin (never from environment variables —
hooks.json's env-var substitution does not work for tool_input fields).
Exit 0 to allow the tool call; exit 2 to block it (stderr is shown to Claude).
"""
import json
import sys
from pathlib import Path

# Read all event data from stdin as JSON.
try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError) as exc:
    # Malformed input — fail open (don't block on a parsing problem, per the
    # graceful-degradation requirement for hook scripts).
    print(f"my-hook: could not parse stdin as JSON ({exc}) — skipping", file=sys.stderr)
    sys.exit(0)

tool_name = data.get("tool_name", "")
file_path_str = data.get("tool_input", {}).get("file_path", "")
file_path = Path(file_path_str) if file_path_str else None

# --- Validation logic goes here ---
# Replace this placeholder with the actual check this hook needs to perform.
# Example shape: reject writes outside the project, reject a forbidden
# filename, reject content that fails a policy check, etc.
bad_result = False
reason = ""

if file_path is not None and ".." in file_path.parts:
    bad_result = True
    reason = f"path traversal ('..') detected in file_path: {file_path}"

# --- End validation logic ---

if bad_result:
    print(f"Blocked {tool_name}: {reason}", file=sys.stderr)
    sys.exit(2)  # Block — stderr is fed to Claude so it can understand and fix it

sys.exit(0)  # Pass — allow the tool call to proceed
```

Notes on this script:
- Reads stdin via `json.load(sys.stdin)` — the `#1 reason command hooks silently do nothing` per
  the skill is expecting env vars instead of stdin; this avoids that mistake entirely.
- Uses `pathlib.Path` for the file path per the skill's cross-platform guidance ("use
  `pathlib.Path` for all paths — never hardcode `/tmp/` or OS-specific separators").
- No `subprocess`/`shell=True` usage, so there's no shell-injection surface from the untrusted
  `tool_input` content — consistent with "never interpolate raw input into shell commands."
- The placeholder validation (path-traversal check) is a stand-in "bad result" condition —
  swap in whatever the plugin's actual policy check should be. The exit-code contract around it
  (`sys.exit(2)` on failure, `sys.exit(0)` on pass) is the part the task specifically asked for.
- The `.py` file does **not** need the executable bit: in the inline-cascade shape, it's always
  passed as an argument to whichever interpreter (`uv run`/`python3`/`python`) the shell cascade
  resolved — it is never exec'd directly via its own shebang.

---

## Validation / testing steps (per the skill's Testing & Validation section)

Not run in this response (no live repo/plugin to test against here), but this is what the skill
directs before shipping the entry above:

1. `jq empty hooks/hooks.json && echo "Valid"` — JSON structure check.
2. `scripts/validate-hook-schema.sh hooks/hooks.json` — schema validation.
3. `shellcheck` does not apply here since the `command` fallback cascade, while shell syntax, is
   authored as a single-line hooks.json string rather than a standalone `.sh` file; if it were
   extracted into a `.sh` wrapper (the "two-file" Pattern 11 shape) it would need a `shellcheck`
   pass instead.
4. Manual test:
   ```bash
   echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.txt"}}' | python3 scripts/my-hook.py
   echo "Exit: $?"   # expect 0

   echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/../etc/passwd"}}' | python3 scripts/my-hook.py
   echo "Exit: $?"   # expect 2, with a message on stderr
   ```
5. Live test: restart Claude Code, trigger a `Write`/`Edit`, check `claude --debug` output for
   hook registration and execution logs.
