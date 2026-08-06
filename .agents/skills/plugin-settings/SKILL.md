---
name: plugin-settings
description: >-
  Implements per-project plugin configuration using .Codex/plugin-name.local.md
  files — YAML frontmatter for structured settings, markdown body for prompts or
  context. Use when adding user-configurable settings to a Codex plugin,
  creating or reading .Codex/plugin-name.local.md files, storing per-project
  plugin state, implementing the plugin settings pattern, reading YAML frontmatter
  from bash hooks, making plugin behavior configurable per project, managing plugin
  state files, or enabling/disabling plugin behavior without editing hooks.json.
allowed-tools: Read Write Edit Glob
---

# Plugin Settings Pattern for Codex Plugins

## Overview

Plugins can store per-project configuration in `.Codex/plugin-name.local.md` — a file with YAML frontmatter for structured settings and a markdown body for prompts or context.

**Key characteristics:**
- File location: `.Codex/plugin-name.local.md` in project root
- Structure: YAML frontmatter + markdown body
- Purpose: Per-project plugin configuration and state
- Usage: Read from hooks, commands, and agents
- Lifecycle: User-managed (not in git, should be in `.gitignore`)

## Quick Start

1. **Design settings schema** — decide which fields, types, and defaults are needed
2. **Add gitignore entry** — `.Codex/*.local.md` so the file is never committed
3. **Create settings file** — `.Codex/plugin-name.local.md` in project root (see File Structure below)
4. **Implement quick-exit in hooks** — check file exists and `enabled: true` before any logic
5. **Parse frontmatter** — `FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$FILE")`
6. **Extract fields** — `VALUE=$(echo "$FRONTMATTER" | grep '^field:' | sed 's/field: *//')`
7. **Document in README** — provide a template and note that changes require Codex restart

## When to Use

- Adding configurable settings that differ per project
- Enabling/disabling hooks without modifying `hooks.json` (which requires restart anyway)
- Passing agent state between Codex sessions (multi-agent coordination)
- Feeding a prompt back as a loop continuation (ralph-loop pattern)
- Storing structured task assignments for subagents

## When NOT to Use

- Global settings shared across all projects — use environment variables instead
- Secrets or credentials — use environment variables, never settings files
- Configuration identical for all users — hardcode defaults or use plugin.json

---

## File Structure

### Basic Template

```markdown
---
enabled: true
setting1: value1
setting2: value2
numeric_setting: 42
list_setting: ["item1", "item2"]
---

# Additional Context

This markdown body can contain:
- Task descriptions
- Additional instructions
- Prompts to feed back to Codex
- Documentation or notes
```

### Example: Plugin State File

**.Codex/my-plugin.local.md:**
```markdown
---
enabled: true
strict_mode: false
max_retries: 3
notification_level: info
coordinator_session: team-leader
---

# Plugin Configuration

This plugin is configured for standard validation mode.
Contact @team-lead with questions.
```

## Reading Settings Files

### From Hooks (Bash Scripts)

**Pattern: Check existence and parse frontmatter**

```bash
STATE_FILE=".Codex/my-plugin.local.md"
[[ ! -f "$STATE_FILE" ]] && exit 0

FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$STATE_FILE")
ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//')
[[ "$ENABLED" != "true" ]] && exit 0

STRICT_MODE=$(echo "$FRONTMATTER" | grep '^strict_mode:' | sed 's/strict_mode: *//')
# Use $STRICT_MODE in hook logic
```

See `scripts/read-settings-hook.sh` for complete working example.

### From Commands

Commands can read settings files to customize behavior:

```markdown
---
description: Process data with plugin
allowed-tools: Read Bash
---

# Process Command

Steps:
1. Check if settings exist at `.Codex/my-plugin.local.md`
2. Read configuration using Read tool
3. Parse YAML frontmatter to extract settings
4. Apply settings to processing logic
5. Execute with configured behavior
```

### From Agents

Agents can reference settings in their instructions:

```markdown
---
name: configured-agent
description: Agent that adapts to project settings
---

Check for plugin settings at `.Codex/my-plugin.local.md`.
If present, parse YAML frontmatter and adapt behavior according to:
- enabled: Whether plugin is active
- mode: Processing mode (strict, standard, lenient)
- Additional configuration fields
```

## Parsing Techniques

For complete parsing patterns — lists, yq, multi-field extraction, atomic updates, validation, edge cases, and performance optimization — see `references/parsing-techniques.md`.

---

## Common Patterns

### Pattern 1: Temporarily Active Hooks

Use settings file to control hook activation:

```bash
STATE_FILE=".Codex/security-scan.local.md"
# Parse frontmatter as shown in Quick Start steps 5-6
[[ ! -f "$STATE_FILE" ]] && exit 0
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$STATE_FILE")
ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//')
[[ "$ENABLED" != "true" ]] && exit 0
# Hook logic here
```

**Use case:** Enable/disable hooks without editing hooks.json (requires restart).

### Pattern 2: Agent State Management

Store agent-specific state and configuration:

**.Codex/multi-agent-swarm.local.md:**
```markdown
---
agent_name: auth-agent
task_number: 3.5
pr_number: 1234
coordinator_session: team-leader
enabled: true
dependencies: ["Task 3.4"]
---

# Task Assignment

Implement JWT authentication for the API.

**Success Criteria:**
- Authentication endpoints created
- Tests passing
- PR created and CI green
```

Read from hooks to coordinate agents:

```bash
AGENT_NAME=$(echo "$FRONTMATTER" | grep '^agent_name:' | sed 's/agent_name: *//')
COORDINATOR=$(echo "$FRONTMATTER" | grep '^coordinator_session:' | sed 's/coordinator_session: *//')

# Send notification to coordinator
tmux send-keys -t "$COORDINATOR" "Agent $AGENT_NAME completed task" Enter
```

### Pattern 3: Configuration-Driven Behavior

**.Codex/my-plugin.local.md:**
```markdown
---
validation_level: strict
max_file_size: 1000000
allowed_extensions: [".js", ".ts", ".tsx"]
enable_logging: true
---

# Validation Configuration

Strict mode enabled for this project.
All writes validated against security policies.
```

Use in hooks or commands:

```bash
LEVEL=$(echo "$FRONTMATTER" | grep '^validation_level:' | sed 's/validation_level: *//')

case "$LEVEL" in
  strict)
    # Apply strict validation
    ;;
  standard)
    # Apply standard validation
    ;;
  lenient)
    # Apply lenient validation
    ;;
esac
```

---

## Creating Settings Files

### From Commands

Commands can create settings files:

```markdown
# Setup Command

Steps:
1. Use `AskUserQuestion` to gather configuration preferences
2. Create `.Codex/my-plugin.local.md` with YAML frontmatter
3. Set appropriate values based on user input
4. Inform user that settings are saved
5. Remind user to restart Codex for hooks to recognize changes
```

### Template Generation

Provide template in plugin README:

```markdown
## Configuration

Create `.Codex/my-plugin.local.md` in your project:

\`\`\`markdown
---
enabled: true
mode: standard
max_retries: 3
---

# Plugin Configuration

Your settings are active.
\`\`\`

After creating or editing, restart Codex for changes to take effect.
```

---

## Best Practices

### File Naming

✅ **DO:**
- Use `.Codex/plugin-name.local.md` format
- Match plugin name exactly
- Use `.local.md` suffix for user-local files

❌ **DON'T:**
- Use different directory (not `.Codex/`)
- Use inconsistent naming
- Use `.md` without `.local` (might be committed)

### Gitignore

Always add to `.gitignore`:

```gitignore
.Codex/*.local.md
.Codex/*.local.json
```

Document this in plugin README.

### Defaults

Provide sensible defaults when settings file doesn't exist:

```bash
if [[ ! -f "$STATE_FILE" ]]; then
  # Use defaults
  ENABLED=true
  MODE=standard
else
  # Read from file
  # ...
fi
```

### Validation

Validate settings values:

```bash
MAX=$(echo "$FRONTMATTER" | grep '^max_value:' | sed 's/max_value: *//')

# Validate numeric range
if ! [[ "$MAX" =~ ^[0-9]+$ ]] || [[ $MAX -lt 1 ]] || [[ $MAX -gt 100 ]]; then
  echo "⚠️  Invalid max_value in settings (must be 1-100)" >&2
  MAX=10  # Use default
fi
```

### Restart Requirement

**Important:** Settings changes require Codex restart.

Document in your README:

```markdown
## Changing Settings

After editing `.Codex/my-plugin.local.md`:
1. Save the file
2. Exit Codex
3. Restart: `Codex` or `cc`
4. New settings will be loaded
```

Hooks cannot be hot-swapped within a session.

---

## Security Considerations

### Sanitize User Input

When writing settings files from user input:

```bash
# Escape quotes in user input
SAFE_VALUE=$(echo "$USER_INPUT" | sed 's/"/\\"/g')

# Write to file
cat > "$STATE_FILE" <<EOF
---
user_setting: "$SAFE_VALUE"
---
EOF
```

### Validate File Paths

If settings contain file paths:

```bash
FILE_PATH=$(echo "$FRONTMATTER" | grep '^data_file:' | sed 's/data_file: *//')

# Check for path traversal
if [[ "$FILE_PATH" == *".."* ]]; then
  echo "⚠️  Invalid path in settings (path traversal)" >&2
  exit 2
fi
```

### Permissions

Settings files should be:
- Readable by user only (`chmod 600`)
- Not committed to git
- Not shared between users

## Real-World Examples

For deep dives into production plugin implementations — multi-agent-swarm (agent coordination with tmux notifications) and ralph-loop (loop state management with completion detection) — see `references/real-world-examples.md`.

---

## Testing & Validation

After implementing the plugin settings pattern:

1. **File existence check** — hook exits cleanly (`exit 0`) when settings file is absent
2. **Enabled flag** — hook is skipped when `enabled: false` in frontmatter
3. **Field defaults** — all fields have fallback values when absent or empty
4. **Gitignore** — `.Codex/*.local.md` is listed in `.gitignore`
5. **Restart documented** — README includes restart instruction after settings change

**Quality gates:**
- [ ] Quick-exit pattern used in all hooks before any file I/O
- [ ] All frontmatter fields have defaults for the missing-file case
- [ ] No credentials or secrets stored in settings files (use env vars)
- [ ] No path traversal possible from settings-derived file paths
- [ ] Settings file template provided in plugin README
- [ ] `.Codex/*.local.md` in `.gitignore`

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/parsing-techniques.md` | Complete bash parsing guide — lists, yq, multi-field extraction, atomic updates, validation, edge cases |
| `references/real-world-examples.md` | Deep dive: multi-agent-swarm (agent coordination) and ralph-loop (loop control) |
| `scripts/read-settings-hook.sh` | Working hook that reads and applies settings |
| `references/create-settings-command.md` | Command that creates a settings file |
| `references/example-settings.md` | Template settings file |
| `scripts/validate-settings.sh` | Validate settings file structure |
| `scripts/parse-frontmatter.sh` | Extract frontmatter fields |
