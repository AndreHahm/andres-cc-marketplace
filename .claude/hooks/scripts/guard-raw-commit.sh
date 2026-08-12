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
    "permissionDecisionReason": "git-kit's raw-command guard requires `jq`, which isn't available in this environment -- install jq or this guard cannot verify the command is safe."
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

# Consume our own marker on every Bash/PowerShell call, before the command
# regex match below -- not just on the call that turns out to match. See
# guard-raw-destructive-cleanup.sh's header comment for the full rationale
# (consuming only inside the match branch let a marker survive its full 60s
# TTL through any number of intervening non-matching commands). Only a marker
# whose `guard` field is this guard's own type ("git-commit") is touched --
# a marker written for a sibling guard is left alone.
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0  # not in a git repo -- nothing to guard
MARKER="$GIT_DIR/git-kit-marker.txt"

now=$(date +%s)
allowed=false

if [ -f "$MARKER" ]; then
  read -r guard ts _skill < "$MARKER" || true
  guard="${guard:-}"  # defensive: a concurrent/partial read under `set -u` must degrade to "no marker", never crash
  if [ "$guard" = "git-commit" ]; then
    case "${ts:-}" in '' | *[!0-9]*) ts="" ;; esac  # digits-only -- never reaches arithmetic otherwise
    if [ -n "$ts" ] && [ $((now - ts)) -le 60 ]; then
      allowed=true
    fi
    rm -f "$MARKER"  # consume as soon as seen -- single use, regardless of whether this call turns out to match below
  fi
fi

# Match `git commit` as a standalone subcommand invocation -- not a mention of
# the word "commit" elsewhere (e.g. `git log --grep=commit`, `echo "commit this"`).
# `git(\.exe)?` also catches the literal `git.exe` invocation PowerShell callers
# sometimes use. The repeating group catches zero or more interposed global
# options -- `-C <dir>`/`-c <k>=<v>` (each a separate space-delimited value
# token) or any other single-token `-`/`--` flag (e.g. `--no-pager`) -- so
# stacked options like `git -c a=b -c c=d commit` or `git --no-pager commit`
# can't bypass this guard. Same prefix pattern guard-raw-branch-create.sh
# already uses.
GIT_PREFIX='(^|[;&|]|[[:space:]])git(\.exe)?([[:space:]]+(-[Cc][[:space:]]+[^[:space:]]+|--?[^[:space:]]+))*[[:space:]]+'
if ! echo "$COMMAND" | grep -qE "${GIT_PREFIX}commit([[:space:]]|\$)"; then
  exit 0
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
