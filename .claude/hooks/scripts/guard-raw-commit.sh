#!/bin/bash
# PreToolUse guard: hard-blocks a raw `git commit` invocation that wasn't
# immediately preceded by an allowlisted git-kit skill's marker handshake.
#
# Marker handshake: a skill that legitimately runs `git commit` directly
# (commit, standalone-commits) writes a single line "git-commit <epoch> <skill>"
# to $(git rev-parse --git-dir)/git-kit-marker.txt right before running it.
# This hook checks for that marker, requires it to be fresh (<=60s old) and
# for the right guard type, then always consumes it (deletes it) whether or
# not it matched -- so a marker can never be reused for a second, unrelated
# raw command later in the session.
#
# The marker lives under .git/ (never .claude/) specifically so it can never
# be accidentally committed regardless of a consuming project's .gitignore --
# .git/ itself is never tracked, by git's own design.
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if { [ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "PowerShell" ]; } || [ -z "$COMMAND" ]; then
  exit 0
fi

# Match `git commit` as a standalone subcommand invocation -- not a mention of
# the word "commit" elsewhere (e.g. `git log --grep=commit`, `echo "commit this"`).
# `git(\.exe)?` also catches the literal `git.exe` invocation PowerShell callers
# sometimes use. The optional `-C <dir>`/`-c <k>=<v>` group catches an interposed
# global option (e.g. git-cleanup's own `Bash(git -C:*)` grant) -- same prefix
# pattern guard-raw-branch-create.sh already uses.
GIT_PREFIX='(^|[;&|]|[[:space:]])git(\.exe)?([[:space:]]+-[Cc][[:space:]]+[^[:space:]]+)?[[:space:]]+'
if ! echo "$COMMAND" | grep -qE "${GIT_PREFIX}commit([[:space:]]|\$)"; then
  exit 0
fi

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0  # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
  if [ "$guard" = "git-commit" ] && [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
    allowed=true
  fi
  rm -f "$MARKER"  # always consume -- single use regardless of outcome
fi

if [ "$allowed" = true ]; then
  exit 0
fi

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Raw `git commit` is blocked by git-kit's commit guard. Use the `commit` skill (`/commit`) instead -- it handles staging review, sensitive-file scanning, message formatting, and the behavior-change test gate this raw invocation would skip. If this fired from inside an allowlisted git-kit skill (commit, standalone-commits), its marker-write step is missing or ran too late -- the marker must be written immediately before this command, not earlier in the same run."
  }
}
EOF
exit 0
