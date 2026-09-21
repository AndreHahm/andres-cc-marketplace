#!/bin/bash
# Strategic Compact - Skill Category Detector
# Runs on PreToolUse (arg "start") and PostToolUse (arg "finish") for Skill
# calls to detect a known "heavy_operation" or "session_analysis" skill
# beginning or completing, and suggests /compact accordingly -- both
# directions fire, with different wording, no cooldown between them: each
# Skill() invocation is a fresh, bounded event worth its own suggestion
# every time, not a potentially-noisy repeated command the way
# compact-milestone-detector.sh's Bash patterns can be.
#
# Unlike compact-track-and-suggest.sh / compact-milestone-detector.sh, this
# script never reads or writes $TRACK_FILE's own counters, so it never
# takes the mkdir-based lock those two scripts share -- it only checks
# $TRACK_FILE's existence, the same "session already initialized"
# precondition the other hooks use, and delivers its own suggestion
# directly via this call's own JSON output (synchronous, not routed
# through the pending-file/Stop-hook relay).
#
# Category lists: git-tracked defaults at
# ${CLAUDE_PLUGIN_ROOT}/hooks/context-kit.settings.json (deliberately placed
# inside hooks/, a real plugin-mirror component directory, rather than at
# the plugin root -- see issue #316: a plugin-root-level file is silently
# never mirrored into this repo's own .claude/ dogfooding checkout, and this
# file would otherwise inherit that exact gap), additively merged with an
# optional local override at ${CLAUDE_PROJECT_DIR}/.claude/context-kit.local.json
# (gitignored, project-specific -- adds skills, never replaces the shipped
# defaults). Requires jq: this classification needs real JSON array
# membership, not a regex approximation, so this script fails open (silently,
# no suggestion) rather than attempt one when jq is unavailable.

PHASE="$1"  # "start" or "finish"

INPUT=$(cat)

if ! command -v jq &>/dev/null; then
    exit 0
fi

SKILL_NAME=$(echo "$INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

[ -z "$SKILL_NAME" ] && exit 0

# Sanity-check the skill name is plausibly a real component identifier
# (R4 kebab-case) before using it in a suggestion or a jq array lookup --
# defense-in-depth, not a correctness requirement (the jq lookup below is
# safe against any string either way).
[[ "$SKILL_NAME" =~ ^[a-z][a-z0-9-]*$ ]] || exit 0

# Get session hash (same pattern as sibling scripts)
if command -v md5sum &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5sum | cut -c1-8)
elif command -v md5 &>/dev/null; then
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5 | cut -c1-8)
else
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | cksum | cut -d' ' -f1)
fi

TRACK_DIR="${HOME:-${USERPROFILE:-/tmp}}/.claude/strategic-compact"
TRACK_FILE="${TRACK_DIR}/session-${SESSION_HASH}"

# Exit if no tracking file -- compact-session-init.sh hasn't run for this
# session yet (same precondition compact-milestone-detector.sh uses).
[ ! -f "$TRACK_FILE" ] && exit 0

DEFAULTS_FILE="${CLAUDE_PLUGIN_ROOT}/hooks/context-kit.settings.json"
[ ! -f "$DEFAULTS_FILE" ] && exit 0

LOCAL_FILE="${CLAUDE_PROJECT_DIR:-}/.claude/context-kit.local.json"

if [ -n "$CLAUDE_PROJECT_DIR" ] && [ -f "$LOCAL_FILE" ]; then
    CATEGORIES=$(jq -s '{
        heavy_operation: (((.[0].skill_categories.heavy_operation // []) + (.[1].skill_categories.heavy_operation // [])) | unique),
        session_analysis: (((.[0].skill_categories.session_analysis // []) + (.[1].skill_categories.session_analysis // [])) | unique)
    }' "$DEFAULTS_FILE" "$LOCAL_FILE" 2>/dev/null)
else
    CATEGORIES=$(jq '{
        heavy_operation: (.skill_categories.heavy_operation // []),
        session_analysis: (.skill_categories.session_analysis // [])
    }' "$DEFAULTS_FILE" 2>/dev/null)
fi

[ -z "$CATEGORIES" ] && exit 0

# Priority on overlap: heavy_operation wins over session_analysis (the
# more resource-costly classification, matching compact-milestone-detector.sh's
# own later-in-the-list-wins precedent for a chained command matching more
# than one milestone pattern).
CATEGORY=""
if echo "$CATEGORIES" | jq -e --arg s "$SKILL_NAME" '.heavy_operation | index($s)' >/dev/null 2>&1; then
    CATEGORY="heavy_operation"
elif echo "$CATEGORIES" | jq -e --arg s "$SKILL_NAME" '.session_analysis | index($s)' >/dev/null 2>&1; then
    CATEGORY="session_analysis"
fi

[ -z "$CATEGORY" ] && exit 0

SUGGESTION=""
case "${CATEGORY}:${PHASE}" in
    heavy_operation:start)
        SUGGESTION="[StrategicCompact] About to run '${SKILL_NAME}', a known heavy operation. Consider /compact first so it runs against a clean context budget."
        ;;
    heavy_operation:finish)
        SUGGESTION="[StrategicCompact] '${SKILL_NAME}' (heavy operation) finished. Good time for /compact -- its own dispatch/report context is no longer needed."
        ;;
    session_analysis:start)
        SUGGESTION="[StrategicCompact] About to run '${SKILL_NAME}', a session-analysis skill. Consider /compact first so it runs against a clean context budget."
        ;;
    session_analysis:finish)
        SUGGESTION="[StrategicCompact] '${SKILL_NAME}' (session analysis) finished. Good time for /compact -- its own transcript-reading context is no longer needed."
        ;;
esac

[ -z "$SUGGESTION" ] && exit 0

HOOK_EVENT_NAME="PostToolUse"
[ "$PHASE" = "start" ] && HOOK_EVENT_NAME="PreToolUse"

# Built via jq -n --arg, not heredoc string interpolation -- $SKILL_NAME is
# embedded in $SUGGESTION and, while it should always be a real registered
# skill name, this is the same safe-construction discipline
# compact-stop-check.sh already uses for suggestion text that could contain
# a character that would otherwise break the JSON shape.
jq -n --arg msg "$SUGGESTION" --arg event "$HOOK_EVENT_NAME" \
    '{systemMessage: $msg, hookSpecificOutput: {hookEventName: $event, additionalContext: $msg}}'

exit 0
