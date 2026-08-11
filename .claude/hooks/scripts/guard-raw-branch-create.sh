#!/bin/bash
# PreToolUse guard: hard-blocks a raw branch-creating command (`git checkout
# -b`/`-B`, `git switch -c`/`-C`/`--create`, `git worktree add -b`/`-B`,
# including an interposed flag or a `git -C <dir>` global option) that wasn't
# immediately preceded by starting-work's marker handshake. Same mechanism as
# guard-raw-commit.sh (see that script's header comment for the full
# marker-handshake rationale).
#
# Deliberately narrow: bare `git branch <name>` is NOT guarded here -- it's
# indistinguishable by regex alone from `git branch --show-current`/`-vv`/
# `--list`/etc., which starting-work, finishing-work, and commit all call
# read-only. A guard that can't tell those apart would block routine,
# harmless calls.
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if { [ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "PowerShell" ]; } || [ -z "$COMMAND" ]; then
  exit 0
fi

# git(\.exe)? also catches the literal `git.exe` invocation PowerShell callers sometimes use.
GIT_PREFIX='(^|[;&|]|[[:space:]])git(\.exe)?([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+'
MATCH=false
if echo "$COMMAND" | grep -qE "${GIT_PREFIX}checkout([[:space:]]+-[^[:space:]]+)*[[:space:]]+-[bB]([[:space:]]|\$)"; then
  MATCH=true
elif echo "$COMMAND" | grep -qE "${GIT_PREFIX}switch([[:space:]]+-[^[:space:]]+)*[[:space:]]+(-[cC]|--create)([[:space:]]|\$)"; then
  MATCH=true
elif echo "$COMMAND" | grep -qE "${GIT_PREFIX}worktree[[:space:]]+add([[:space:]]+-[^[:space:]]+)*[[:space:]]+-[bB]([[:space:]]|\$)"; then
  MATCH=true
fi
if [ "$MATCH" != true ]; then
  exit 0
fi

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0 # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
  if [ "$guard" = "git-branch-create" ] && [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
    allowed=true
  fi
  rm -f "$MARKER" # always consume -- single use regardless of outcome
fi

if [ "$allowed" = true ]; then
  exit 0
fi

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Raw branch creation (`git checkout -b`/`git switch -c`/`git worktree add -b`) is blocked by git-kit's branch-creation guard. Use the `starting-work` skill (`Skill(git-kit:starting-work)`) instead -- it syncs main, validates the branch name, and asks worktree-vs-branch, all of which this raw invocation would skip. If this fired from inside starting-work itself, its marker-write step is missing or ran too late -- the marker must be written immediately before this command."
  }
}
EOF
exit 0
