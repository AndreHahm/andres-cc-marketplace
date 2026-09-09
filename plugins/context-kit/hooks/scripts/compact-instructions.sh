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

# PreCompact doesn't support hookSpecificOutput.additionalContext
# Only use stderr for user visibility and systemMessage for basic notification

COMPACT_MSG="[StrategicCompact] Compacting...${CONTEXT_INFO}"

# Write guidance to stderr so user sees it
echo "$COMPACT_MSG" >&2
echo "Preserve: modified files, task progress, decisions, errors, next steps" >&2

# Return minimal valid JSON (PreCompact only supports basic fields)
cat << EOF
{
  "systemMessage": "$COMPACT_MSG"
}
EOF

exit 0
