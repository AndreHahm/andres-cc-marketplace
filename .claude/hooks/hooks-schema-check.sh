#!/bin/bash

# PostToolUse hook: runs hook-development's validate-hook-schema.sh live whenever a
# plugin hooks.json file is written/edited. That script was previously manual-only
# (run by hand or by instruction); this wrapper backs it with an always-on,
# live PostToolUse check instead.
#
# Scoped to files literally named hooks.json — the validator's designed input and
# the plugin hooks/hooks.json format. Deliberately NOT wired to .claude/settings.json:
# that file mixes a "hooks" object with unrelated top-level keys (env, permissions,
# model, ...), which validate-hook-schema.sh's plugin-vs-settings format detection
# does not yet handle correctly (would misreport those keys as "unknown top-level
# key"); fixing that is a separate, not-yet-requested change.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR="$SCRIPT_DIR/../skills/hook-development/scripts/validate-hook-schema.sh"

INPUT="$(cat)"
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' | tr -d '\r')

[[ "$FILE_PATH" == *hooks.json ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

OUTPUT="$(bash "$VALIDATOR" "$FILE_PATH" 2>&1)"
STATUS=$?

if [[ $STATUS -ne 0 ]]; then
  jq -n --arg msg "hooks.json schema check failed:
$OUTPUT" '{"decision":"block","reason":$msg,"hookSpecificOutput":{"hookEventName":"PostToolUse"}}'
fi
