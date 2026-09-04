#!/usr/bin/env bash
# PostToolUse hook: auto-validate marketplace.json after Write/Edit
# Checks if the edited file is marketplace.json, runs validation if so.

set -euo pipefail

# Read tool use details from stdin
INPUT=$(cat)

# Check if the edited file is marketplace.json
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    path = data.get('tool_input', {}).get('file_path', '')
    print(path)
except:
    print('')
" 2>/dev/null)

if [[ "$FILE_PATH" == *"marketplace.json"* ]]; then
    MARKETPLACE_DIR=$(dirname "$(dirname "$FILE_PATH")")
    if [[ -f "$FILE_PATH" ]]; then
        RESULT=$(cd "$MARKETPLACE_DIR" && claude plugin validate . 2>&1) || true
        if echo "$RESULT" | grep -q "Validation passed"; then
            MSG="marketplace.json validated successfully"
        else
            ERRORS=$(echo "$RESULT" | grep -v "^$" | head -5) || true
            MSG="marketplace.json validation FAILED:
$ERRORS"
        fi
        jq -n --arg msg "$MSG" '{"decision":"block","reason":$msg,"hookSpecificOutput":{"hookEventName":"PostToolUse"}}'
    fi
fi
