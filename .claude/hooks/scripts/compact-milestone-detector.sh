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

# Extract command and session id - try jq first, fallback to grep. No
# success/failure field is extracted here: PostToolUse (the event this hook
# is wired to) only ever fires after a tool call completes successfully —
# a failed Bash command routes to the separate PostToolUseFailure event
# instead, which this plugin doesn't wire up — and the real Bash
# tool_response payload has no `.success` boolean field anyway (it's
# `{stdout, stderr, interrupted, isImage}`). An earlier version of this
# hook gated milestone detection on `.tool_response.success`, which was
# always empty/false in practice and silently disabled the test_pass/build
# milestone types entirely.
if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
else
    COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:.*"\([^"]*\)"/\1/')
    SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)"/\1/')
fi

# Exit if no command
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

# Detect milestone patterns. Each block below is a separate `if` (not
# `elif`), so on a chained command matching more than one pattern (e.g.
# `npm test && git commit -am fix`), the later block wins — deploy > build >
# commit > test_pass, in the order checked below. Deliberate: a later
# milestone in this list is treated as the more significant one when
# several occur in the same command.
MILESTONE_TYPE=""

# Split the command into "segments" on ;, &&, ||, | (plus any literal
# newlines already in $COMMAND) so each pattern below can be anchored to
# the START of its own segment, rather than matching anywhere in the
# string. Without this, a runner/build/deploy keyword appearing only as
# another command's own argument or search text (e.g. `rg -n pytest
# README.md`, `grep -n "git commit" docs.md`) is indistinguishable from an
# actual invocation — found live by Codex review, reproduced with
# `rg -n pytest README.md` wrongly reporting a test-pass milestone despite
# no test ever running.
COMMAND_SEGMENTS=$(printf '%s\n' "$COMMAND" | sed -E 's/(&&|\|\||[;|])/\n/g')
# A segment's real command name may be preceded by simple VAR=value
# assignments and/or one known wrapper-command prefix (uv run, npx, poetry
# run, pnpm exec) — allow those between the segment start and the actual
# keyword, but nothing else.
CMD_START='^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*(env[[:space:]]+)?(uv run |npx |poetry run |pnpm exec )?'

# Test commands — PostToolUse only fires after the Bash call completed
# successfully (see the comment above), so no separate success check is
# needed here. `-w` (whole-word match around the entire matched pattern)
# ensures a short token like `jest` only matches a real word, not a
# substring of an unrelated command (e.g. `majestic`, `jester`) — this
# branch was dead code before the SUCCESS-gate removal above, so this
# substring-match exposure is new. Uses `-w`, not `\b`: BSD grep (macOS's
# default `/usr/bin/grep`) doesn't support the GNU-only `\b` word-boundary
# escape at all — it's treated as a literal `b`, silently matching nothing
# on that platform (corrected 2026-09-11, found by CodeRabbit's automated
# review; `-w` is supported by both GNU and BSD grep).
# Skip the milestone when the command itself swallows a failing test's
# exit code (e.g. `pytest || true`) — PostToolUse fires on the outer
# command's own exit status, not the test framework's, so a command
# shaped this way can complete successfully (firing this hook) even
# though the tests inside it actually failed. Narrow, deliberate
# heuristic: only the exact trailing `|| true` / `; true` pattern
# (optionally followed by a shell comment, e.g. `|| true  # flaky`),
# not every possible failure-swallowing shape (found by cross-model-review).
if echo "$COMMAND_SEGMENTS" | grep -qiwE "${CMD_START}(npm test|npm run test|yarn test|pnpm test|jest|vitest|pytest|python -m pytest|go test|cargo test|rspec|phpunit|mvn test|gradle test)" \
    && ! echo "$COMMAND" | grep -qE '(\|\|[[:space:]]*true|;[[:space:]]*true)[[:space:]]*(#.*)?$'; then
    MILESTONE_TYPE="test_pass"
fi

# Git commit
if echo "$COMMAND_SEGMENTS" | grep -qiwE "${CMD_START}git commit"; then
    MILESTONE_TYPE="commit"
fi

# Build commands — same PostToolUse-implies-success and `-w` (not `\b`,
# for BSD-grep portability — see the test-commands comment above) reasoning
# as above (`make build` would otherwise substring-match inside `cmake
# build`).
if echo "$COMMAND_SEGMENTS" | grep -qiwE "${CMD_START}(npm run build|yarn build|pnpm build|cargo build|go build|make build|gradle build|mvn package)"; then
    MILESTONE_TYPE="build"
fi

# Deploy commands — same `-w`/BSD-portability reasoning as above, swept here
# for consistency (this block predates the SUCCESS-gate fix and was already
# live, but shares the same unanchored-substring shape).
if echo "$COMMAND_SEGMENTS" | grep -qiwE "${CMD_START}(deploy|npm run deploy|vercel|netlify|heroku|kubectl apply|docker push)"; then
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
