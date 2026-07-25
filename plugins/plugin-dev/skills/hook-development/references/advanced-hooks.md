# Advanced Hook Patterns and Use Cases

Production-grade patterns for complex hook scenarios, advanced use cases, and sophisticated automation workflows.

**R18 exception (recorded):** several examples below intentionally exceed the rulebook's 30-line code-block threshold — each is a complete, runnable `hooks.json` configuration or standalone test/example script for one named pattern; splitting one would leave a non-functional fragment. Matches this plugin's established R18 exception pattern (see `command-development/references/marketplace-considerations.md`).

## Table of Contents

- [Pattern 1: Conditional Execution](#pattern-1-conditional-execution)
- [Pattern 2: Sequential Hooks with Fallback](#pattern-2-sequential-hooks-with-fallback)
- [Pattern 3: Rate Limiting](#pattern-3-rate-limiting)
- [Pattern 4: Caching Results](#pattern-4-caching-results)
- [Pattern 5: Multiple Tool Matchers with Different Actions](#pattern-5-multiple-tool-matchers-with-different-actions)
- [Pattern 6: Event Chaining (Upstream/Downstream)](#pattern-6-event-chaining-upstreamdownstream)
- [Pattern 7: Idempotent Updates](#pattern-7-idempotent-updates)
- [Pattern 8: Validation Before Blocking](#pattern-8-validation-before-blocking)
- [Pattern 9: Async Hook for Slow Operations](#pattern-9-async-hook-for-slow-operations)
- [Pattern 10: Multi-Stage Verification](#pattern-10-multi-stage-verification)
- [Pattern 11: Conditional Blocking Based on Context](#pattern-11-conditional-blocking-based-on-context)
- [Pattern 12: Logging & Monitoring Integration](#pattern-12-logging--monitoring-integration)
- [Pattern 13: Environment-Based Hook Behavior](#pattern-13-environment-based-hook-behavior)
- [Pattern 14: Retry Logic](#pattern-14-retry-logic)
- [Pattern 15: Complex Decision Agent](#pattern-15-complex-decision-agent)
- [Pattern 16: Multi-Stage Command + Prompt Validation](#pattern-16-multi-stage-command--prompt-validation)
- [Pattern 17: Hook Chaining via State](#pattern-17-hook-chaining-via-state)
- [Pattern 18: Secret Detection](#pattern-18-secret-detection)
- [Cross-Event Workflows](#cross-event-workflows)
- [Integration with External Systems](#integration-with-external-systems)
- [Testing Advanced Hooks](#testing-advanced-hooks)
- [Debugging Complex Hooks](#debugging-complex-hooks)
- [Best Practices & Common Pitfalls](#best-practices--common-pitfalls)
- [Production Deployment Checklist](#production-deployment-checklist)

---

## Pattern 1: Conditional Execution

**Scenario:** Hook should only run under certain conditions.

**Example:** Format only .js files, not everything.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^Write$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/conditional-format.sh",
            "timeout": 2000,
            "env": {
              "ALLOWED_EXTENSIONS": ".js,.jsx,.ts,.tsx",
              "FORMAT_JS": "true"
            }
          }
        ]
      }
    ]
  }
}
```

**Script (conditional-format.sh):**
```bash
#!/bin/bash

FILE_PATH="$1"
ALLOWED_EXTENSIONS="${ALLOWED_EXTENSIONS:-.js}"

# Check if file extension is in allowed list
if [[ ! "$FILE_PATH" =~ ($ALLOWED_EXTENSIONS)$ ]]; then
  exit 0  # Don't format, but don't fail
fi

# Format the file
prettier --write "$FILE_PATH" 2>/dev/null || true
exit 0
```

**Key concept:** Script decides whether to execute based on context, not just matcher.

---

## Pattern 2: Sequential Hooks with Fallback

**Scenario:** Try primary format, fall back to secondary if it fails.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-primary.sh",
            "timeout": 2000,
            "onError": "continue"
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-fallback.sh",
            "timeout": 2000,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

**Execution flow:**
1. Try primary formatter (prettier)
2. If fails, silently continue
3. Try fallback formatter (basic indentation)
4. If fails, warn user

---

## Pattern 3: Rate Limiting

**Scenario:** Hook runs too often; need to throttle.

**Script (rate-limited-format.sh):**
```bash
#!/bin/bash

LOCK_FILE="${TMPDIR:-/tmp}/format.lock"
LOCKOUT_DURATION=30  # Don't run more than once per 30 seconds

# Check if recent execution exists
if [ -f "$LOCK_FILE" ]; then
  LAST_RUN=$(cat "$LOCK_FILE")
  NOW=$(date +%s)
  ELAPSED=$((NOW - LAST_RUN))

  if [ "$ELAPSED" -lt "$LOCKOUT_DURATION" ]; then
    echo "Rate limited: last run $ELAPSED seconds ago" >&2
    exit 0  # Skip this run
  fi
fi

# Update lock file
date +%s > "$LOCK_FILE"

# Do the expensive operation
prettier --write . 2>/dev/null || true

exit 0
```

**Concept:** Track last execution time, skip if too recent.

---

## Pattern 4: Caching Results

**Scenario:** Hook result doesn't change often; cache to avoid re-execution.

**Script (cached-validate.sh):**
```bash
#!/bin/bash

FILE_PATH="$1"
CACHE_DIR="${CACHE_DIR:-$HOME/.cache/hook-cache}"
CACHE_FILE="$CACHE_DIR/$(echo "$FILE_PATH" | md5sum | cut -d' ' -f1).cache"

mkdir -p "$CACHE_DIR"

# Check cache
if [ -f "$CACHE_FILE" ]; then
  LAST_MODIFIED=$(stat -f%m "$FILE_PATH" 2>/dev/null || stat -c%Y "$FILE_PATH")
  CACHE_TIME=$(cat "$CACHE_FILE")

  if [ $((LAST_MODIFIED - CACHE_TIME)) -lt 0 ]; then
    # File hasn't changed since cache
    exit 0
  fi
fi

# Validate file
if npm run lint "$FILE_PATH" 2>/dev/null; then
  # Cache this success
  stat -f%m "$FILE_PATH" 2>/dev/null || stat -c%Y "$FILE_PATH" > "$CACHE_FILE"
  exit 0
else
  exit 1
fi
```

**Concept:** Store result with file modification time; reuse if file unchanged.

---

## Pattern 5: Multiple Tool Matchers with Different Actions

**Scenario:** Different formatters for different tool types.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^Write$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-write.sh"
          }
        ]
      }
    ]
  }
}
```

Repeat the same `{ "matcher": ..., "hooks": [...] }` entry once per tool inside the `PostToolUse` array — e.g. `"^Edit$"` calling `format-edit.sh`, `"^Bash$"` calling `audit-bash.sh`.

**Execution:** Each matcher is independent; only matching matchers execute.

---

## Pattern 6: Event Chaining (Upstream/Downstream)

**Scenario:** Hook on one event triggers behavior that affects another.

**Example:** Format after write, which triggers test hook.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^Write$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
            "timeout": 2000
          }
        ]
      },
      {
        "matcher": "^Bash$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/collect-test-metrics.sh",
            "timeout": 1000,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

**Flow:**
1. Write file → PostToolUse Write hook → Format runs
2. Bash test → PostToolUse Bash hook → Metrics collected

**Concept:** Separate hooks can create a pipeline effect.

---

## Pattern 7: Idempotent Updates

**Scenario:** Hook might run multiple times; must be safe to rerun.

**Script (idempotent-update.sh):**
```bash
#!/bin/bash

FILE_PATH="$1"
LOCK_FILE="${FILE_PATH}.lock"
MAX_WAIT=10

# Prevent concurrent updates
WAIT_TIME=0
while [ -f "$LOCK_FILE" ] && [ $WAIT_TIME -lt $MAX_WAIT ]; do
  sleep 0.5
  WAIT_TIME=$((WAIT_TIME + 1))
done

# Create lock
touch "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# Idempotent update: read, check, write
CURRENT=$(cat "$FILE_PATH")
NEW=$(computed_value)

if [ "$CURRENT" != "$NEW" ]; then
  echo "$NEW" > "$FILE_PATH.tmp"
  mv "$FILE_PATH.tmp" "$FILE_PATH"  # Atomic move
fi

exit 0
```

**Key principles:**
- Locking prevents concurrent modification
- Atomic file operations (temp + move)
- Check before modifying
- Same result on repeated runs

---

## Pattern 8: Validation Before Blocking

**Scenario:** Prevent dangerous operations with validation.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate-before-write.sh",
            "timeout": 1000,
            "onError": "fail"
          }
        ]
      }
    ]
  }
}
```

**Script (validate-before-write.sh):**
```bash
#!/bin/bash

FILE_PATH="$1"

# Dangerous paths check
DANGEROUS_PATTERNS=("^/etc" "^/sys" "^/dev" "^/proc" "^/root" "^/var/log")

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" =~ $pattern ]]; then
    echo "Dangerous path: $FILE_PATH" >&2
    exit 2  # Exit 2: blocking error, shows stderr to Claude
  fi
done

# Size check
if [ -f "$FILE_PATH" ]; then
  SIZE=$(stat -f%z "$FILE_PATH" 2>/dev/null || stat -c%s "$FILE_PATH")
  if [ "$SIZE" -gt 104857600 ]; then  # 100MB
    echo "File too large: $SIZE bytes" >&2
    exit 2
  fi
fi

exit 0  # All checks passed
```

**Concept:** `onError: "fail"` means validation failure blocks tool execution. Use `exit 2` to communicate the reason to Claude.

---

## Pattern 9: Async Hook for Slow Operations

**Scenario:** Operations that take time and shouldn't block Claude Code execution.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/log-and-analyze.sh",
            "timeout": 5000,
            "async": true,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

**Characteristics:**
- `async: true` ensures hook runs in background without blocking Claude
- `onError: "warn"` is appropriate (background failures don't affect execution)
- Timeout still enforced but doesn't slow Claude Code
- Perfect for: logging, metrics, webhooks, notifications, file I/O
- Cannot return decisions — use only for side effects

---

## Pattern 10: Multi-Stage Verification

**Scenario:** Complex verification with multiple checks that must all pass.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "deploy",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/stage1-syntax-check.sh",
            "timeout": 3000,
            "onError": "fail"
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/stage2-tests.sh",
            "timeout": 15000,
            "onError": "fail"
          },
          {
            "type": "prompt",
            "prompt": "All tests passed. Approve deployment? Answer YES or NO.",
            "timeout": 10000,
            "onError": "fail"
          }
        ]
      }
    ]
  }
}
```

**Execution order:**
1. Stage 1: Syntax check (fail if code has errors)
2. Stage 2: Tests (fail if tests fail)
3. Stage 3: Human approval (fail if user says no)

**Any failure stops the chain.**

---

## Pattern 11: Conditional Blocking Based on Context

**Scenario:** Block operation only under certain conditions.

**Script (smart-blocking.sh):**
```bash
#!/bin/bash

# Get environment context
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
TIME=$(date +%H)

# Block deployments after 5 PM
if [[ "$1" == "deploy" ]] && [ "$TIME" -ge 17 ]; then
  echo "Deployment blocked: after business hours" >&2
  exit 2
fi

# Block commits to main without review
if [[ "$BRANCH" == "main" ]]; then
  echo "Commits to main must be via pull request" >&2
  exit 2
fi

exit 0
```

**Concept:** Script implements sophisticated decision logic beyond simple matching.

---

## Pattern 12: Logging & Monitoring Integration

**Scenario:** Track hook execution for debugging and monitoring asynchronously.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-with-logging.sh",
            "timeout": 2000,
            "async": true,
            "onError": "warn",
            "env": {
              "LOG_FILE": "${CLAUDE_PLUGIN_ROOT}/logs/hook-format.log",
              "METRICS_FILE": "${CLAUDE_PLUGIN_ROOT}/metrics/hook-metrics.json"
            }
          }
        ]
      }
    ]
  }
}
```

**Note:** `async: true` allows logging/metrics to run in background without slowing Claude Code execution.

**Script (format-with-logging.sh):**
```bash
#!/bin/bash

LOG_FILE="${LOG_FILE:-/dev/null}"
METRICS_FILE="${METRICS_FILE:-/dev/null}"

START_TIME=$(date +%s%N)

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Formatting: $*" >> "$LOG_FILE"

# Do formatting
prettier --write "$@" 2>> "$LOG_FILE"
RESULT=$?

END_TIME=$(date +%s%N)
DURATION=$(((END_TIME - START_TIME) / 1000000))  # Convert to ms

if [ "$RESULT" -eq 0 ]; then
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] SUCCESS ($DURATION ms)" >> "$LOG_FILE"
else
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] FAILED ($DURATION ms)" >> "$LOG_FILE"
fi

# Log metrics
echo "{ \"timestamp\": $(date +%s), \"duration_ms\": $DURATION, \"success\": $RESULT }" >> "$METRICS_FILE"

exit $RESULT
```

---

## Pattern 13: Environment-Based Hook Behavior

**Scenario:** Different behavior in dev vs production.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
            "timeout": 2000,
            "env": {
              "ENVIRONMENT": "${CLAUDE_ENVIRONMENT:-dev}",
              "STRICT_MODE": "${STRICT_MODE:-false}"
            },
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

**Script (format.sh):**
```bash
#!/bin/bash

ENVIRONMENT="${ENVIRONMENT:-dev}"
STRICT_MODE="${STRICT_MODE:-false}"

if [ "$ENVIRONMENT" = "production" ]; then
  # Production: strict formatting
  prettier --write --check "$@" || exit 2
else
  # Dev: lenient formatting
  prettier --write "$@" 2>/dev/null || true
fi

exit 0
```

---

## Pattern 14: Retry Logic

**Scenario:** Transient failures; retry before failing.

**Script (with-retry.sh):**
```bash
#!/bin/bash

COMMAND=("$@")
MAX_RETRIES=3
RETRY_DELAY=1

for attempt in $(seq 1 "$MAX_RETRIES"); do
  echo "Attempt $attempt/$MAX_RETRIES: ${COMMAND[*]}" >&2

  if "${COMMAND[@]}"; then
    echo "Success on attempt $attempt" >&2
    exit 0
  fi

  if [ "$attempt" -lt "$MAX_RETRIES" ]; then
    echo "Failed, retrying in ${RETRY_DELAY}s..." >&2
    sleep "$RETRY_DELAY"
  fi
done

echo "Failed after $MAX_RETRIES attempts" >&2
exit 1
```

**Usage:**
```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/with-retry.sh npm run build"
}
```

---

## Pattern 15: Complex Decision Agent

**Scenario:** Sophisticated validation logic that benefits from reasoning.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "refactor|migrate|upgrade",
        "hooks": [
          {
            "type": "agent",
            "agent": "refactor-advisor",
            "timeout": 30000,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

**Agent instructions (in plugin):**
```
You are a refactoring advisor. When Claude is about to refactor code:

1. Analyze the scope of the refactoring
2. Check if there are existing tests (coverage?)
3. Verify no critical dependencies
4. Recommend safety steps (backup, tests first)
5. Return APPROVE or WARN_RISKY or DENY_UNSAFE

Use available tools to check files and dependencies.
```

---

## Pattern 16: Multi-Stage Command + Prompt Validation

**Scenario:** Fast deterministic pre-screening before an expensive prompt hook.

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/quick-check.sh",
          "timeout": 5000
        },
        {
          "type": "prompt",
          "prompt": "Deep analysis of bash command: $ARGUMENTS",
          "timeout": 15000
        }
      ]
    }
  ]
}
```

**Script (quick-check.sh):**
```bash
#!/bin/bash
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command')

# Immediately approve safe commands without invoking the LLM
if [[ "$command" =~ ^(ls|pwd|echo|date|whoami)$ ]]; then
  exit 0
fi

# Pass everything else to the prompt hook for intelligent analysis
exit 0
```

**Why this works:** The command hook quickly approves obviously safe commands at near-zero cost. The prompt hook only processes edge cases requiring judgment, saving tokens on routine operations.

---

## Pattern 17: Hook Chaining via State

**Scenario:** Share analysis results between sequential hooks using temporary state files.

```bash
# Hook 1 (PreToolUse): Analyze and save state
#!/bin/bash
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command')

# Calculate risk level
if echo "$command" | grep -qE "rm|delete|drop|truncate"; then
  risk_level="high"
elif echo "$command" | grep -qE "write|insert|update"; then
  risk_level="medium"
else
  risk_level="low"
fi

echo "$risk_level" > "/tmp/hook-state-$$"
exit 0
```

```bash
# Hook 2 (PostToolUse): Use saved state for follow-up action
#!/bin/bash
risk_level=$(cat "/tmp/hook-state-$$" 2>/dev/null || echo "unknown")

if [ "$risk_level" = "high" ]; then
  echo "High-risk operation completed — triggering audit log" >&2
  bash "${CLAUDE_PLUGIN_ROOT}/scripts/audit-log.sh"
fi

rm -f "/tmp/hook-state-$$"
exit 0
```

**Important:** State sharing only works reliably for sequential events on the same session (e.g., PreToolUse → PostToolUse). Hooks within the same event run in parallel and cannot share state this way.

---

## Pattern 18: Secret Detection

**Scenario:** Block writes that contain hardcoded credentials or API keys.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/detect-secrets.sh",
            "timeout": 2000,
            "onError": "fail"
          }
        ]
      }
    ]
  }
}
```

**Script (detect-secrets.sh):**
```bash
#!/bin/bash
input=$(cat)
content=$(echo "$input" | jq -r '.tool_input.content // empty')

if [ -z "$content" ]; then
  exit 0  # No content to check
fi

# Check for common secret patterns
if echo "$content" | grep -qE "(api[_-]?key|password|secret|token).{0,20}['\"]?[A-Za-z0-9]{20,}"; then
  echo "Potential secret detected in content — remove credentials before writing" >&2
  exit 2
fi

exit 0
```

---

## Cross-Event Workflows

Coordinate hooks across multiple events to implement multi-step policies:

**SessionStart — Initialize tracking:**
```bash
#!/bin/bash
# Initialize per-session counters
echo "0" > "/tmp/test-count-$$"
echo "0" > "/tmp/write-count-$$"
```

**PostToolUse — Accumulate metrics:**
```bash
#!/bin/bash
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

if [ "$tool_name" = "Write" ] || [ "$tool_name" = "Edit" ]; then
  count=$(cat "/tmp/write-count-$$" 2>/dev/null || echo "0")
  echo $((count + 1)) > "/tmp/write-count-$$"
fi

if [ "$tool_name" = "Bash" ]; then
  result=$(echo "$input" | jq -r '.tool_result // empty')
  if echo "$result" | grep -q "test"; then
    count=$(cat "/tmp/test-count-$$" 2>/dev/null || echo "0")
    echo $((count + 1)) > "/tmp/test-count-$$"
  fi
fi
```

**Stop — Verify policy before allowing stop:**
```bash
#!/bin/bash
input=$(cat)

# Guard against infinite loop
if [ "$(echo "$input" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0
fi

write_count=$(cat "/tmp/write-count-$$" 2>/dev/null || echo "0")
test_count=$(cat "/tmp/test-count-$$" 2>/dev/null || echo "0")

if [ "$write_count" -gt 0 ] && [ "$test_count" -eq 0 ]; then
  echo "Code was written but no tests were run — run tests before stopping" >&2
  exit 2
fi

# Clean up session state
rm -f "/tmp/test-count-$$" "/tmp/write-count-$$"
```

**Stop hooks can also read the transcript:**
```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Review the full transcript at $TRANSCRIPT_PATH. Check: 1) Were tests run after code changes? 2) Did the build succeed? 3) Were all user questions answered? Return 'approve' only if complete.",
          "timeout": 30000
        }
      ]
    }
  ]
}
```

---

## Integration with External Systems

### Slack Notifications

```bash
#!/bin/bash
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

# Send notification to Slack (async — don't block execution)
curl -s -X POST "$SLACK_WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"Claude used ${tool_name} in session ${SESSION_ID:-unknown}\"}" \
  --max-time 3 \
  2>/dev/null || true

exit 0
```

Configure as `async: true` with `onError: "warn"` — notification failures should never block Claude.

### Database Logging

```bash
#!/bin/bash
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')
timestamp=$(date -Iseconds)

# Log to PostgreSQL
psql "$DATABASE_URL" -c \
  "INSERT INTO hook_logs (timestamp, user_id, tool_name, session_id) VALUES ('$timestamp', '$USER', '$tool_name', '${SESSION_ID:-}')" \
  2>/dev/null || true

exit 0
```

### Metrics Collection (StatsD)

```bash
#!/bin/bash
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

# Send counter to StatsD
echo "hook.pretooluse.${tool_name}:1|c" | nc -u -w1 statsd.local 8125 2>/dev/null || true

exit 0
```

---

## Testing Advanced Hooks

### Unit Testing Hook Scripts

Test scripts directly by feeding synthetic event JSON to stdin:

```bash
#!/bin/bash
# test-hook.sh

# Test 1: Approve safe command
result=$(echo '{"tool_input": {"command": "ls"}}' | bash validate-bash.sh)
exit_code=$?
if [ "$exit_code" -eq 0 ]; then
  echo "✓ Test 1 passed: safe command approved"
else
  echo "✗ Test 1 failed: expected exit 0, got $exit_code"
fi

# Test 2: Block dangerous command (must exit 2)
echo '{"tool_input": {"command": "rm -rf /"}}' | bash validate-bash.sh
if [ $? -eq 2 ]; then
  echo "✓ Test 2 passed: dangerous command blocked"
else
  echo "✗ Test 2 failed: expected exit 2"
fi

# Test 3: Secret detection blocks writes with credentials
echo '{"tool_input": {"content": "api_key=\"AKIAIOSFODNN7EXAMPLE\""}}' | bash detect-secrets.sh
if [ $? -eq 2 ]; then
  echo "✓ Test 3 passed: secret detected and blocked"
else
  echo "✗ Test 3 failed: secret was not detected"
fi
```

### Integration Testing

Exercise the full hook environment including environment variables:

```bash
#!/bin/bash
# integration-test.sh

# Set up test environment
export CLAUDE_PROJECT_DIR="/tmp/test-project-$$"
export CLAUDE_PLUGIN_ROOT="$(pwd)"
mkdir -p "$CLAUDE_PROJECT_DIR"

# Test SessionStart hook
echo '{}' | bash hooks/session-start.sh
if [ -f "/tmp/test-count-$$" ]; then
  echo "✓ SessionStart hook initialized counters"
else
  echo "✗ SessionStart hook did not initialize counters"
fi

# Simulate PostToolUse Write event
echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.js"}}' | bash hooks/post-tool-use.sh
write_count=$(cat "/tmp/write-count-$$" 2>/dev/null || echo "0")
if [ "$write_count" -eq 1 ]; then
  echo "✓ PostToolUse tracked write count"
else
  echo "✗ PostToolUse did not track write count (got $write_count)"
fi

# Clean up
rm -rf "$CLAUDE_PROJECT_DIR"
rm -f "/tmp/test-count-$$" "/tmp/write-count-$$"
```

---

## Debugging Complex Hooks

### Strategy 1: Add Debug Logging

```bash
#!/bin/bash

DEBUG="${DEBUG:-false}"

debug() {
  if [ "$DEBUG" = "true" ]; then
    echo "[DEBUG] $*" >&2
  fi
}

debug "Starting with args: $*"
debug "Environment: $(env | grep CLAUDE)"

# ... rest of script
```

Enable with:
```json
{
  "env": {
    "DEBUG": "true",
    "LOG_FILE": "/tmp/hook-debug.log"
  }
}
```

### Strategy 2: Test Script Standalone

```bash
# Before deploying hook, test script directly
export DEBUG=true
export LOG_FILE=/tmp/test.log

${CLAUDE_PLUGIN_ROOT}/scripts/my-script.sh test.js

# Check logs
cat /tmp/test.log
```

### Strategy 3: Measure Performance

```bash
#!/bin/bash

SCRIPT="${CLAUDE_PLUGIN_ROOT}/scripts/expensive-operation.sh"

# Time the operation
time $SCRIPT "$@"

# Check if within acceptable range (<1s for sync hooks, <5s for agent hooks)
```

---


## Production Deployment Checklist

See `validation-guide.md`'s "Production & Team Hooks Checklist" for the full canonical checklist (idempotency, atomicity, exit codes, shellcheck, rollback, monitoring, and documentation are all covered there).
