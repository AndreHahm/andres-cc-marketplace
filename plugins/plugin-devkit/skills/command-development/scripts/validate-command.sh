#!/bin/bash
# Validate a command file's basic structure: extension, location, frontmatter markers, non-empty.

set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: $0 <command-file.md>"
  exit 1
fi

COMMAND_FILE="$1"

if [ ! -f "$COMMAND_FILE" ]; then
  echo "ERROR: File not found: $COMMAND_FILE"
  exit 1
fi

if [[ ! "$COMMAND_FILE" =~ \.md$ ]]; then
  echo "ERROR: File must have .md extension"
  exit 1
fi

if [ ! -s "$COMMAND_FILE" ]; then
  echo "ERROR: File is empty"
  exit 1
fi

if head -n 1 "$COMMAND_FILE" | grep -q "^---"; then
  MARKERS=$(head -n 50 "$COMMAND_FILE" | grep -c "^---")
  if [ "$MARKERS" -ne 2 ]; then
    echo "ERROR: Invalid YAML frontmatter (need exactly 2 '---' markers)"
    exit 1
  fi
  echo "OK: YAML frontmatter syntax valid"
fi

echo "OK: Command file structure valid"
