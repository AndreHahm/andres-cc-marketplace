#!/bin/bash
# PreToolUse guard: hard-blocks a raw `gh pr review` or `gh pr comment`
# invocation that wasn't immediately preceded by collaborating-on-a-pr's,
# explain-pr-changes's, or codex-review-recovery's marker handshake. Same
# mechanism as guard-raw-pr-ops.sh (see that script's header comment for the
# full marker-handshake rationale).
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
    "permissionDecisionReason": "git-kit's reviewer-action guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
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
# match below -- not just on the call that turns out to match. See
# guard-raw-destructive-cleanup.sh's header comment for the full rationale
# (consuming only inside the match branch let a marker survive its full 60s
# TTL through any number of intervening non-matching commands). Only a marker
# whose `guard` field is this guard's own type ("gh-pr-review") is touched --
# a marker written for a sibling guard is left alone.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0 # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "gh-pr-review" ]; then
    case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
    if [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
      allowed=true
    fi
    rm -f "$MARKER" # consume as soon as seen -- single use, regardless of whether this call turns out to match below
  fi
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

if [ "$allowed" = true ]; then
  exit 0
fi

REASON="Raw \`$GH_SUBCOMMAND\` is blocked by git-kit's reviewer-action guard. Use whichever of \`collaborating-on-a-pr\`, \`explain-pr-changes\`, or \`codex-review-recovery\` matches what you're doing instead -- each writes the marker this guard requires immediately before running the same command. If this fired from inside one of those skills, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."

jq -n --arg reason "$REASON" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
exit 0
