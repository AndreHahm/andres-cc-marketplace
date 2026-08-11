#!/bin/bash
# PreToolUse guard: hard-blocks a raw `gh pr review` or `gh pr comment`
# invocation that wasn't immediately preceded by collaborating-on-a-pr's
# marker handshake. Same mechanism as guard-raw-pr-ops.sh (see that script's
# header comment for the full marker-handshake rationale).
#
# Deliberately narrow: `gh pr view` (read-only) and `gh pr edit` (used for
# non-review metadata edits across several skills) are NOT guarded here --
# only the two write actions collaborating-on-a-pr's reviewer flow owns.
# Also NOT guarded: the equivalent raw `gh api .../pulls/<n>/reviews` /
# `.../comments` REST calls -- mitigated today because collaborating-on-a-pr's
# own `allowed-tools` scopes its only `gh api` grant to `gh api user --jq`,
# so this skill itself can't take that route; the gap is for a different
# component with a broader `gh api` grant, and is a known, disclosed residual
# rather than an oversight.
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if { [ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "PowerShell" ]; } || [ -z "$COMMAND" ]; then
  exit 0
fi

GH_SUBCOMMAND=""
# gh(\.exe)? also catches the literal `gh.exe` invocation PowerShell callers sometimes use.
if echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+review([[:space:]]|$)'; then
  GH_SUBCOMMAND="gh pr review"
elif echo "$COMMAND" | grep -qE '(^|[;&|]|[[:space:]])gh(\.exe)?[[:space:]]+pr[[:space:]]+comment([[:space:]]|$)'; then
  GH_SUBCOMMAND="gh pr comment"
else
  exit 0
fi

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0 # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
  if [ "$guard" = "gh-pr-review" ] && [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
    allowed=true
  fi
  rm -f "$MARKER" # always consume -- single use regardless of outcome
fi

if [ "$allowed" = true ]; then
  exit 0
fi

REASON="Raw \`$GH_SUBCOMMAND\` is blocked by git-kit's reviewer-action guard. Use the \`collaborating-on-a-pr\` skill (\`Skill(git-kit:collaborating-on-a-pr)\`) instead -- it adds CODEOWNERS context and a structured action choice this raw invocation would skip. If this fired from inside collaborating-on-a-pr itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."

jq -n --arg reason "$REASON" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
