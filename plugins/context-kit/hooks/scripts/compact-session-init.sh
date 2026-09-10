#!/bin/bash
# Strategic Compact - Session Initializer
# Runs at session start to set up tracking and provide initial context
#
# Features:
# - Initializes tool call tracking
# - Records session start time (for time-based suggestions)
# - Cleans up old tracking files

# Read input from stdin
INPUT=$(cat)

# Extract session info - try jq first, fallback to grep
if command -v jq &>/dev/null; then
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
    SOURCE=$(echo "$INPUT" | jq -r '.source // "startup"' 2>/dev/null)
else
    SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
    SOURCE=$(echo "$INPUT" | grep -o '"source"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
    SOURCE="${SOURCE:-startup}"
fi

# Create tracking directory (portable: $HOME, falling back to Windows $USERPROFILE, then /tmp)
TRACK_DIR="${HOME:-${USERPROFILE:-/tmp}}/.claude/strategic-compact"
mkdir -p "$TRACK_DIR"

# Clean up old session files (older than 24 hours)
find "$TRACK_DIR" -name "session-*" -mtime +1 -delete 2>/dev/null || true

# Get session hash
if command -v md5sum &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5sum | cut -c1-8)
elif command -v md5 &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5 | cut -c1-8)
else
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | cksum | cut -d' ' -f1)
fi

TRACK_FILE="${TRACK_DIR}/session-${SESSION_HASH}"
TRACK_LOCK="${TRACK_FILE}.lock"

# Get current timestamp
START_TIME=$(date +%s)

# Validate an env-var-sourced value is a plain decimal integer before it's
# ever written into $TRACK_FILE (which every other hook in this plugin
# dot-sources as shell code — see compact-track-and-suggest.sh). An
# unvalidated value here is both a numeric-comparison bug (bash treats a
# leading-zero numeral as octal, e.g. "050" errors) and a shell-injection
# vector (e.g. "50; rm -rf ~" would execute verbatim once sourced). Reject
# anything that isn't purely digits and fall back to the default instead.
_validate_int() {
    local value="$1" default="$2"
    if [[ "$value" =~ ^[0-9]+$ ]]; then
        echo "$((10#$value))"
    else
        echo "$default"
    fi
}

# Read configurable thresholds from environment (with defaults)
T1=$(_validate_int "${STRATEGIC_COMPACT_T1:-50}" 50)
T2=$(_validate_int "${STRATEGIC_COMPACT_T2:-75}" 75)
T3=$(_validate_int "${STRATEGIC_COMPACT_T3:-100}" 100)
TIME_THRESHOLD=$(_validate_int "${STRATEGIC_COMPACT_TIME:-1800}" 1800)  # 30 minutes default

# Initialize on fresh starts AND after compact (context is fresh after compact).
# Guarded by the same mkdir-based lock as compact-track-and-suggest.sh /
# compact-milestone-detector.sh (see that script's own comment for the full
# two-phase rationale and the live timing behind it) — a stray in-flight
# async compact-track-and-suggest.sh invocation from just before a
# /clear or compact event could otherwise race this reset.
if [ "$SOURCE" = "startup" ] || [ "$SOURCE" = "clear" ] || [ "$SOURCE" = "compact" ]; then
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

    # Fail open like the sibling scripts: if the lock couldn't be acquired,
    # skip the reset rather than writing it anyway — an unconditional write
    # here could still land in the middle of a real holder's own
    # read-modify-write and get clobbered by (or clobber) it, which is
    # exactly the race this lock exists to prevent. Skipping just leaves
    # this one session starting with the prior session's leftover counters
    # instead of a clean reset — a minor, self-correcting cosmetic gap, not
    # a correctness issue.
    if [ "$_lock_acquired" -eq 1 ]; then
        {
            echo "TOTAL=0"
            echo "EXPLORATION=0"
            echo "IMPLEMENTATION=0"
            echo "LAST_PHASE=exploration"
            echo "SUGGESTED_T1=0"
            echo "SUGGESTED_T2=0"
            echo "SUGGESTED_T3=0"
            echo "SUGGESTED_TIME=0"
            echo "PHASE_TRANSITION_SUGGESTED=0"
            echo "MILESTONE_SUGGESTED=0"
            echo "START_TIME=$START_TIME"
            echo "LAST_MILESTONE_TIME=$START_TIME"
            echo "T1=$T1"
            echo "T2=$T2"
            echo "T3=$T3"
            echo "TIME_THRESHOLD=$TIME_THRESHOLD"
        } > "${TRACK_FILE}.tmp" && mv "${TRACK_FILE}.tmp" "$TRACK_FILE"

        _owner_pid=$(head -n1 "${TRACK_LOCK}/created" 2>/dev/null)
        if [ -z "$_owner_pid" ] || [ "$_owner_pid" = "$$" ]; then
            rm -rf "$TRACK_LOCK" 2>/dev/null
        fi
    fi
fi

# Build config info for context
CONFIG_INFO="Thresholds: ${T1}/${T2}/${T3} calls, ${TIME_THRESHOLD}s time limit."

# Provide context about strategic compact being active
STARTUP_MSG="[StrategicCompact] Context management active. ${CONFIG_INFO} Suggestions appear at phase transitions, tool thresholds, milestones (test pass, commit), and time limits. Use /compact at suggested moments."

# Send system notification on session start (optional - can be noisy)
# Uncomment to enable:
# if [[ "$OSTYPE" == "darwin"* ]]; then
#     osascript -e "display notification \"Context management active\" with title \"Strategic Compact\"" 2>/dev/null &
# fi

# Write to stderr so user sees it
echo "$STARTUP_MSG" >&2

cat << EOF
{
  "systemMessage": "$STARTUP_MSG",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$STARTUP_MSG"
  }
}
EOF

exit 0
