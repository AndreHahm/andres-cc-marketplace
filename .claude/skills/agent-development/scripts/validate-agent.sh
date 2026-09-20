#!/bin/bash
# Agent File Validator
# Validates agent markdown files for correct structure and content

set -euo pipefail

# Usage
if [ $# -eq 0 ]; then
  echo "Usage: $0 <path/to/agent.md>"
  echo ""
  echo "Validates agent file for:"
  echo "  - YAML frontmatter structure"
  echo "  - Required fields (name, description, model, color, tools)"
  echo "  - Field formats and constraints"
  echo "  - System prompt presence and length"
  echo "  - Example blocks in description"
  exit 1
fi

AGENT_FILE="$1"

echo "🔍 Validating agent file: $AGENT_FILE"
echo ""

# Check 1: File exists
if [ ! -f "$AGENT_FILE" ]; then
  echo "❌ File not found: $AGENT_FILE"
  exit 1
fi
echo "✅ File exists"

# Check 2: Starts with ---
FIRST_LINE=$(head -1 "$AGENT_FILE")
if [ "$FIRST_LINE" != "---" ]; then
  echo "❌ File must start with YAML frontmatter (---)"
  exit 1
fi
echo "✅ Starts with frontmatter"

# Check 3: Has closing ---
if ! tail -n +2 "$AGENT_FILE" | grep -q '^---$'; then
  echo "❌ Frontmatter not closed (missing second ---)"
  exit 1
fi
echo "✅ Frontmatter properly closed"

# Extract frontmatter and system prompt
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$AGENT_FILE")
SYSTEM_PROMPT=$(awk '/^---$/{i++; next} i>=2' "$AGENT_FILE")

# Check 4: Required fields
echo ""
echo "Checking required fields..."

error_count=0
warning_count=0

# Check name field
NAME=$(echo "$FRONTMATTER" | grep '^name:' | sed 's/name: *//' | sed 's/^"\(.*\)"$/\1/') || true

if [ -z "$NAME" ]; then
  echo "❌ Missing required field: name"
  error_count=$((error_count+1))
else
  echo "✅ name: $NAME"

  # Validate name format
  if ! [[ "$NAME" =~ ^[a-z0-9][a-z0-9-]*[a-z0-9]$ ]]; then
    echo "❌ name must be lowercase, start/end with alphanumeric, and contain only letters, numbers, hyphens"
    error_count=$((error_count+1))
  fi

  # Validate name length
  name_length=${#NAME}
  if [ $name_length -lt 3 ]; then
    echo "❌ name too short (minimum 3 characters)"
    error_count=$((error_count+1))
  elif [ $name_length -gt 64 ]; then
    echo "❌ name too long (maximum 64 characters)"
    error_count=$((error_count+1))
  fi

  # Check for generic names
  if [[ "$NAME" =~ ^(helper|assistant|agent|tool)$ ]]; then
    echo "⚠️  name is too generic: $NAME"
    warning_count=$((warning_count+1))
  fi
fi

# Check description field
# Supports both single-line ("description: text") and YAML block-scalar
# ("description: >-" or "description: |" followed by indented lines) forms —
# the latter is required by this plugin's own R8 rule for descriptions over
# 80 characters, so nearly every compliant agent uses it.
DESCRIPTION=$(echo "$FRONTMATTER" | awk '
  /^description:/ {
    line = $0
    sub(/^description: */, "", line)
    if (line == ">-" || line == ">" || line == "|-" || line == "|") {
      in_block = 1
      next
    }
    gsub(/^"/, "", line)
    gsub(/"$/, "", line)
    print line
    exit
  }
  in_block {
    if ($0 !~ /^[ \t]/) { exit }
    text = $0
    sub(/^[ \t]+/, "", text)
    out = (out == "") ? text : out " " text
    next
  }
  END { if (in_block) print out }
')

if [ -z "$DESCRIPTION" ]; then
  echo "❌ Missing required field: description"
  error_count=$((error_count+1))
else
  desc_length=${#DESCRIPTION}
  echo "✅ description: ${desc_length} characters"

  if [ $desc_length -lt 10 ]; then
    echo "⚠️  description too short (minimum 10 characters recommended)"
    warning_count=$((warning_count+1))
  elif [ $desc_length -gt 5000 ]; then
    echo "⚠️  description very long (over 5000 characters)"
    warning_count=$((warning_count+1))
  fi

  # Check for example blocks (avoid in description — use body "When to invoke" section instead)
  if echo "$DESCRIPTION" | grep -q '<example>'; then
    echo "⚠️  Avoid <example> blocks in description — put trigger scenarios in body '## When to invoke' section instead"
    warning_count=$((warning_count+1))
  fi

  # Check for a trigger-condition clause. Official examples use varied phrasing
  # ("Use when...", "Use proactively...", "Trigger proactively after...") rather
  # than one fixed sentence, so match any of those instead of a single literal.
  if ! echo "$DESCRIPTION" | grep -qiE 'use (this agent |proactively|when)|trigger (proactively|when)'; then
    echo "⚠️  description should include a trigger-condition clause (e.g. 'Use when...', 'Trigger proactively after...')"
    warning_count=$((warning_count+1))
  fi
fi

# Check model field
MODEL=$(echo "$FRONTMATTER" | grep '^model:' | sed 's/model: *//') || true

if [ -z "$MODEL" ]; then
  echo "❌ Missing required field: model"
  error_count=$((error_count+1))
else
  echo "✅ model: $MODEL"

  case "$MODEL" in
    inherit|sonnet|opus|haiku|fable)
      # Valid model
      ;;
    claude-*)
      # Valid full model ID string (e.g. claude-sonnet-4-5)
      ;;
    *)
      echo "⚠️  Unknown model: $MODEL (valid: inherit, sonnet, opus, haiku, fable, or a full model ID string e.g. claude-sonnet-4-5)"
      warning_count=$((warning_count+1))
      ;;
  esac
fi

# Check color field
COLOR=$(echo "$FRONTMATTER" | grep '^color:' | sed 's/color: *//') || true

if [ -z "$COLOR" ]; then
  echo "❌ Missing required field: color"
  error_count=$((error_count+1))
else
  echo "✅ color: $COLOR"

  case "$COLOR" in
    red|blue|green|yellow|purple|orange|pink|cyan)
      # Valid color
      ;;
    magenta)
      echo "⚠️  Deprecated color: magenta is no longer listed in current platform docs (valid: red, blue, green, yellow, purple, orange, pink, cyan)"
      warning_count=$((warning_count+1))
      ;;
    *)
      echo "⚠️  Unknown color: $COLOR (valid: red, blue, green, yellow, purple, orange, pink, cyan)"
      warning_count=$((warning_count+1))
      ;;
  esac
fi

# Check tools field
TOOLS=$(echo "$FRONTMATTER" | grep '^tools:' | sed 's/tools: *//') || true

if [ -n "$TOOLS" ]; then
  echo "✅ tools: $TOOLS"
else
  echo "❌ Missing required field: tools (omitting it grants access to ALL tools; least privilege requires an explicit, scoped list)"
  error_count=$((error_count+1))
fi

# Check for a description/tools contradiction: a description claiming read-only
# or review-only behavior must not pair with a tools list containing Bash, Write, or Edit
if [ -n "$TOOLS" ] && [ -n "${DESCRIPTION:-}" ]; then
  # "review only"/"analysis only" (spaced) are deliberately excluded: they read as a scope
  # limiter in ordinary language ("review only the files changed by this PR") at least as often
  # as a capability claim, and would false-positive on the former. Only the hyphenated compound
  # forms are unambiguous capability claims. "read only" isn't excluded the same way -- it doesn't
  # have the same natural scope-limiter reading in this context.
  if echo "$DESCRIPTION" | grep -qiE 'read-only|read only|review-only|analysis-only'; then
    if echo "$TOOLS" | grep -qE '\b(Bash|Write|Edit)\b'; then
      echo "❌ description claims read-only/review-only/analysis-only behavior but tools includes Bash/Write/Edit"
      error_count=$((error_count+1))
    fi
  fi
fi

# Check 5: System prompt
echo ""
echo "Checking system prompt..."

if [ -z "$SYSTEM_PROMPT" ]; then
  echo "❌ System prompt is empty"
  error_count=$((error_count+1))
else
  prompt_length=${#SYSTEM_PROMPT}
  echo "✅ System prompt: $prompt_length characters"

  if [ $prompt_length -lt 20 ]; then
    echo "❌ System prompt too short (minimum 20 characters)"
    error_count=$((error_count+1))
  elif [ $prompt_length -gt 10000 ]; then
    echo "⚠️  System prompt very long (over 10,000 characters)"
    warning_count=$((warning_count+1))
  fi

  # Check for second person
  if ! echo "$SYSTEM_PROMPT" | grep -q "You are\|You will\|Your"; then
    echo "⚠️  System prompt should use second person (You are..., You will...)"
    warning_count=$((warning_count+1))
  fi

  # Check for structure
  if ! echo "$SYSTEM_PROMPT" | grep -qi "responsibilities\|process\|steps"; then
    echo "💡 Consider adding clear responsibilities or process steps"
  fi

  if ! echo "$SYSTEM_PROMPT" | grep -qi "output"; then
    echo "💡 Consider defining output format expectations"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $error_count -eq 0 ] && [ $warning_count -eq 0 ]; then
  echo "✅ All checks passed!"
  exit 0
elif [ $error_count -eq 0 ]; then
  echo "⚠️  Validation passed with $warning_count warning(s)"
  exit 0
else
  echo "❌ Validation failed with $error_count error(s) and $warning_count warning(s)"
  exit 1
fi
