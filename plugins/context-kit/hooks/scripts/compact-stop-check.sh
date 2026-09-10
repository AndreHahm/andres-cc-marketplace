#!/bin/bash
# Strategic Compact - Stop Hook
# Checks if there are pending suggestions and forces Claude to inform the user
#
# This hook runs when Claude stops responding. If there are pending
# suggestions that haven't been communicated, it blocks the stop
# and forces Claude to inform the user.

# Read input from stdin
INPUT=$(cat)

# Extract session info
if command -v jq &>/dev/null; then
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
    STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
else
    SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
    STOP_HOOK_ACTIVE=$(echo "$INPUT" | grep -o '"stop_hook_active"[[:space:]]*:[[:space:]]*[a-z]*' | sed 's/.*:[[:space:]]*//')
fi

# Don't run if stop hook is already active (prevent infinite loop)
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

# Get session hash
if command -v md5sum &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5sum | cut -c1-8)
elif command -v md5 &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5 | cut -c1-8)
else
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | cksum | cut -d' ' -f1)
fi

TRACK_DIR="${HOME:-${USERPROFILE:-/tmp}}/.claude/strategic-compact"
PENDING_FILE="${TRACK_DIR}/pending-${SESSION_HASH}"

# Check if there's a pending suggestion to communicate
if [ -f "$PENDING_FILE" ]; then
    SUGGESTION=$(cat "$PENDING_FILE")
    rm -f "$PENDING_FILE"

    # Block the stop and force Claude to communicate
    cat << EOF
{
  "decision": "block",
  "reason": "IMPORTANT: Before continuing, inform the user about this context management suggestion: $SUGGESTION"
}
EOF
    exit 0
fi

exit 0
