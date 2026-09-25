# PostToolUse Hook: `scripts/my-hook.py` on every Write/Edit

Built using `hook-development`'s "Basic Command Hook" template (`references/patterns-and-templates.md`),
the CRITICAL stdin/nested-array guidance in `SKILL.md`, and Pattern 11's required
`uv` → `python3` → `python` runner-fallback convention (a Python script invoked via a bare `hooks.json`
`command` path has no interpreter of its own, so the skill mandates this two-file shape as the default,
not an optional hardening step).

Three files are needed:

1. `hooks/hooks.json` — the PostToolUse registration (plugin project layout: hooks live at
   `hooks/hooks.json`, not `.claude-plugin/hooks.json`).
2. `scripts/my-hook.sh` — the interpreter-selection wrapper. This is what `hooks.json`'s `command`
   actually invokes, so it needs the executable bit.
3. `scripts/my-hook.py` — the actual hook logic (JSON-in on stdin, exit 2 to block). Passed as an
   argument to whichever interpreter the wrapper resolved, so it never needs the executable bit or its
   own shebang to be invoked directly.

---

## `hooks/hooks.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/my-hook.sh",
            "timeout": 5,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

Notes on each field, per the skill:
- Nested `"hooks": [...]` array inside the matcher object is required — a hook action placed directly
  under the event array (skipping this nesting) is the "#1 JSON mistake" the skill calls out.
- `matcher` uses `^(Write|Edit)$` (anchored exact-match alternation) from the skill's Common Matcher
  Patterns table, rather than a bare `Write|Edit` substring match.
- `command` uses `${CLAUDE_PLUGIN_ROOT}` for a portable, install-location-independent path, and points
  at the `.sh` wrapper — never directly at the `.py` file, since `hooks.json` has no way to select an
  interpreter itself.
- `timeout: 5` — PostToolUse is a `command` hook (default timeout 600s if omitted); the skill's
  Performance & Safety section says each hook should complete in under 5 seconds, so this caps it there.
- `onError: "warn"` — logs a warning and continues if the hook process itself errors out unexpectedly,
  without crashing the plugin. (This is independent of the hook's own exit-2 blocking behavior, which is
  the script's normal, intentional signaling path, not an error.)

---

## `scripts/my-hook.sh`

```bash
#!/bin/bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$(cat)"
if command -v uv >/dev/null 2>&1; then
  echo "$INPUT" | uv run "$SCRIPT_DIR/my-hook.py"
elif command -v python3 >/dev/null 2>&1; then
  echo "$INPUT" | python3 "$SCRIPT_DIR/my-hook.py"
elif command -v python >/dev/null 2>&1; then
  echo "$INPUT" | python "$SCRIPT_DIR/my-hook.py"
else
  echo '{"systemMessage":"my-hook: no Python runner (uv/python3/python) found on PATH — skipped."}'
fi
```

Needs the executable bit: `chmod +x scripts/my-hook.sh`.

This is the skill's canonical Pattern 11 wrapper, adapted only in filename (`my-hook.py` instead of the
template's placeholder). It reads the full event JSON once via `INPUT="$(cat)"` (per the SKILL.md CRITICAL
section — command hooks receive event data on stdin, never via environment-variable substitution) and
pipes it to whichever of `uv` / `python3` / `python` is found first on `PATH`. The final `else` branch is
the required graceful-degradation path: if none of the three interpreters exist, the wrapper emits a
`systemMessage` and exits 0 rather than falling through to a bare `exec python ...` that would crash
uncaught. This particular hook is advisory-on-missing-interpreter (skip rather than block) — the skill
notes a hook can instead choose to fail closed with a `"decision":"block"` JSON body in that branch if
blocking-on-missing-interpreter is the safer default for a given hook; not applicable here since nothing
in the task described that requirement.

---

## `scripts/my-hook.py`

```python
#!/usr/bin/env python3
import json
import sys


def main():
    data = json.load(sys.stdin)
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # TODO: replace with the actual post-write/edit check.
    # Set is_bad = True (with a reason) when the result should be blocked.
    is_bad = False
    reason = "validation failed"

    if is_bad:
        print(f"{tool_name} on {file_path}: {reason}", file=sys.stderr)
        sys.exit(2)  # exit 2 is the ONLY way to communicate a hook failure to Claude (stderr shown to it)

    sys.exit(0)  # pass/continue


if __name__ == "__main__":
    main()
```

No executable bit needed (it's always passed as an argument to the resolved interpreter in
`my-hook.sh`, never exec'd via its own shebang).

Behavior, per the skill's Exit Codes & Output Contract:
- `sys.exit(0)` — pass/continue, no message shown.
- `sys.exit(2)` — blocking error; whatever is written to stderr is fed back to Claude so it can
  understand and fix the problem. This is the mechanism the task asked for ("exit 2 to block on a bad
  result").
- Any other exit code would be a non-blocking warning (logged, execution continues) — not used here
  since the task only asked for pass/block.

The actual "bad result" check (the `is_bad` condition) is left as a `TODO` placeholder — the task didn't
specify what makes a result bad, so filling in fabricated validation logic would be inventing scope beyond
what was asked. Field paths used (`tool_name`, `tool_input.file_path`) follow the standard PostToolUse
stdin JSON shape the skill's CRITICAL section documents (`echo "$INPUT" | jq -r '.tool_input.file_path'`
in bash terms) — `tool_input` for `Write`/`Edit` carries the target file's path there.

---

## Testing (per the skill's Testing & Validation checklist)

Before shipping, the skill's own workflow calls for:
1. `jq empty hooks/hooks.json && echo "Valid"` — JSON structure check.
2. `scripts/validate-hook-schema.sh hooks/hooks.json` — schema validation.
3. `shellcheck scripts/my-hook.sh` — lint the wrapper script.
4. Manual test, piping sample event JSON:
   ```bash
   echo '{"tool_name":"Write","tool_input":{"file_path":"/test.txt"}}' | bash scripts/my-hook.sh
   echo "Exit: $?"
   ```
   (happy path — expect exit 0) and a second run with `is_bad = True` temporarily set in `my-hook.py`
   to confirm the sad path (expect exit 2 and a stderr message).
5. Live test with `claude --debug` after restarting Claude Code, watching for hook registration/
   execution log lines.
