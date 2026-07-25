#!/bin/bash
# Validate a command file's frontmatter fields: model value, allowed-tools presence, description length.

set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: $0 <command-file.md>"
  exit 1
fi

COMMAND_FILE="$1"

FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$COMMAND_FILE" | sed '1d;$d')

if [ -z "$FRONTMATTER" ]; then
  echo "No frontmatter to validate"
  exit 0
fi

if echo "$FRONTMATTER" | grep -q "^model:"; then
  MODEL=$(echo "$FRONTMATTER" | grep "^model:" | cut -d: -f2 | tr -d ' ')
  if ! echo "sonnet opus haiku fable inherit" | grep -qw "$MODEL" && [[ "$MODEL" != claude-* ]]; then
    echo "ERROR: Invalid model '$MODEL' (must be sonnet, opus, haiku, fable, inherit, or a full model ID string e.g. claude-sonnet-4-5)"
    exit 1
  fi
  echo "OK: Model field valid: $MODEL"
fi

if echo "$FRONTMATTER" | grep -q "^allowed-tools:"; then
  echo "OK: allowed-tools field present"
fi

if echo "$FRONTMATTER" | grep -q "^description:"; then
  DESC=$(echo "$FRONTMATTER" | grep "^description:" | cut -d: -f2-)
  LENGTH=${#DESC}
  if [ "$LENGTH" -gt 80 ]; then
    echo "WARNING: Description length $LENGTH (recommend < 60 chars, shown truncated in /help beyond that)"
  else
    echo "OK: Description length acceptable: $LENGTH chars"
  fi
fi

echo "OK: Frontmatter fields valid"
