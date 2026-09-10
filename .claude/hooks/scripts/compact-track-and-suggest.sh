#!/bin/bash
# Strategic Compact - Tool Tracker and Suggestion Engine
# Tracks tool usage patterns and suggests compaction at strategic moments
#
# Features:
# 1. Configurable thresholds (via environment variables)
# 2. Phase transition detection (exploration -> implementation)
# 3. Time-based suggestions (after configurable duration)
# 4. Tool call counting with suggestions

# Read input from stdin
INPUT=$(cat)

# Extract tool name - try jq first, fallback to grep/sed
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
else
    TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
    SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
fi

# Exit if no tool name
[ -z "$TOOL_NAME" ] && exit 0

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

mkdir -p "$TRACK_DIR"

# Acquire a lock before the read-modify-write below — this hook (PreToolUse)
# and compact-milestone-detector.sh (PostToolUse) both read, modify, and
# write the same $TRACK_FILE, and Claude Code can dispatch multiple tool
# calls in one turn, so an unlocked read-modify-write can race and silently
# lose a counter update. `mkdir` is atomic on both POSIX and NTFS (via Git
# Bash), unlike a plain file-existence check. Bounded retries (~3s total),
# never indefinite — this hook is purely advisory, so failing to get the
# lock in time just skips this call's update rather than risking a torn
# write; a hook must also stay fast regardless.
# Acquiring the lock has two phases, deliberately separated by cost:
#
# Phase 1 (below): plain `mkdir` retries, deliberately with **no explicit
# sleep** between attempts — measured live on this platform, `mkdir`
# itself already costs ~30ms/attempt (Windows/Git-Bash process-spawn
# overhead), which is real pacing on its own; adding `sleep` on top of
# that (a *second* forked process per attempt) roughly quadrupled the
# per-attempt cost (~32ms → ~144ms) for no benefit. This phase can afford
# many attempts and resolves the common case (mild, short-lived
# contention from a concurrent PostToolUse/PreToolUse invocation) fast
# and with high throughput.
#
# Phase 2 (after the loop, only if phase 1 never acquired): a *single*
# stale-lock check-and-bust attempt. Bounding this to once per invocation
# matters because it forks real subprocesses (`date`, `kill`) — measured
# live on this platform: checking every retry inside phase 1 made a
# worst-case, always-contended run take 4-11s, well past this hook's own
# 5s timeout, before the retry loop even finished. One bounded check at
# the end avoids that compounding cost entirely while still recovering
# from a genuinely crashed/killed prior invocation (no trap-based cleanup
# exists here).
#
# The stale-lock check itself: age alone isn't sufficient to bust, since
# this hook now runs async (see hooks.json) and more than one instance can
# legitimately be in flight at once — an age-only bust could tear a lock
# away from a holder that's merely slow, not dead, causing the exact
# double-write race this locking exists to prevent. `kill -0` (send no
# signal, just check liveness) confirms the recorded holder is actually
# gone before busting. Claude Code's own hook timeout (5s, per this
# plugin's hooks.json) already kills a genuinely-hung hook well before our
# 10s staleness threshold, so this PID check is defense-in-depth, not the
# primary mechanism, for a harness-driven invocation.
_lock_acquired=0
_attempts=0
while [ "$_attempts" -lt 60 ]; do
    if mkdir "$TRACK_LOCK" 2>/dev/null; then
        # Record our own PID and acquisition time inside the lock dir, one
        # per line, read back later via `read` instead of `stat`ing the
        # directory — `stat`'s format-flag syntax differs between GNU and
        # BSD (`-f` means "filesystem info" on GNU, not "format string"),
        # and there's no reliable way to detect which one a given `stat`
        # is at runtime without risking silently wrong output from the
        # other. The PID is what lets phase 2 tell "crashed" from "still
        # running but slow" before busting.
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

# Couldn't get the lock (another invocation is actively holding it) — fail
# open: skip this call's tracking update rather than race it.
[ "$_lock_acquired" -ne 1 ] && exit 0

# Validate an env-var-sourced value is a plain decimal integer before it's
# ever written into $TRACK_FILE, which is dot-sourced as shell code below —
# an unvalidated value is both a numeric-comparison bug (bash treats a
# leading-zero numeral as octal) and a shell-injection vector. See the
# identical helper in compact-session-init.sh (the other writer of this
# same initial-state block).
_validate_int() {
    local value="$1" default="$2"
    if [[ "$value" =~ ^[0-9]+$ ]]; then
        echo "$((10#$value))"
    else
        echo "$default"
    fi
}

# Initialize tracking file if needed (with configurable defaults)
if [ ! -f "$TRACK_FILE" ]; then
    START_TIME=$(date +%s)
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
        echo "T1=$(_validate_int "${STRATEGIC_COMPACT_T1:-50}" 50)"
        echo "T2=$(_validate_int "${STRATEGIC_COMPACT_T2:-75}" 75)"
        echo "T3=$(_validate_int "${STRATEGIC_COMPACT_T3:-100}" 100)"
        echo "TIME_THRESHOLD=$(_validate_int "${STRATEGIC_COMPACT_TIME:-1800}" 1800)"
    } > "$TRACK_FILE"
fi

# Source current counts and config
. "$TRACK_FILE"

# Increment total
TOTAL=$((TOTAL + 1))

# Get current timestamp for time-based checks
CURRENT_TIME=$(date +%s)
ELAPSED=$((CURRENT_TIME - START_TIME))

# Categorize tool by phase
case "$TOOL_NAME" in
    Read|Grep|Glob|WebFetch|WebSearch|Task|ToolSearch|ListMcpResourcesTool|ReadMcpResourceTool)
        EXPLORATION=$((EXPLORATION + 1))
        CURRENT_PHASE="exploration"
        ;;
    Edit|Write|NotebookEdit)
        IMPLEMENTATION=$((IMPLEMENTATION + 1))
        CURRENT_PHASE="implementation"
        ;;
    Bash)
        if [ "$IMPLEMENTATION" -gt 5 ]; then
            CURRENT_PHASE="implementation"
        else
            CURRENT_PHASE="exploration"
        fi
        ;;
    *)
        CURRENT_PHASE="$LAST_PHASE"
        ;;
esac

# Detect phase transition: exploration → implementation
TRANSITION_DETECTED=0
if [ "$LAST_PHASE" = "exploration" ] && [ "$CURRENT_PHASE" = "implementation" ]; then
    if [ "$EXPLORATION" -ge 10 ] && [ "$PHASE_TRANSITION_SUGGESTED" -eq 0 ]; then
        TRANSITION_DETECTED=1
        PHASE_TRANSITION_SUGGESTED=1
    fi
fi

# Check for suggestions
SUGGESTION=""

# Phase transition
if [ "$TRANSITION_DETECTED" -eq 1 ]; then
    SUGGESTION="[StrategicCompact] Phase transition detected (exploration -> implementation after ${EXPLORATION} reads). Consider /compact now to free context before coding."
fi

# Configurable thresholds
if [ "$TOTAL" -eq "$T1" ] && [ "$SUGGESTED_T1" -eq 0 ]; then
    SUGGESTED_T1=1
    SUGGESTION="[StrategicCompact] ${T1} tool calls reached. If context feels cluttered, this is a good checkpoint for /compact."
fi

if [ "$TOTAL" -eq "$T2" ] && [ "$SUGGESTED_T2" -eq 0 ]; then
    SUGGESTED_T2=1
    SUGGESTION="[StrategicCompact] ${T2} tool calls. Context is filling up. Recommend /compact or /handoff before continuing."
fi

if [ "$TOTAL" -eq "$T3" ] && [ "$SUGGESTED_T3" -eq 0 ]; then
    SUGGESTED_T3=1
    SUGGESTION="[StrategicCompact] ${T3} tool calls reached. Strongly recommend /compact or /handoff now to maintain performance."
fi

# Every 50 calls after T3
if [ "$TOTAL" -gt "$T3" ] && [ $((TOTAL % 50)) -eq 0 ]; then
    SUGGESTION="[StrategicCompact] ${TOTAL} tool calls in session. Consider /compact if not done recently."
fi

# Time-based suggestion (only once per session)
if [ "$ELAPSED" -ge "$TIME_THRESHOLD" ] && [ "$SUGGESTED_TIME" -eq 0 ]; then
    SUGGESTED_TIME=1
    MINUTES=$((ELAPSED / 60))
    SUGGESTION="[StrategicCompact] Session running for ${MINUTES} minutes. Long sessions accumulate stale context. Consider /compact or /handoff."
fi

# Save updated state (atomic write)
{
    echo "TOTAL=$TOTAL"
    echo "EXPLORATION=$EXPLORATION"
    echo "IMPLEMENTATION=$IMPLEMENTATION"
    echo "LAST_PHASE=$CURRENT_PHASE"
    echo "SUGGESTED_T1=$SUGGESTED_T1"
    echo "SUGGESTED_T2=$SUGGESTED_T2"
    echo "SUGGESTED_T3=$SUGGESTED_T3"
    echo "SUGGESTED_TIME=$SUGGESTED_TIME"
    echo "PHASE_TRANSITION_SUGGESTED=$PHASE_TRANSITION_SUGGESTED"
    echo "MILESTONE_SUGGESTED=$MILESTONE_SUGGESTED"
    echo "START_TIME=$START_TIME"
    echo "LAST_MILESTONE_TIME=$LAST_MILESTONE_TIME"
    echo "T1=$T1"
    echo "T2=$T2"
    echo "T3=$T3"
    echo "TIME_THRESHOLD=$TIME_THRESHOLD"
} > "${TRACK_FILE}.tmp" && mv "${TRACK_FILE}.tmp" "$TRACK_FILE"

# Release the lock now that the read-modify-write is complete — everything
# after this point (notification, JSON output) doesn't touch $TRACK_FILE.
# Only release if we still own it: if another waiter busted our lock while
# we were running (should not happen while our PID is alive, per the
# liveness check above, but this is the cheap second half of that same
# defense) and took ownership itself, deleting the dir out from under that
# new owner would reopen the exact race this locking exists to prevent.
_owner_pid=$(head -n1 "${TRACK_LOCK}/created" 2>/dev/null)
if [ -z "$_owner_pid" ] || [ "$_owner_pid" = "$$" ]; then
    rm -rf "$TRACK_LOCK" 2>/dev/null
fi

# Output JSON with suggestion if any
if [ -n "$SUGGESTION" ]; then
    # Write pending suggestion for Stop hook to pick up
    echo "$SUGGESTION" > "${TRACK_DIR}/pending-${SESSION_HASH}"

    # Send system notification (macOS or Linux)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        osascript -e "display notification \"$SUGGESTION\" with title \"Strategic Compact\"" 2>/dev/null &
    elif command -v notify-send &>/dev/null; then
        notify-send "Strategic Compact" "$SUGGESTION" 2>/dev/null &
    fi

    cat << EOF
{
  "systemMessage": "$SUGGESTION",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "IMPORTANT - MUST INFORM USER: $SUGGESTION"
  }
}
EOF
fi

exit 0
