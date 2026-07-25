#!/bin/bash

# PostToolUse + PostToolUseFailure hook (matcher: Agent|Bash on both events):
# best-effort, log-only reminder for plugin-rulebook R25 (Unplanned-Overhead
# Disclosure). See r25-overhead-disclosure-check.py's header for scope and
# why this is a forward-looking reminder, not a compliance check.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_PY="$SCRIPT_DIR/r25-overhead-disclosure-check.py"

INPUT="$(cat)"

if command -v uv >/dev/null 2>&1; then
  echo "$INPUT" | uv run "$CHECK_PY"
elif command -v python3 >/dev/null 2>&1; then
  echo "$INPUT" | python3 "$CHECK_PY"
elif command -v python >/dev/null 2>&1; then
  echo "$INPUT" | python "$CHECK_PY"
fi
# No Python runner found: silently allow (log-only hook; PostToolUse/
# PostToolUseFailure cannot block regardless of runner availability).
exit 0
