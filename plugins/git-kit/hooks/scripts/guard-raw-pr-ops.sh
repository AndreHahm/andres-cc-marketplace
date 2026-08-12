#!/bin/bash
# PreToolUse guard: hard-blocks a raw `gh pr create` or `gh pr merge`
# invocation that wasn't immediately preceded by an allowlisted git-kit
# skill's marker handshake. Same mechanism as guard-raw-commit.sh (see that
# script's header comment for the full marker-handshake rationale) -- kept
# as a separate script/hook registration since it guards a different pair
# of commands and has its own guard-type values.
set -euo pipefail

# Fail closed, not open: if jq isn't available, the script below can't parse
# INPUT and would otherwise crash -- which, under this hook's "onError": "warn"
# registration, lets the tool call proceed with just a warning. Emit an
# explicit deny instead, so a missing dependency can't silently defeat this
# guard.
if ! command -v jq >/dev/null 2>&1; then
  cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "git-kit's PR-operations guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
  }
}
EOF
  exit 0
fi

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if { [ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "PowerShell" ]; } || [ -z "$COMMAND" ]; then
  exit 0
fi

# Consume our own marker on every Bash/PowerShell call, before the subcommand
# match below determines which of this script's two guard types actually
# applies. See guard-raw-destructive-cleanup.sh's header comment for the full
# rationale (consuming only inside the match branch let a marker survive its
# full 60s TTL through any number of intervening non-matching commands).
# Unlike the other guards, this script owns two guard types ("gh-pr-create"
# and "gh-pr-merge") -- a marker is consumed here if it belongs to EITHER of
# them (before we know which specific subcommand, if any, this call is), but
# is only treated as authorizing this call once the actual subcommand is
# known below. A marker written for a sibling guard (a different type
# entirely) is left alone.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0  # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false
marker_guard=""
marker_ts=""

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "gh-pr-create" ] || [ "$guard" = "gh-pr-merge" ]; then
    case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
    marker_guard="$guard"
    marker_ts="$ts"
    rm -f "$MARKER"  # consume as soon as seen -- single use, regardless of which (if either) subcommand this call turns out to be
  fi
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

if [ "$marker_guard" = "$GUARD_TYPE" ] && [ -n "$marker_ts" ] && [ $((now - marker_ts)) -le 60 ]; then
  allowed=true
fi

if [ "$allowed" = true ]; then
  exit 0
fi

REASON="Raw \`$GH_SUBCOMMAND\` is blocked by git-kit's PR-operations guard. Use the \`$SKILL_NAME\` skill (\`/$SKILL_NAME\`) instead -- it handles $SKILL_HANDLES this raw invocation would skip. If this fired from inside $SKILL_NAME itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."

jq -n --arg reason "$REASON" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
