#!/bin/bash
# Strategic Compact - Pre-Compact Instructions Injector
# Runs before compaction to provide intelligent summarization guidance
#
# Ensures important context survives compaction:
# - Code changes and file paths
# - Key decisions made
# - Current task status
# - Test results and errors

# Read input from stdin
INPUT=$(cat)

# Extract trigger type - try jq first, fallback to grep
if command -v jq &>/dev/null; then
    TRIGGER=$(echo "$INPUT" | jq -r '.trigger // "auto"' 2>/dev/null)
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
else
    TRIGGER=$(echo "$INPUT" | grep -o '"trigger"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
    SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
    TRIGGER="${TRIGGER:-auto}"
fi

# Get session tracking info if available
if command -v md5sum &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5sum | cut -c1-8)
elif command -v md5 &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5 | cut -c1-8)
else
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | cksum | cut -d' ' -f1)
fi

TRACK_DIR="${HOME:-${USERPROFILE:-/tmp}}/.claude/strategic-compact"
TRACK_FILE="${TRACK_DIR}/session-${SESSION_HASH}"

# Build context about the session
CONTEXT_INFO=""
if [ -f "$TRACK_FILE" ]; then
    . "$TRACK_FILE"
    CONTEXT_INFO=" Session had ${TOTAL} tool calls (${EXPLORATION} exploration, ${IMPLEMENTATION} implementation)."
fi

# This script only emits stderr and systemMessage below, not
# hookSpecificOutput.additionalContext -- even though Claude Code's own docs
# (https://code.claude.com/docs/en/hooks) confirm PreCompact DOES support
# additionalContext as an output field. That's an implementation choice here,
# not a contract limitation (corrected 2026-09-11, found by CodeRabbit's
# automated review -- an earlier version of this comment wrongly claimed
# PreCompact doesn't support additionalContext at all). Neither stderr nor
# systemMessage is guaranteed reliably visible by default: stderr on a normal
# (exit 0) hook is shown in verbose mode only, and systemMessage's exact
# delivery for PreCompact specifically is not independently confirmed one way
# or the other. This is deliberately a best-effort nudge, not this plugin's
# actual state-preservation guarantee — that's pre-compact.py/post-compact-
# restore.py's capture/restore mechanism (SessionStart's additionalContext,
# which IS supported and is what this plugin's docs describe as the real
# behavior).
COMPACT_MSG="[StrategicCompact] Compacting...${CONTEXT_INFO}"

# Write guidance to stderr (visible in verbose mode; not guaranteed otherwise)
echo "$COMPACT_MSG" >&2
echo "Preserve: modified files, task progress, decisions, errors, next steps" >&2

# Return minimal valid JSON (PreCompact only supports basic fields)
cat << EOF
{
  "systemMessage": "$COMPACT_MSG"
}
EOF

exit 0
