# Hook Patterns and Templates

Copy-paste starting points and proven implementation patterns for Claude Code hooks.

**R18 exception (recorded):** several templates/patterns below intentionally exceed the rulebook's 30-line code-block threshold — each is a complete, copy-paste-ready hook configuration or script; splitting one would break its copy-paste usability. Matches this plugin's established R18 exception pattern (see `command-development/references/marketplace-considerations.md`).

## Table of Contents

**Templates (copy-paste starting points):**
- [Basic Command Hook](#basic-command-hook)
- [Command Hook with Error Handling](#command-hook-with-error-handling)
- [Prompt Hook (UserPromptSubmit)](#prompt-hook-userpromptsubmit)
- [Prompt Hook (Stop/SubagentStop)](#prompt-hook-stopsubagentsop)
- [Prompt Hook (PreToolUse / PermissionRequest)](#prompt-hook-pretooluse--permissionrequest)
- [Multiple Hooks on Same Event](#multiple-hooks-on-same-event)
- [Multiple Matchers on Same Event](#multiple-matchers-on-same-event)
- [Format on Write Hook](#format-on-write-hook)
- [Validate Before Commit Hook](#validate-before-commit-hook)
- [Async Logging and Notifications Hook](#async-logging-and-notifications-hook)
- [Cleanup on Session End Hook](#cleanup-on-session-end-hook)

**Common Patterns (use-case scenarios):**
- [Pattern 1: Security Validation](#pattern-1-security-validation)
- [Pattern 2: Test Enforcement](#pattern-2-test-enforcement)
- [Pattern 3: Context Loading](#pattern-3-context-loading)
- [Pattern 4: Notification Logging](#pattern-4-notification-logging)
- [Pattern 5: MCP Tool Monitoring](#pattern-5-mcp-tool-monitoring)
- [Pattern 6: Build Verification](#pattern-6-build-verification)
- [Pattern 7: Permission Confirmation](#pattern-7-permission-confirmation)
- [Pattern 8: Code Quality Checks](#pattern-8-code-quality-checks)
- [Pattern 9: Temporarily Active Hooks](#pattern-9-temporarily-active-hooks)
- [Pattern 10: Configuration-Driven Hooks](#pattern-10-configuration-driven-hooks)
- [Pattern 11: Cross-Platform Python Hook](#pattern-11-cross-platform-python-hook)

**Reference:**
- [Common Matcher Patterns](#common-matcher-patterns)
- [Environment Variables in Hooks](#environment-variables-in-hooks)
- [Hook File Organization](#hook-file-organization)
- [Testing Hooks Locally](#testing-hooks-locally)
- [Shellcheck: Validating Hook Scripts](#shellcheck-validating-hook-scripts)
- [Migration: From Script-Based to Hook-Based](#migration-from-script-based-to-hook-based)
- [Production Deployment Checklist](#production-deployment-checklist)

---

## Basic Command Hook

**Use case:** Run a script after a tool executes. Example: format code after writing a file.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/my-script.sh",
            "timeout": 2000
          }
        ]
      }
    ]
  }
}
```

**Customization:**
- Replace `PostToolUse` with your event (PreToolUse, UserPromptSubmit, SessionEnd, etc.)
- Replace `^(Write|Edit)$` with tools/patterns to match
- Replace `my-script.sh` with your script path
- Adjust `timeout` based on how long your script takes

---

## Command Hook with Error Handling

**Use case:** Run script with explicit error handling and logging.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
            "timeout": 3000,
            "onError": "warn",
            "env": {
              "PLUGIN_ROOT": "${CLAUDE_PLUGIN_ROOT}",
              "LOG_LEVEL": "debug"
            }
          }
        ]
      }
    ]
  }
}
```

**Error behavior options:**
- `"warn"` — Log warning, continue (safe for most cases)
- `"fail"` — Fail hook but don't crash plugin
- `"continue"` — Silently continue (only if errors are expected)

**CRITICAL: Exit Code Strategy**

```bash
#!/bin/bash

# Case 1: Claude needs to see this error (blocking validation)
if some_critical_check_fails; then
  echo "Error message for Claude" >&2
  exit 2  # Shows stderr to Claude — he can understand and fix it
fi

# Case 2: Optional check, Claude doesn't need to know
if some_optional_check_fails; then
  echo "Debug info" >&2
  exit 1  # Hidden from Claude (verbose mode only)
fi

# Case 3: Success
exit 0
```

**Exit 2 is the ONLY way to communicate hook failures to Claude.**

---

## Prompt Hook (UserPromptSubmit)

**Use case:** LLM-based validation on user input. Example: block prompts with sensitive data patterns.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Does this prompt contain code or a legitimate technical question? ${ARGUMENTS}\n\nRespond with: {\"ok\": true} or {\"ok\": false, \"reason\": \"why\"}",
            "timeout": 10000
          }
        ]
      }
    ]
  }
}
```

If LLM responds with `ok: false`, prompt is blocked with reason shown to user.

---

## Prompt Hook (Stop/SubagentStop)

**Use case:** Intelligent decision-making on stop. Example: prevent stop if work incomplete.

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Evaluate if work can stop: ${ARGUMENTS}\n\nRespond with: {\"ok\": true, \"reason\": \"why stop\"} or {\"ok\": false, \"reason\": \"why continue\"}",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

If `ok: false`, stop is prevented and reason shown to Claude. Always add a `stop_hook_active` guard in command hooks to prevent infinite loops (see SKILL.md).

---

## Prompt Hook (PreToolUse / PermissionRequest)

**Use case:** Context-aware permission decisions. Example: allow risky commands only in safe contexts.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^Bash$",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Is this bash command safe? Command: ${ARGUMENTS}\n\nRespond: {\"ok\": true} or {\"ok\": false, \"reason\": \"why not\"}",
            "timeout": 15000
          }
        ]
      }
    ]
  }
}
```

**Note on prompt hooks:**
- Cost tokens (API calls ~2–10s each)
- Use for complex decisions needing context understanding
- Don't use for simple deterministic validation (use command hooks instead)
- Timeouts longer than command hooks (10–30s typical)

---

## Multiple Hooks on Same Event

**Use case:** Run multiple scripts/verifications after tool use. Example: format, lint, then test.

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
            "onError": "warn"
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/lint.sh",
            "timeout": 3000,
            "onError": "warn"
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/test.sh",
            "timeout": 10000,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

**Execution order:** Top to bottom (format → lint → test)

**Important:** Each hook can fail independently. Set `onError: "warn"` so failures don't cascade.

---

## Multiple Matchers on Same Event

**Use case:** Run different hooks for different conditions. Example: different formatters for different file types.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "\\.js$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/prettier.sh",
            "timeout": 2000
          }
        ]
      },
      {
        "matcher": "\\.py$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/black.sh",
            "timeout": 2000
          }
        ]
      }
    ]
  }
}
```

**Logic:** If matcher 1 matches, execute hooks for matcher 1. If matcher 2 matches, execute hooks for matcher 2. Both can execute if both match.

---

## Format on Write Hook

**Complete example:** Format code after file is written.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-code.sh",
            "timeout": 2000,
            "onError": "warn"
          }
        ]
      }
    ]
  }
}
```

**Script (format-code.sh):**
```bash
#!/bin/bash
set -e

input=$(cat)
FILE_PATH=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if [[ "$FILE_PATH" == *.js ]] || [[ "$FILE_PATH" == *.jsx ]]; then
  prettier --write "$FILE_PATH" 2>/dev/null || echo "prettier failed for $FILE_PATH" >&2
elif [[ "$FILE_PATH" == *.py ]]; then
  black "$FILE_PATH" 2>/dev/null || echo "black failed for $FILE_PATH" >&2
fi

exit 0
```

---

## Validate Before Commit Hook

**Complete example:** Validation hook that prevents commits with issues.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "commit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/pre-commit.sh",
            "timeout": 5000,
            "onError": "fail"
          }
        ]
      }
    ]
  }
}
```

**Script (pre-commit.sh):**
```bash
#!/bin/bash

# Run linting
if ! npm run lint --silent 2>/dev/null; then
  echo "Linting failed. Fix errors before committing." >&2
  exit 2  # Exit 2: blocking error, shows stderr to Claude
fi

# Run tests
if ! npm test --silent 2>/dev/null; then
  echo "Tests failed. Fix failures before committing." >&2
  exit 2  # Exit 2: blocking error, shows stderr to Claude
fi

exit 0
```

**Exit code behavior:**
- `exit 0` = success (no error shown)
- `exit 2` = blocking error (stderr shown to Claude, he can understand and fix)
- `exit 1` = non-blocking error (stderr only in verbose mode, Claude never sees it)

---

## Async Logging and Notifications Hook

**Complete example:** Log tool usage to external service without blocking Claude Code.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit|Bash)$",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/log-to-service.sh",
            "timeout": 5000,
            "onError": "warn",
            "async": true
          }
        ]
      }
    ]
  }
}
```

**Script (log-to-service.sh):**
```bash
#!/bin/bash

input=$(cat)
TOOL_NAME=$(echo "$input" | jq -r '.tool_name // "unknown"')
FILE_PATH=$(echo "$input" | jq -r '.tool_input.file_path // empty')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

LOG_ENTRY=$(cat <<EOF
{
  "timestamp": "$TIMESTAMP",
  "user": "${USER:-unknown}",
  "tool": "$TOOL_NAME",
  "file": "$FILE_PATH"
}
EOF
)

# Send to logging service (doesn't block if it fails)
curl -s -X POST "https://logs.example.com/api/events" \
  -H "Content-Type: application/json" \
  -d "$LOG_ENTRY" \
  --max-time 4 \
  --connect-timeout 2 || true

# Or append to local log (faster)
echo "$LOG_ENTRY" >> "${CLAUDE_PLUGIN_ROOT}/logs/tool-usage.jsonl"

exit 0
```

**Notes:**
- `async: true` means hook runs in background; Claude continues immediately
- `onError: "warn"` is appropriate (logging failures shouldn't block execution)
- Use `|| true` to prevent failures from blocking

---

## Cleanup on Session End Hook

**Complete example:** Run cleanup tasks when Claude Code session ends.

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup.sh",
            "timeout": 3000,
            "onError": "warn",
            "async": true
          }
        ]
      }
    ]
  }
}
```

**Script (cleanup.sh):**
```bash
#!/bin/bash

# Remove temporary files
rm -f "${CLAUDE_PLUGIN_ROOT}/temp/"*.tmp

# Archive logs
if [ -f "${CLAUDE_PLUGIN_ROOT}/logs/session.log" ]; then
  gzip "${CLAUDE_PLUGIN_ROOT}/logs/session.log"
fi

exit 0
```

---

## Pattern 1: Security Validation

Block dangerous file writes using prompt-based hooks:

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "File path: $TOOL_INPUT.file_path. Verify: 1) Not in /etc or system directories 2) Not .env or credentials 3) Path doesn't contain '..' traversal. Return 'approve' or 'deny'."
        }
      ]
    }
  ]
}
```

**Use for:** Preventing writes to sensitive files or system directories.

---

## Pattern 2: Test Enforcement

Ensure tests run before stopping:

```json
{
  "Stop": [
    {
      "matcher": ".*",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Review transcript. If code was modified (Write/Edit tools used), verify tests were executed. If no tests were run, block with reason 'Tests must be run after code changes'."
        }
      ]
    }
  ]
}
```

**Use for:** Enforcing quality standards and preventing incomplete work.

---

## Pattern 3: Context Loading

Load project-specific context at session start:

```json
{
  "SessionStart": [
    {
      "matcher": ".*",
      "hooks": [
        {
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-context.sh"
        }
      ]
    }
  ]
}
```

**Example script (load-context.sh):**
```bash
#!/bin/bash
cd "$CLAUDE_PROJECT_DIR" || exit 1

# Detect project type and set env vars for the session
if [ -f "package.json" ]; then
  echo "export PROJECT_TYPE=nodejs" >> "$CLAUDE_ENV_FILE"
  echo "export PACKAGE_MANAGER=$(command -v pnpm >/dev/null && echo pnpm || echo npm)" >> "$CLAUDE_ENV_FILE"
elif [ -f "Cargo.toml" ]; then
  echo "export PROJECT_TYPE=rust" >> "$CLAUDE_ENV_FILE"
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  echo "export PROJECT_TYPE=python" >> "$CLAUDE_ENV_FILE"
fi
```

**Use for:** Automatically detecting and configuring project-specific settings. Env vars written to `$CLAUDE_ENV_FILE` persist for the session.

---

## Pattern 4: Notification Logging

Log all notifications for audit or analysis:

```json
{
  "Notification": [
    {
      "matcher": ".*",
      "hooks": [
        {
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/log-notification.sh",
          "async": true
        }
      ]
    }
  ]
}
```

**Use for:** Tracking user notifications or integration with external logging systems.

---

## Pattern 5: MCP Tool Monitoring

Monitor and validate MCP tool usage:

```json
{
  "PreToolUse": [
    {
      "matcher": "mcp__.*__delete.*",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Deletion operation detected. Verify: Is this deletion intentional? Can it be undone? Are there backups? Return 'approve' only if safe."
        }
      ]
    }
  ]
}
```

**Use for:** Protecting against destructive MCP operations.

---

## Pattern 6: Build Verification

Ensure project builds after code changes:

```json
{
  "Stop": [
    {
      "matcher": ".*",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Check if code was modified. If Write/Edit tools were used, verify the project was built (npm run build, cargo build, etc). If not built, block and request build."
        }
      ]
    }
  ]
}
```

**Use for:** Catching build errors before committing or stopping work.

---

## Pattern 7: Permission Confirmation

Ask user before dangerous operations:

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Command: $TOOL_INPUT.command. If command contains 'rm', 'delete', 'drop', or other destructive operations, return 'ask' to confirm with user. Otherwise 'approve'."
        }
      ]
    }
  ]
}
```

**Use for:** User confirmation on potentially destructive commands.

---

## Pattern 8: Code Quality Checks

Run linters or formatters on file edits:

```json
{
  "PostToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-quality.sh"
        }
      ]
    }
  ]
}
```

**Example script (check-quality.sh):**
```bash
#!/bin/bash
input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

[ -z "$file_path" ] && exit 0

# Run linter if applicable
if [[ "$file_path" == *.js ]] || [[ "$file_path" == *.ts ]]; then
  npx eslint "$file_path" 2>&1 || true
fi
```

**Use for:** Automatic code quality enforcement.

---

## Pattern 9: Temporarily Active Hooks

Create hooks that only run when explicitly enabled via a flag file:

```bash
#!/bin/bash
# Hook only active when flag file exists
FLAG_FILE="$CLAUDE_PROJECT_DIR/.enable-security-scan"

if [ ! -f "$FLAG_FILE" ]; then
  exit 0  # Quick exit when disabled
fi

# Flag present — run validation
input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Run security scan
security-scanner "$file_path"
```

**Activation:**
```bash
# Enable the hook
touch .enable-security-scan

# Disable the hook
rm .enable-security-scan
```

**Use for:**
- Temporary debugging hooks
- Performance-intensive checks that are opt-in
- Project-specific validation
- Feature flags for development

**Note:** Claude Code must be restarted after creating/removing flag files.

---

## Pattern 10: Configuration-Driven Hooks

Use a JSON config file to control hook behavior per project:

```bash
#!/bin/bash
CONFIG_FILE="$CLAUDE_PROJECT_DIR/.claude/my-plugin.local.json"

# Read configuration (with defaults)
if [ -f "$CONFIG_FILE" ]; then
  strict_mode=$(jq -r '.strictMode // false' "$CONFIG_FILE")
  max_file_size=$(jq -r '.maxFileSize // 1000000' "$CONFIG_FILE")
else
  strict_mode=false
  max_file_size=1000000
fi

# Skip if not in strict mode
if [ "$strict_mode" != "true" ]; then
  exit 0
fi

# Apply configured limits
input=$(cat)
content=$(echo "$input" | jq -r '.tool_input.content // empty')
file_size=${#content}

if [ "$file_size" -gt "$max_file_size" ]; then
  echo "File exceeds configured size limit (${file_size} > ${max_file_size} bytes)" >&2
  exit 2
fi
```

**Configuration file (.claude/my-plugin.local.json):**
```json
{
  "strictMode": true,
  "maxFileSize": 500000,
  "allowedPaths": ["/tmp", "/home/user/projects"]
}
```

**Use for:**
- User-configurable hook behavior
- Per-project settings
- Team-specific rules

---

## Pattern 11: Cross-Platform Python Hook

**Use case:** A validation hook that must run identically on macOS, Linux, and Windows.

Prefer Python over bash for cross-platform hook scripts. Use `pathlib.Path` for every file path — never hardcode `/tmp/` or OS-specific separators — and never call `subprocess` with `shell=True` and a string command.

```python
#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

data = json.load(sys.stdin)
file_path = Path(data["tool_input"]["file_path"])  # pathlib, not string paths

# List args, no shell=True — safe and portable across OSes
result = subprocess.run(["eslint", str(file_path)], capture_output=True, text=True, check=False)

if result.returncode != 0:
    print(result.stdout[:2000], file=sys.stderr)
    sys.exit(2)
sys.exit(0)
```

**Portable runner fallback (optional):** since a plain `python` binary may not exist on every system, register the hook command with a three-way fallback so it works whether `uv`, `python3`, or only `python` is on `PATH`:

```bash
command -v uv >/dev/null 2>&1 && exec uv run "$0" "$@"
command -v python3 >/dev/null 2>&1 && exec python3 "$0" "$@"
exec python "$0" "$@"
```

---

## Common Matcher Patterns

| Pattern | Matches | Use Case |
|---------|---------|----------|
| `^Write$` | Exactly "Write" tool | Format after write |
| `^(Write\|Edit)$` | Write OR Edit | Edit files |
| `^(Read\|Glob\|Grep)$` | Any file read | Audit reads |
| `\.js$` | Files ending in .js | JS-specific action |
| `\.py$` | Files ending in .py | Python-specific action |
| `commit\|push` | Text contains commit or push | Version control |
| `test\|spec` | Text contains test or spec | Test-related |
| `mcp__.*__delete` | Any MCP delete tool | Protect MCP operations |
| `.*` | Matches everything | Run always (use sparingly) |

**Examples:**
```json
{ "matcher": "^(Write|Edit)$" }   // Tool names: exact match
{ "matcher": "\\.js$" }            // File pattern: .js files
{ "matcher": "commit|push" }       // Text pattern: commit or push
```

---

## Environment Variables in Hooks

**Available to all command hooks:**

```json
{
  "type": "command",
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh",
  "env": {
    "PLUGIN_ROOT": "${CLAUDE_PLUGIN_ROOT}",
    "DEBUG": "true",
    "CONFIG_PATH": "${CLAUDE_PLUGIN_ROOT}/config.json"
  }
}
```

| Variable | Description |
|----------|-------------|
| `${CLAUDE_PLUGIN_ROOT}` | Automatically resolved to plugin root path |
| `$CLAUDE_PROJECT_DIR` | Current project directory |
| `$CLAUDE_ENV_FILE` | SessionStart only — append `export VAR=val` to persist env vars |

Custom variables are passed exactly as specified in the `env` object.

---

## Hook File Organization

**Standard structure in plugin.json:**

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "pattern", "hooks": [...] }
    ],
    "PostToolUse": [
      { "matcher": "pattern", "hooks": [...] }
    ],
    "SessionEnd": [
      { "matcher": ".*", "hooks": [...] }
    ]
  }
}
```

**Alternative: Separate hooks.json file**

If hooks are complex, create `hooks/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [...],
    "UserPromptSubmit": [...],
    "SessionEnd": [...]
  }
}
```

Then reference in `plugin.json`:
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "hooks": "./hooks/hooks.json"
}
```

---

## Testing Hooks Locally

**Before deploying, test locally:**

```bash
# 1. Create test hook config
cat > test-hook.json <<'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^Write$",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
          "timeout": 2000
        }]
      }
    ]
  }
}
EOF

# 2. Validate syntax
jq empty test-hook.json && echo "Valid JSON"

# 3. Test script standalone with sample input
echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.js"}}' \
  | bash "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
echo "Exit: $?"

# 4. Install plugin with hooks
claude plugin validate .
claude plugin install .
```

---

## Shellcheck: Validating Hook Scripts

All command hook scripts must pass `shellcheck` before deployment.

**Install shellcheck:**
```bash
brew install shellcheck          # macOS
apt install shellcheck           # Debian/Ubuntu
yum install shellcheck           # CentOS/RHEL
```

**Validate scripts:**
```bash
shellcheck scripts/format.sh               # Single script
shellcheck scripts/*.sh                    # All scripts in directory
shellcheck -S warning scripts/format.sh   # Show only warnings
```

**Common issues shellcheck catches:**

| Issue | Example | Fix |
|-------|---------|-----|
| Unquoted variables | `[ $SIZE -gt 100 ]` | `[ "$SIZE" -gt 100 ]` |
| Useless echo | `echo $(date +%s)` | `date +%s` |
| Word splitting | `for file in $FILES` | Quote the variable or use an array |
| Trap expansion | `trap "rm $file" EXIT` | `trap 'rm "$file"' EXIT` |
| Array in string | `ARGS="$@"` | `ARGS=("$@")` |

---

## Migration: From Script-Based to Hook-Based

**Before (manual):**
```bash
# Write file
claude write myfile.js
# Then manually: prettier myfile.js
```

**After (hook-based):**
```bash
# Write file — hook automatically runs: prettier myfile.js
claude write myfile.js
```

**Setup:**
1. Create hook config with matcher for Write tool
2. Point hook to formatting script
3. Install plugin with hook
4. No more manual formatting needed

---

## Production Deployment Checklist

See `validation-guide.md`'s "Production & Team Hooks Checklist" for the full canonical checklist. Two things specific to the format-on-write pattern shown throughout this file: timeout should be reasonable (<5s for sync operations), and script paths should use `${CLAUDE_PLUGIN_ROOT}` rather than a hardcoded path.
