#!/bin/bash
# Hook Schema Validator
# Validates hooks.json structure and checks for common issues

set -euo pipefail

# Usage
if [ $# -eq 0 ]; then
  echo "Usage: $0 <path/to/hooks.json>"
  echo ""
  echo "Validates hook configuration file for:"
  echo "  - Valid JSON syntax"
  echo "  - Required fields"
  echo "  - Hook type validity"
  echo "  - Matcher patterns"
  echo "  - Timeout ranges"
  exit 1
fi

HOOKS_FILE="$1"

if [ ! -f "$HOOKS_FILE" ]; then
  echo "❌ Error: File not found: $HOOKS_FILE"
  exit 1
fi

echo "🔍 Validating hooks configuration: $HOOKS_FILE"
echo ""

# Check 1: Valid JSON
echo "Checking JSON syntax..."
if ! jq empty "$HOOKS_FILE" 2>/dev/null; then
  echo "❌ Invalid JSON syntax"
  exit 1
fi
echo "✅ Valid JSON"

# Some jq builds (observed with jq 1.8.1 on Windows/Git Bash) emit CRLF line
# endings from -r mode even for LF-only input, which silently breaks every
# string/regex comparison below (e.g. "PostToolUse\r" != "PostToolUse").
# Strip \r unconditionally so this works regardless of the jq build in use.
jqr() {
  jq -r "$@" "$HOOKS_FILE" | tr -d '\r'
}

# Detect format: plugin hooks.json nests events under a "hooks" object
# ({"description": ..., "hooks": {"EventName": [...]}}); settings.json/.claude
# hooks files put event names directly at the root ({"EventName": [...]}).
if jq -e '(.hooks? // empty) | type == "object"' "$HOOKS_FILE" >/dev/null 2>&1; then
  FORMAT="plugin"
  BASE_PREFIX=".hooks"
  EVENTS_FILTER='.hooks | keys[]'
else
  FORMAT="settings"
  BASE_PREFIX=""
  EVENTS_FILTER='keys[]'
fi

# Check 2: Root structure
echo ""
echo "Checking root structure..."
# Full event list per code.claude.com/docs/en/hooks (verified 2026-07-05; see
# .claude/plugin-rulebook-audit-decisions.md for the audit that reconciled this
# against the previous 9-event list, which false-flagged most real events).
VALID_EVENTS=(
  "SessionStart" "Setup" "UserPromptSubmit" "UserPromptExpansion"
  "PreToolUse" "PermissionRequest" "PermissionDenied" "PostToolUse" "PostToolUseFailure" "PostToolBatch"
  "Notification" "MessageDisplay" "SubagentStart" "SubagentStop" "TaskCreated" "TaskCompleted"
  "Stop" "StopFailure" "TeammateIdle" "InstructionsLoaded" "ConfigChange" "CwdChanged" "FileChanged"
  "WorktreeCreate" "WorktreeRemove" "PreCompact" "PostCompact" "Elicitation" "ElicitationResult" "SessionEnd"
)

if [ "$FORMAT" = "plugin" ]; then
  for key in $(jqr 'keys[]'); do
    if [ "$key" != "description" ] && [ "$key" != "hooks" ]; then
      echo "⚠️  Unknown top-level key: $key (plugin hooks.json only supports 'description' and 'hooks')"
    fi
  done
fi

for event in $(jqr "$EVENTS_FILTER"); do
  found=false
  for valid_event in "${VALID_EVENTS[@]}"; do
    if [ "$event" = "$valid_event" ]; then
      found=true
      break
    fi
  done

  if [ "$found" = false ]; then
    echo "⚠️  Unknown event type: $event"
  fi
done
echo "✅ Root structure valid"

# Check 3: Validate each hook
echo ""
echo "Validating individual hooks..."

error_count=0
warning_count=0

for event in $(jqr "$EVENTS_FILTER"); do
  hook_count=$(jqr "${BASE_PREFIX}.\"$event\" | length")

  for ((i=0; i<hook_count; i++)); do
    # Check matcher exists. Use has("matcher") rather than a value/emptiness
    # test — an empty-string matcher ("") is a valid, documented pattern for
    # events that don't discriminate by tool (Stop, SessionStart, etc.) and
    # must not be reported as a missing field.
    matcher_present=$(jqr "${BASE_PREFIX}.\"$event\"[$i] | has(\"matcher\")")
    if [ "$matcher_present" != "true" ]; then
      echo "❌ $event[$i]: Missing 'matcher' field"
      error_count=$((error_count + 1))
      continue
    fi

    # Check hooks array exists
    hooks=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks // empty")
    if [ -z "$hooks" ] || [ "$hooks" = "null" ]; then
      echo "❌ $event[$i]: Missing 'hooks' array"
      error_count=$((error_count + 1))
      continue
    fi

    # Validate each hook in the array
    hook_array_count=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks | length")

    for ((j=0; j<hook_array_count; j++)); do
      hook_type=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks[$j].type // empty")

      if [ -z "$hook_type" ]; then
        echo "❌ $event[$i].hooks[$j]: Missing 'type' field"
        error_count=$((error_count + 1))
        continue
      fi

      if [ "$hook_type" != "command" ] && [ "$hook_type" != "prompt" ] && [ "$hook_type" != "http" ] && [ "$hook_type" != "mcp_tool" ] && [ "$hook_type" != "agent" ]; then
        echo "❌ $event[$i].hooks[$j]: Invalid type '$hook_type' (must be one of: command, http, mcp_tool, prompt, agent)"
        error_count=$((error_count + 1))
        continue
      fi

      # Check type-specific fields
      if [ "$hook_type" = "command" ]; then
        command=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks[$j].command // empty")
        if [ -z "$command" ]; then
          echo "❌ $event[$i].hooks[$j]: Command hooks must have 'command' field"
          error_count=$((error_count + 1))
        else
          # Check for hardcoded paths
          if [[ "$command" == /* ]] && [[ "$command" != *'${CLAUDE_PLUGIN_ROOT}'* ]]; then
            echo "⚠️  $event[$i].hooks[$j]: Hardcoded absolute path detected. Consider using \${CLAUDE_PLUGIN_ROOT}"
            warning_count=$((warning_count + 1))
          fi
        fi
      elif [ "$hook_type" = "prompt" ] || [ "$hook_type" = "agent" ]; then
        prompt=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks[$j].prompt // empty")
        if [ -z "$prompt" ]; then
          echo "❌ $event[$i].hooks[$j]: '$hook_type' hooks must have 'prompt' field"
          error_count=$((error_count + 1))
        fi

        # Check if prompt-based hooks are used on supported events
        if [ "$hook_type" = "prompt" ] && [ "$event" != "Stop" ] && [ "$event" != "SubagentStop" ] && [ "$event" != "UserPromptSubmit" ] && [ "$event" != "PreToolUse" ]; then
          echo "⚠️  $event[$i].hooks[$j]: Prompt hooks may not be fully supported on $event (best on Stop, SubagentStop, UserPromptSubmit, PreToolUse)"
          warning_count=$((warning_count + 1))
        fi
      elif [ "$hook_type" = "http" ]; then
        url=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks[$j].url // empty")
        if [ -z "$url" ]; then
          echo "❌ $event[$i].hooks[$j]: 'http' hooks must have 'url' field"
          error_count=$((error_count + 1))
        fi
      elif [ "$hook_type" = "mcp_tool" ]; then
        server=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks[$j].server // empty")
        tool=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks[$j].tool // empty")
        if [ -z "$server" ]; then
          echo "❌ $event[$i].hooks[$j]: 'mcp_tool' hooks must have 'server' field"
          error_count=$((error_count + 1))
        fi
        if [ -z "$tool" ]; then
          echo "❌ $event[$i].hooks[$j]: 'mcp_tool' hooks must have 'tool' field"
          error_count=$((error_count + 1))
        fi
      fi

      # Check timeout
      timeout=$(jqr "${BASE_PREFIX}.\"$event\"[$i].hooks[$j].timeout // empty")
      if [ -n "$timeout" ] && [ "$timeout" != "null" ]; then
        if ! [[ "$timeout" =~ ^[0-9]+$ ]]; then
          echo "❌ $event[$i].hooks[$j]: Timeout must be a number"
          error_count=$((error_count + 1))
        elif [ "$timeout" -gt 600 ]; then
          echo "⚠️  $event[$i].hooks[$j]: Timeout $timeout seconds is very high (max 600s)"
          warning_count=$((warning_count + 1))
        elif [ "$timeout" -lt 5 ]; then
          echo "⚠️  $event[$i].hooks[$j]: Timeout $timeout seconds is very low"
          warning_count=$((warning_count + 1))
        fi
      fi
    done
  done
done

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
