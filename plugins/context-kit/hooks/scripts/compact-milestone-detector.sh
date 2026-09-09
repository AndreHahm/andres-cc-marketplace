#!/bin/bash
# Strategic Compact - Milestone Detector
# Runs on PostToolUse for Bash commands to detect milestones
#
# Detects:
# - Successful test runs (npm test, pytest, go test, etc.)
# - Git commits
# - Build completions
# - Deployment commands
#
# Suggests compact after significant milestones

# Read input from stdin
INPUT=$(cat)

# Extract command and response - try jq first, fallback to grep
if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    SUCCESS=$(echo "$INPUT" | jq -r '.tool_response.success // empty' 2>/dev/null)
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
else
    COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:.*"\([^"]*\)"/\1/')
    SUCCESS=$(echo "$INPUT" | grep -o '"success"[[:space:]]*:[[:space:]]*[a-z]*' | head -1 | sed 's/.*:[[:space:]]*//')
    SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
fi

# Exit if no command or not successful
[ -z "$COMMAND" ] && exit 0

# Get session hash
if command -v md5sum &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5sum | cut -c1-8)
elif command -v md5 &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5 | cut -c1-8)
else
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | cksum | cut -d' ' -f1)
fi

TRACK_DIR="${HOME:-${USERPROFILE:-/tmp}}/.claude/strategic-compact"
TRACK_FILE="${TRACK_DIR}/session-${SESSION_HASH}"
TRACK_LOCK="${TRACK_FILE}.lock"

# Exit if no tracking file
[ ! -f "$TRACK_FILE" ] && exit 0

# Acquire a lock before reading/updating $TRACK_FILE — this hook
# (PostToolUse) and compact-track-and-suggest.sh (PreToolUse) both
# read-modify-write the same file, and Claude Code can dispatch multiple
# tool calls in one turn. Same two-phase scheme as compact-track-and-
# suggest.sh: many cheap `mkdir`-only retries (phase 1), then at most one
# fork-costly stale-lock check-and-bust before giving up (phase 2) — see
# that script's own comment for the full rationale, including the live
# timing measurement behind splitting it this way.
_lock_acquired=0
_attempts=0
while [ "$_attempts" -lt 60 ]; do
    if mkdir "$TRACK_LOCK" 2>/dev/null; then
        printf '%s\n%s\n' "$$" "$(date +%s)" > "${TRACK_LOCK}/created" 2>/dev/null
        _lock_acquired=1
        break
    fi
    _attempts=$((_attempts + 1))
done

if [ "$_lock_acquired" -ne 1 ] && [ -f "${TRACK_LOCK}/created" ]; then
    LOCK_PID=""
    LOCK_CREATED=""
    { read -r LOCK_PID; read -r LOCK_CREATED; } < "${TRACK_LOCK}/created" 2>/dev/null
    if [[ "$LOCK_CREATED" =~ ^[0-9]+$ ]]; then
        LOCK_AGE=$(( $(date +%s) - LOCK_CREATED ))
        if [ "$LOCK_AGE" -ge 10 ] && { ! [[ "$LOCK_PID" =~ ^[0-9]+$ ]] || ! kill -0 "$LOCK_PID" 2>/dev/null; }; then
            rm -rf "$TRACK_LOCK" 2>/dev/null
            if mkdir "$TRACK_LOCK" 2>/dev/null; then
                printf '%s\n%s\n' "$$" "$(date +%s)" > "${TRACK_LOCK}/created" 2>/dev/null
                _lock_acquired=1
            fi
        fi
    fi
fi

[ "$_lock_acquired" -ne 1 ] && exit 0

# Source current state
. "$TRACK_FILE"

# Get current time
CURRENT_TIME=$(date +%s)
TIME_SINCE_MILESTONE=$((CURRENT_TIME - LAST_MILESTONE_TIME))

# Detect milestone patterns
MILESTONE_TYPE=""

# Test commands (successful) — only count as a milestone when the command actually succeeded
if [ "$SUCCESS" = "true" ] && echo "$COMMAND" | grep -qiE '(npm test|npm run test|yarn test|pnpm test|jest|vitest|pytest|python -m pytest|go test|cargo test|rspec|phpunit|mvn test|gradle test)'; then
    MILESTONE_TYPE="test_pass"
fi

# Git commit
if echo "$COMMAND" | grep -qE 'git commit'; then
    MILESTONE_TYPE="commit"
fi

# Build commands — only count as a milestone when the command actually succeeded
if [ "$SUCCESS" = "true" ] && echo "$COMMAND" | grep -qiE '(npm run build|yarn build|pnpm build|cargo build|go build|make build|gradle build|mvn package)'; then
    MILESTONE_TYPE="build"
fi

# Deploy commands
if echo "$COMMAND" | grep -qiE '(deploy|npm run deploy|vercel|netlify|heroku|kubectl apply|docker push)'; then
    MILESTONE_TYPE="deploy"
fi

# If milestone detected and enough time passed since last milestone suggestion (5 minutes)
SUGGESTION=""
if [ -n "$MILESTONE_TYPE" ] && [ "$TIME_SINCE_MILESTONE" -ge 300 ]; then
    case "$MILESTONE_TYPE" in
        test_pass)
            SUGGESTION="[StrategicCompact] Tests passed - milestone reached. Good checkpoint for /compact if implementation phase complete."
            ;;
        commit)
            SUGGESTION="[StrategicCompact] Code committed - milestone reached. Consider /compact or /handoff before starting next task."
            ;;
        build)
            SUGGESTION="[StrategicCompact] Build completed - milestone reached. Good time for /compact if moving to testing or deployment."
            ;;
        deploy)
            SUGGESTION="[StrategicCompact] Deployment complete - major milestone. Strongly recommend /compact or new session for next task."
            ;;
    esac

    # Update last milestone time
    LAST_MILESTONE_TIME=$CURRENT_TIME

    # Save updated state
    {
        echo "TOTAL=$TOTAL"
        echo "EXPLORATION=$EXPLORATION"
        echo "IMPLEMENTATION=$IMPLEMENTATION"
        echo "LAST_PHASE=$LAST_PHASE"
        echo "SUGGESTED_T1=$SUGGESTED_T1"
        echo "SUGGESTED_T2=$SUGGESTED_T2"
        echo "SUGGESTED_T3=$SUGGESTED_T3"
        echo "SUGGESTED_TIME=$SUGGESTED_TIME"
        echo "PHASE_TRANSITION_SUGGESTED=$PHASE_TRANSITION_SUGGESTED"
        echo "MILESTONE_SUGGESTED=1"
        echo "START_TIME=$START_TIME"
        echo "LAST_MILESTONE_TIME=$LAST_MILESTONE_TIME"
        echo "T1=$T1"
        echo "T2=$T2"
        echo "T3=$T3"
        echo "TIME_THRESHOLD=$TIME_THRESHOLD"
    } > "${TRACK_FILE}.tmp" && mv "${TRACK_FILE}.tmp" "$TRACK_FILE"
fi

# Release the lock now that any read-modify-write is complete. Only if we
# still own it — see compact-track-and-suggest.sh's matching comment for why.
_owner_pid=$(head -n1 "${TRACK_LOCK}/created" 2>/dev/null)
if [ -z "$_owner_pid" ] || [ "$_owner_pid" = "$$" ]; then
    rm -rf "$TRACK_LOCK" 2>/dev/null
fi

# Output JSON with suggestion if any
if [ -n "$SUGGESTION" ]; then
    # Send system notification (macOS or Linux)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        osascript -e "display notification \"$SUGGESTION\" with title \"Strategic Compact\"" 2>/dev/null &
    elif command -v notify-send &>/dev/null; then
        notify-send "Strategic Compact" "$SUGGESTION" 2>/dev/null &
    fi

    # Also write to stderr for immediate visibility
    echo "$SUGGESTION" >&2

    cat << EOF
{
  "systemMessage": "$SUGGESTION",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "$SUGGESTION"
  }
}
EOF
fi

exit 0
