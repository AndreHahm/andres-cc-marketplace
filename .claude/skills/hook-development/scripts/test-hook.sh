#!/bin/bash
# Hook Testing Helper
# Tests a hook with sample input and shows output

set -euo pipefail

# Usage
show_usage() {
  echo "Usage: $0 [options] <hook-script> <test-input.json>"
  echo ""
  echo "Options:"
  echo "  -h, --help      Show this help message"
  echo "  -v, --verbose   Show detailed execution information"
  echo "  -t, --timeout N Set timeout in seconds (default: 60)"
  echo "  --json          Emit a machine-readable JSON result document instead of"
  echo "                  the default human-readable text (implies non-verbose)"
  echo "  --yaml          Same as --json, YAML-formatted instead"
  echo ""
  echo "Examples:"
  echo "  $0 validate-bash.sh test-input.json"
  echo "  $0 -v -t 30 validate-write.sh write-input.json"
  echo "  $0 --json validate-bash.sh test-input.json"
  echo ""
  echo "Creates sample test input with:"
  echo "  $0 --create-sample <event-type>"
  exit 0
}

# Create sample input
create_sample() {
  event_type="$1"

  case "$event_type" in
    PreToolUse)
      cat <<'EOF'
{
  "session_id": "test-session",
  "transcript_path": "/tmp/transcript.txt",
  "cwd": "/tmp/test-project",
  "permission_mode": "ask",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/tmp/test.txt",
    "content": "Test content"
  }
}
EOF
      ;;
    PostToolUse)
      cat <<'EOF'
{
  "session_id": "test-session",
  "transcript_path": "/tmp/transcript.txt",
  "cwd": "/tmp/test-project",
  "permission_mode": "ask",
  "hook_event_name": "PostToolUse",
  "tool_name": "Bash",
  "tool_result": "Command executed successfully"
}
EOF
      ;;
    Stop|SubagentStop)
      cat <<'EOF'
{
  "session_id": "test-session",
  "transcript_path": "/tmp/transcript.txt",
  "cwd": "/tmp/test-project",
  "permission_mode": "ask",
  "hook_event_name": "Stop",
  "reason": "Task appears complete"
}
EOF
      ;;
    UserPromptSubmit)
      cat <<'EOF'
{
  "session_id": "test-session",
  "transcript_path": "/tmp/transcript.txt",
  "cwd": "/tmp/test-project",
  "permission_mode": "ask",
  "hook_event_name": "UserPromptSubmit",
  "user_prompt": "Test user prompt"
}
EOF
      ;;
    SessionStart|SessionEnd)
      cat <<'EOF'
{
  "session_id": "test-session",
  "transcript_path": "/tmp/transcript.txt",
  "cwd": "/tmp/test-project",
  "permission_mode": "ask",
  "hook_event_name": "SessionStart"
}
EOF
      ;;
    *)
      echo "Unknown event type: $event_type"
      echo "Valid types: PreToolUse, PostToolUse, Stop, SubagentStop, UserPromptSubmit, SessionStart, SessionEnd"
      exit 1
      ;;
  esac
}

# Parse arguments
VERBOSE=false
TIMEOUT=60
OUTPUT_FORMAT="text"

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      show_usage
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -t|--timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --json)
      OUTPUT_FORMAT="json"
      VERBOSE=false
      shift
      ;;
    --yaml)
      OUTPUT_FORMAT="yaml"
      VERBOSE=false
      shift
      ;;
    --create-sample)
      create_sample "$2"
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

if [ $# -ne 2 ]; then
  echo "Error: Missing required arguments"
  echo ""
  show_usage
fi

HOOK_SCRIPT="$1"
TEST_INPUT="$2"

# Validate inputs
if [ ! -f "$HOOK_SCRIPT" ]; then
  echo "❌ Error: Hook script not found: $HOOK_SCRIPT"
  exit 1
fi

if [ ! -x "$HOOK_SCRIPT" ]; then
  echo "⚠️  Warning: Hook script is not executable. Attempting to run with bash..."
  RUN_CMD=(bash "$HOOK_SCRIPT")
else
  RUN_CMD=("$HOOK_SCRIPT")
fi

if [ ! -f "$TEST_INPUT" ]; then
  echo "❌ Error: Test input not found: $TEST_INPUT"
  exit 1
fi

# Validate test input JSON
if ! jq empty "$TEST_INPUT" 2>/dev/null; then
  echo "❌ Error: Test input is not valid JSON"
  exit 1
fi

if [ "$OUTPUT_FORMAT" = "text" ]; then
  echo "🧪 Testing hook: $HOOK_SCRIPT"
  echo "📥 Input: $TEST_INPUT"
  echo ""

  if [ "$VERBOSE" = true ]; then
    echo "Input JSON:"
    jq . "$TEST_INPUT"
    echo ""
  fi
fi

# Set up environment
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-/tmp/test-project}"
export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(pwd)}"
export CLAUDE_ENV_FILE="${CLAUDE_ENV_FILE:-/tmp/test-env-$$}"

if [ "$OUTPUT_FORMAT" = "text" ] && [ "$VERBOSE" = true ]; then
  echo "Environment:"
  echo "  CLAUDE_PROJECT_DIR=$CLAUDE_PROJECT_DIR"
  echo "  CLAUDE_PLUGIN_ROOT=$CLAUDE_PLUGIN_ROOT"
  echo "  CLAUDE_ENV_FILE=$CLAUDE_ENV_FILE"
  echo ""
fi

# Run the hook
if [ "$OUTPUT_FORMAT" = "text" ]; then
  echo "▶️  Running hook (timeout: ${TIMEOUT}s)..."
  echo ""
fi

start_time=$(date +%s)

set +e
# argv-based invocation (RUN_CMD array), not a `bash -c "...$HOOK_SCRIPT..."` string
# — HOOK_SCRIPT is a path from the plugin/component under test and must never be
# re-parsed by a shell, since a crafted filename (shell metacharacters) would
# otherwise be a command-injection vector here.
output=$(cat "$TEST_INPUT" | timeout "$TIMEOUT" "${RUN_CMD[@]}" 2>&1)
exit_code=$?
set -e

end_time=$(date +%s)
duration=$((end_time - start_time))

# Classify the result -- same exit-code contract test-hook.sh has always used
# (0/2 are both valid hook completions; 124 is a timeout; anything else is
# unexpected), now computed once and reused by both the text and structured
# output paths instead of being embedded only in echo statements.
case $exit_code in
  0)
    classification="approved"
    status="pass"
    ;;
  2)
    classification="blocked"
    status="pass"
    ;;
  124)
    classification="timeout"
    status="fail"
    ;;
  *)
    classification="unexpected"
    status="fail"
    ;;
esac

output_is_json=false
if echo "$output" | jq empty 2>/dev/null; then
  output_is_json=true
fi

env_file_created=false
if [ -f "$CLAUDE_ENV_FILE" ]; then
  env_file_created=true
fi

if [ "$OUTPUT_FORMAT" = "text" ]; then
  # Analyze results
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Results:"
  echo ""
  echo "Exit Code: $exit_code"
  echo "Duration: ${duration}s"
  echo ""

  case "$classification" in
    approved) echo "✅ Hook approved/succeeded" ;;
    blocked) echo "🚫 Hook blocked/denied" ;;
    timeout) echo "⏱️  Hook timed out after ${TIMEOUT}s" ;;
    unexpected) echo "⚠️  Hook returned unexpected exit code: $exit_code" ;;
  esac

  echo ""
  echo "Output:"
  if [ -n "$output" ]; then
    echo "$output"
    echo ""

    if [ "$output_is_json" = true ]; then
      echo "Parsed JSON output:"
      echo "$output" | jq .
    fi
  else
    echo "(no output)"
  fi

  if [ "$env_file_created" = true ]; then
    echo ""
    echo "Environment file created:"
    cat "$CLAUDE_ENV_FILE"
    rm -f "$CLAUDE_ENV_FILE"
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [ "$status" = "pass" ]; then
    echo "✅ Test completed successfully"
  else
    echo "❌ Test failed"
  fi
elif [ "$OUTPUT_FORMAT" = "json" ]; then
  if [ "$env_file_created" = true ]; then
    rm -f "$CLAUDE_ENV_FILE"
  fi
  jq -n \
    --arg version "1.0" \
    --arg source "test-hook.sh" \
    --arg hook_script "$HOOK_SCRIPT" \
    --arg test_input "$TEST_INPUT" \
    --argjson exit_code "$exit_code" \
    --argjson duration_seconds "$duration" \
    --arg classification "$classification" \
    --arg status "$status" \
    --arg output "$output" \
    --argjson output_is_json "$output_is_json" \
    --argjson env_file_created "$env_file_created" \
    '{version: $version, source: $source, hook_script: $hook_script, test_input: $test_input, exit_code: $exit_code, duration_seconds: $duration_seconds, classification: $classification, status: $status, output_is_json: $output_is_json, env_file_created: $env_file_created, output: $output}'
else
  # yaml -- hand-formatted, no extra dependency for this simple shape.
  # `output` uses a block scalar so embedded quotes/colons/newlines never
  # need escaping.
  if [ "$env_file_created" = true ]; then
    rm -f "$CLAUDE_ENV_FILE"
  fi
  echo 'version: "1.0"'
  echo "source: test-hook.sh"
  echo "hook_script: $HOOK_SCRIPT"
  echo "test_input: $TEST_INPUT"
  echo "exit_code: $exit_code"
  echo "duration_seconds: $duration"
  echo "classification: $classification"
  echo "status: $status"
  echo "output_is_json: $output_is_json"
  echo "env_file_created: $env_file_created"
  echo "output: |"
  if [ -n "$output" ]; then
    echo "$output" | sed 's/^/  /'
  fi
fi

[ "$status" = "pass" ] && exit 0 || exit 1
