#!/bin/bash
# Stop guard: blocks the agent's turn from ending while the current worktree
# is one `starting-work` locked to this session (per its own lock step) and
# that worktree has uncommitted changes or commits not yet in the resolved
# default branch. Exists because Claude Code's built-in worktree exit flow
# (EnterWorktree/ExitWorktree) can remove a session's bound worktree on exit
# -- this hook makes sure nothing gets silently lost in that moment.
#
# Escape hatch: if the most recent user message, trimmed, is exactly
# "exit anyway" (case-insensitive) -- not merely containing that phrase --
# the block is skipped for this turn. Whole-message match deliberately, so
# untrusted text quoted elsewhere in the transcript (a PR body, a tool
# result) can't accidentally or deliberately trigger the override.
set -euo pipefail

INPUT=$(cat)

STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  exit 0 # already continuing from a previous block -- avoid an infinite loop
fi

git rev-parse --git-dir >/dev/null 2>&1 || exit 0 # not in a git repo
TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

# Only enforce for a worktree starting-work actually locked to a session --
# never for the main checkout or a worktree created some other way.
WORKTREE_INFO=$(git worktree list --porcelain 2>/dev/null || true)
LOCK_REASON=$(printf '%s\n' "$WORKTREE_INFO" | awk -v top="$TOPLEVEL" '
  /^worktree / { path=substr($0, 10); in_block=(path==top) }
  in_block && /^locked/ { sub(/^locked ?/, ""); print; exit }
')
if [ -z "$LOCK_REASON" ] || ! printf '%s' "$LOCK_REASON" | grep -qi "claude session"; then
  exit 0
fi

DIRTY=false
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  DIRTY=true
fi

UNMERGED=false
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
if [ -n "$(git log "origin/$DEFAULT_BRANCH"..HEAD --oneline 2>/dev/null)" ]; then
  UNMERGED=true
fi

if [ "$DIRTY" = false ] && [ "$UNMERGED" = false ]; then
  exit 0 # clean -- nothing to protect
fi

TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
  # Trimmed to a whole-message match, not a substring search -- a real override
  # is a short, deliberate command, never text embedded inside a longer PR
  # body, tool result, or system-reminder block quoted in the transcript.
  LAST_USER_MSG=$(jq -rs '
    [.[] | select(.type == "user" and (.message.role // empty) == "user")]
    | if length == 0 then "" else
        last | .message.content
        | if type == "string" then . else
            map(select(.type == "text") | .text) | join(" ")
          end
      end
    | gsub("^\\s+|\\s+$"; "")
  ' -- "$TRANSCRIPT_PATH" 2>/dev/null || echo "")
  LAST_USER_MSG_LOWER=$(printf '%s' "$LAST_USER_MSG" | tr '[:upper:]' '[:lower:]')
  if [ "$LAST_USER_MSG_LOWER" = "exit anyway" ]; then
    exit 0
  fi
fi

STATE_DESC="uncommitted changes"
if [ "$DIRTY" = true ] && [ "$UNMERGED" = true ]; then
  STATE_DESC="uncommitted changes and commits not yet in $DEFAULT_BRANCH"
elif [ "$UNMERGED" = true ]; then
  STATE_DESC="commits not yet in $DEFAULT_BRANCH"
fi

jq -n \
  --arg path "$TOPLEVEL" \
  --arg state "$STATE_DESC" \
  '{
    "decision": "block",
    "reason": ("This session'\''s bound worktree at " + $path + " has " + $state + ". Tell the user plainly: exiting now could lose this work if the worktree gets removed. Suggest committing (Skill(git-kit:commit)) or pushing first. If they want to exit anyway, they can say \"exit anyway\" and try again."),
    "systemMessage": ("Bound worktree has " + $state + " -- say \"exit anyway\" to override.")
  }'
exit 0
