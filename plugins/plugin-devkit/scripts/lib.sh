#!/bin/bash

# Shared utilities for skill-improver plugin.
# Keys must be literal alphanumeric/underscore strings.

# Parse a YAML frontmatter field from a markdown file.
# Usage: parse_field <file> <key>
parse_field() {
  local file="$1" key="$2"
  sed -n '/^---$/,/^---$/{
    /^'"$key"':/{ s/'"$key"': *//; s/^["'"'"']//; s/["'"'"']$//; p; q; }
  }' "$file" 2>/dev/null || echo ""
}

# Extract session ID from a state file path.
# Usage: extract_session_id <filepath>
extract_session_id() {
  basename "$1" | sed 's/skill-improver\.\(.*\)\.local\.md/\1/'
}

# Remove a state file, using trash if available, falling back to rm -f.
# trash is not guaranteed to be installed; under set -e a missing binary
# would otherwise abort the caller before it can clean up or exit 0.
# Usage: safe_trash <filepath>
safe_trash() {
  if command -v trash >/dev/null 2>&1; then
    trash "$1"
  else
    rm -f "$1"
  fi
}