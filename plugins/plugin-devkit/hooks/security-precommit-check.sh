#!/bin/bash

# PreToolUse hook (matcher: Bash): backs a deterministic, log-only subset of
# security-reviewer's checks against staged plugin component files, right before
# a `git commit` executes. See security-precommit-check.py's header for what it
# checks and why it's log-only (never blocks) in this initial version.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_PY="$SCRIPT_DIR/security-precommit-check.py"

INPUT="$(cat)"

if command -v uv >/dev/null 2>&1; then
  echo "$INPUT" | uv run "$CHECK_PY"
elif command -v python3 >/dev/null 2>&1; then
  echo "$INPUT" | python3 "$CHECK_PY"
elif command -v python >/dev/null 2>&1; then
  echo "$INPUT" | python "$CHECK_PY"
fi
# No Python runner found: silently allow (log-only hook -- absence of the check
# should never block a commit; contrast with rulebook-check.sh, which blocks with
# a clear message when no runner is found, because that hook enforces a REQUIRED gate).
exit 0
