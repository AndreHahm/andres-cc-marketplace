#!/bin/bash

# PostToolUse hook (matcher: Agent|Skill): best-effort, log-only runtime check
# for a small set of known plugin-rulebook R26 (Expensive-Action Opt-In)
# signatures. See r26-expensive-action-check.py's header for scope and the
# reason this is log-only (never blocks) and does not attempt R25.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_PY="$SCRIPT_DIR/r26-expensive-action-check.py"

INPUT="$(cat)"

if command -v uv >/dev/null 2>&1; then
  echo "$INPUT" | uv run "$CHECK_PY"
elif command -v python3 >/dev/null 2>&1; then
  echo "$INPUT" | python3 "$CHECK_PY"
elif command -v python >/dev/null 2>&1; then
  echo "$INPUT" | python "$CHECK_PY"
fi
# No Python runner found: silently allow (log-only hook; PostToolUse cannot
# block regardless of runner availability).
exit 0
