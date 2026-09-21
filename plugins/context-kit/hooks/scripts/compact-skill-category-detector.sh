#!/bin/bash
# Strategic Compact - Skill Category Detector
# Runs on PreToolUse for Skill calls to detect a known "heavy_operation" or
# "session_analysis" skill about to start, and suggests /compact accordingly
# if it's been a while.
#
# PreToolUse-only by design (no PostToolUse "finish" counterpart): a Skill()
# call's own PostToolUse event fires once the skill's instructions have
# loaded into the conversation as a message, not once the model has actually
# finished executing the workflow those instructions describe (see
# plugin-devkit's skill-development/references/design-patterns.md, "Skill
# content lifecycle") -- there is no hook event in Claude Code that fires on
# real workflow completion for a foreground skill. An earlier version of this
# script wired both phases and had PostToolUse claim the skill "finished";
# that claim was false almost every time it fired (found by Codex's
# automated PR review, 2026-09-21, against PR #368). Rather than keep a
# message that reads as factually wrong most of the time, the finish phase
# was dropped entirely.
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
    SESSION_HASH=$(echo "${SESSION_ID:-default}" | md5 -q | cut -c1-8)
else
    # No md5 tool available -- fail open rather than fall back to a
    # different hash algorithm (cksum). See compact-session-init.sh's
    # matching comment for the full rationale (found by cross-model-review,
    # 2026-09-21).
    exit 0
fi

TRACK_DIR="${HOME:-${USERPROFILE:-/tmp}}/.claude/strategic-compact"
TRACK_FILE="${TRACK_DIR}/session-${SESSION_HASH}"

# Exit if no tracking file -- compact-session-init.sh hasn't run for this
# session yet (same precondition compact-milestone-detector.sh uses).
[ ! -f "$TRACK_FILE" ] && exit 0

# Guard against an unset CLAUDE_PLUGIN_ROOT the same way LOCAL_FILE below already
# guards CLAUDE_PROJECT_DIR -- unguarded, this would build the root-relative path
# "/hooks/context-kit.settings.json", which on Windows/Git-Bash is subject to
# MSYS's automatic POSIX-to-Windows path translation rather than failing cleanly
# (found by scripts-reviewer, 2026-09-21).
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && exit 0
DEFAULTS_FILE="${CLAUDE_PLUGIN_ROOT:-}/hooks/context-kit.settings.json"
[ ! -f "$DEFAULTS_FILE" ] && exit 0

DEFAULTS_CATEGORIES=$(jq '{
    heavy_operation: (.skill_categories.heavy_operation // []),
    session_analysis: (.skill_categories.session_analysis // [])
}' "$DEFAULTS_FILE" 2>/dev/null)

[ -z "$DEFAULTS_CATEGORIES" ] && exit 0

LOCAL_FILE="${CLAUDE_PROJECT_DIR:-}/.claude/context-kit.local.json"
CATEGORIES="$DEFAULTS_CATEGORIES"

if [ -n "$CLAUDE_PROJECT_DIR" ] && [ -f "$LOCAL_FILE" ]; then
    LOCAL_CATEGORIES=$(jq '{
        heavy_operation: (.skill_categories.heavy_operation // []),
        session_analysis: (.skill_categories.session_analysis // [])
    }' "$LOCAL_FILE" 2>/dev/null)
    if [ -n "$LOCAL_CATEGORIES" ]; then
        # Additive merge, each file parsed independently -- a malformed
        # local override (invalid JSON, wrong types) must never take the
        # shipped defaults down with it. The prior version ran both files
        # through one combined `jq -s` call, so a parse failure on the
        # local file alone emptied CATEGORIES entirely, silently disabling
        # even shipped-default skills (found by Codex + CodeRabbit's
        # automated PR reviews, 2026-09-21, against PR #368 -- contradicted
        # this skill's own documented "additive, never replaces" contract).
        MERGED_CATEGORIES=$(jq -n --argjson d "$DEFAULTS_CATEGORIES" --argjson l "$LOCAL_CATEGORIES" '{
            heavy_operation: (($d.heavy_operation + $l.heavy_operation) | unique),
            session_analysis: (($d.session_analysis + $l.session_analysis) | unique)
        }' 2>/dev/null)
        [ -n "$MERGED_CATEGORIES" ] && CATEGORIES="$MERGED_CATEGORIES"
    else
        echo "compact-skill-category-detector.sh: local override file is malformed JSON; using shipped defaults only" >&2
    fi
fi

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
case "$CATEGORY" in
    heavy_operation)
        SUGGESTION="[StrategicCompact] '${SKILL_NAME}' is a known heavy operation. If you haven't compacted recently, this is a good moment to."
        ;;
    session_analysis)
        SUGGESTION="[StrategicCompact] '${SKILL_NAME}' is a session-analysis skill. If you haven't compacted recently, this is a good moment to."
        ;;
esac

[ -z "$SUGGESTION" ] && exit 0

# Built via jq -n --arg, not heredoc string interpolation -- $SKILL_NAME is
# embedded in $SUGGESTION and, while it should always be a real registered
# skill name, this is the same safe-construction discipline
# compact-stop-check.sh already uses for suggestion text that could contain
# a character that would otherwise break the JSON shape.
jq -n --arg msg "$SUGGESTION" \
    '{systemMessage: $msg, hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $msg}}'

exit 0
