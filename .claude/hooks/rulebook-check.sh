#!/bin/bash

# PostToolUse hook: backs plugin-rulebook-enforcement.md with a live check.
# Runs a deterministic subset of plugin-rulebook rules (R4-R6, R8, R9, R13, R14, R17, R18)
# plus frontmatter-allowlist, agent-enum, broken-link/orphan-file, and hooks-only-var checks
# against any plugin component (skill/agent/command/hook/rule) touched by Write or Edit.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_PATH="$SCRIPT_DIR/../skills/plugin-rulebook/assets/settings.json"
CHECK_PY="$SCRIPT_DIR/rulebook-check.py"

INPUT="$(cat)"

if command -v uv >/dev/null 2>&1; then
  echo "$INPUT" | uv run "$CHECK_PY" "$SETTINGS_PATH"
elif command -v python3 >/dev/null 2>&1; then
  echo "$INPUT" | python3 "$CHECK_PY" "$SETTINGS_PATH"
elif command -v python >/dev/null 2>&1; then
  echo "$INPUT" | python "$CHECK_PY" "$SETTINGS_PATH"
else
  echo '{"decision":"block","reason":"rulebook-check: no Python runner (uv/python3/python) found on PATH — install uv or Python 3.8+ to enable this check.","hookSpecificOutput":{"hookEventName":"PostToolUse"}}'
fi
