# PreToolUse hook: validate before every Write/Edit (Python, `scripts/my-hook.py`)

Following `hook-development`'s conventions:

- **File location**: this is a plugin project, so the hook config goes in `hooks/hooks.json` at the
  plugin root (never `.claude-plugin/hooks.json` — that directory is reserved for `plugin.json`).
- **Structure**: every handler sits inside the nested `"hooks": [...]` array under the matcher, per the
  CRITICAL "Nested hooks Array JSON Structure" section.
- **Stdin, not env vars**: the script reads the full event JSON from stdin (`json.load(sys.stdin)`),
  never `${arguments.file_path}`-style env substitution.
- **Matcher**: `^(Write|Edit)$` — exact tool-name match for both tools, per the Common Matcher Patterns
  table.
- **Exit codes**: `0` = allow, `2` = block with the stderr message shown to Claude — "Exit 2 is the ONLY
  way to communicate hook failures to Claude."
- **Pattern 11 (Cross-Platform Python Hook) — required interpreter fallback**: `hooks.json` invokes
  `command` by bare path with no interpreter of its own, and a plain `python` binary isn't guaranteed to
  exist, so the hook uses the required `uv` → `python3` → `python` cascade with graceful degradation
  (never an uncaught crash) if none is found. Per Pattern 11's own guidance, the `uv` tier includes the
  functional probe (`uv --version`, not just `command -v uv`) — `command -v uv` only proves a `uv` binary
  is on `PATH`, not that invoking it actually works, and since the cascade uses `exec`, a broken/sandboxed
  `uv` would otherwise dead-end instead of falling through to `python3`/`python`.
- **Shape choice**: this is a single, straightforward validation script with no logic beyond interpreter
  selection, so it uses Pattern 11's **inline `command` cascade** shape (Shape 1) rather than a separate
  `.sh` wrapper — "Good default for a single straightforward script... this is what most of this repo's
  own hooks actually use." Because the cascade `exec`s the target `.py` file directly, stdin passes
  through automatically with no need to buffer it in the JSON `command` string.

---

## File: `hooks/hooks.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "if command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then exec uv run --no-project \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; elif command -v python3 >/dev/null 2>&1; then exec python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; elif command -v python >/dev/null 2>&1; then exec python \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; else exit 0; fi",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Notes on this entry, tied back to the skill:

- `matcher` is `"^(Write|Edit)$"` — matches are case-sensitive, and this is the exact tool-name form the
  skill's Common Matcher Patterns table shows for "Edit files."
- `timeout: 5` — the skill's Performance & Safety section says "each hook should complete in under 5
  seconds," and this is a fast deterministic check (command type is the documented choice for that,
  per the Type Decision table), so a short timeout is appropriate. (Default for `command` type is 600s
  if omitted — set explicitly here since this hook is meant to be fast.)
- No `onError` is set — this hook's whole purpose is a blocking safety gate (exit 2 on bad input), so the
  default (non-`"warn"`/`"continue"`) behavior is correct; `onError: "warn"`/`"continue"` are for hooks
  whose failures shouldn't block execution (e.g. logging), which this is not.
- The final `else exit 0;` branch is the required graceful-degradation path: if none of `uv`, `python3`,
  or `python` is found, the hook exits 0 (allow) rather than crashing. (A blocking hook could instead
  choose to fail closed there per Pattern 11's note — but silently missing an interpreter is not "a bad
  result" the validation logic itself detected, so this template defaults to allow; swap to a
  `sys.exit(2)`-equivalent shell branch if failing closed is the safer default for your specific check.)

---

## File: `scripts/my-hook.py`

```python
#!/usr/bin/env python3
"""PreToolUse hook for Write/Edit.

Reads the tool-call event JSON from stdin (never environment variables —
see hook-development's CRITICAL "Command Hooks Receive Data via Stdin"
section) and exits 2 to block the tool call when validation fails, or 0
to allow it. Exit 2 is the only way to surface a blocking message to
Claude; the message must go to stderr.
"""
import json
import sys
from pathlib import Path

data = json.load(sys.stdin)
file_path = Path(data.get("tool_input", {}).get("file_path", ""))


def is_bad_result(path: Path) -> bool:
    """Replace with the real validation check for this hook."""
    return False


if is_bad_result(file_path):
    print(f"Blocked: {file_path} failed validation.", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
```

Notes on this script, tied back to the skill:

- Uses `pathlib.Path` for the file path — never a hardcoded `/tmp/`-style string or OS-specific
  separator — per the Performance & Safety section's "Prefer Python for cross-platform hook scripts"
  guidance and Pattern 11's template.
- No `subprocess` call is needed for this validation shape, but if one were added, it must use list
  arguments and never `shell=True` with a string command (Performance & Safety section /
  Pattern 11).
- `json.load(sys.stdin)` is the required stdin-JSON parsing approach — reading `tool_input.file_path`
  from the parsed event data, not from an env var.
- The `is_bad_result()` function is an intentionally minimal placeholder — the task only specified "exit
  2 on a bad result," not what the check itself should be; fill in the real validation logic there.
- The `.py` file is passed as an argument to whichever interpreter the `hooks.json` cascade resolves
  (`uv run --no-project .../my-hook.py`, `python3 .../my-hook.py`, or `python .../my-hook.py`) — it is
  never `exec`'d via its own shebang, so it does **not** need the executable bit set (only the two-file
  `.sh`-wrapper shape from Pattern 11 requires that, for the wrapper itself).

---

## Testing & Validation (per the skill's own Testing & Validation section)

1. **JSON structure**: `jq empty hooks/hooks.json && echo "Valid"`
2. **Schema validation**: `scripts/validate-hook-schema.sh hooks/hooks.json`
3. **Script lint**: no separate `.sh` script exists in this shape (the fallback lives inline in
   `hooks.json`'s own `command` string), so there is nothing for `shellcheck` to check here — this is
   the tradeoff of picking Shape 1 over the `.sh`-wrapper shape.
4. **Manual test** (happy path and sad path):
   ```bash
   echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/ok.txt"}}' \
     | python3 scripts/my-hook.py; echo "Exit: $?"   # expect 0

   # Flip is_bad_result() to return True temporarily to confirm the blocking path:
   echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/bad.txt"}}' \
     | python3 scripts/my-hook.py; echo "Exit: $?"   # expect 2, stderr message printed
   ```
5. **Live test**: restart Claude Code, trigger a Write/Edit, check `claude --debug` output for hook
   registration and execution.

**Quality gates:**
- [ ] `jq empty` passes on `hooks/hooks.json`
- [ ] Happy path: valid input → hook passes (exit 0)
- [ ] Sad path: invalid/blocked input → hook fires correctly (exit 2 + stderr)
- [ ] `scripts/validate-hook-schema.sh` reports no errors
- [ ] Interpreter cascade verified: at minimum confirm `uv --version` succeeds (or falls through
  correctly) on the target machine, since a present-but-broken `uv` would otherwise dead-end via `exec`
