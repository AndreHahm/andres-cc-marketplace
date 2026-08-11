#!/bin/bash
# PreToolUse guard: hard-blocks a raw `gh pr create` or `gh pr merge`
# invocation that wasn't immediately preceded by an allowlisted git-kit
# skill's marker handshake. Same mechanism as guard-raw-commit.sh (see that
# script's header comment for the full marker-handshake rationale) -- kept
# as a separate script/hook registration since it guards a different pair
# of commands and has its own guard-type values.
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if { [ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "PowerShell" ]; } || [ -z "$COMMAND" ]; then
  exit 0
fi

GUARD_TYPE=""
SKILL_NAME=""
GH_SUBCOMMAND=""
SKILL_HANDLES=""
# gh(\.exe)? also catches the literal `gh.exe` invocation PowerShell callers sometimes use.
if echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+create([[:space:]]|$)'; then
  GUARD_TYPE="gh-pr-create"
  SKILL_NAME="create-pr"
  GH_SUBCOMMAND="gh pr create"
  SKILL_HANDLES="template resolution, draft-vs-ready confirmation, and pre-flight commit checks"
elif echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
  GUARD_TYPE="gh-pr-merge"
  SKILL_NAME="merge-pr"
  GH_SUBCOMMAND="gh pr merge"
  SKILL_HANDLES="readiness checks (draft/CI/reviews) and a merge-rights verification"
else
  exit 0
fi

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0  # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
  if [ "$guard" = "$GUARD_TYPE" ] && [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
    allowed=true
  fi
  rm -f "$MARKER"  # always consume -- single use regardless of outcome
fi

if [ "$allowed" = true ]; then
  exit 0
fi

REASON="Raw \`$GH_SUBCOMMAND\` is blocked by git-kit's PR-operations guard. Use the \`$SKILL_NAME\` skill (\`/$SKILL_NAME\`) instead -- it handles $SKILL_HANDLES this raw invocation would skip. If this fired from inside $SKILL_NAME itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."

jq -n --arg reason "$REASON" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
