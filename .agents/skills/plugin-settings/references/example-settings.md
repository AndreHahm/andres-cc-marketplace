# Example Plugin Settings File

**R18 exception (recorded):** the "Template: Agent State File" example below intentionally exceeds the rulebook's 30-line code-block threshold — it's a complete, coherent settings template; splitting it would break it.

## Template: Basic Configuration

**.claude/my-plugin.local.md:**

```markdown
---
enabled: true
mode: standard
---

# My Plugin Configuration

Plugin is active in standard mode.
```

## Template: Advanced Configuration

**.claude/my-plugin.local.md:**

```markdown
---
enabled: true
strict_mode: false
max_file_size: 1000000
allowed_extensions: [".js", ".ts", ".tsx"]
enable_logging: true
retry_attempts: 3
---

# My Plugin Advanced Configuration

Standard validation mode, 1MB file size limit, JavaScript/TypeScript files
allowed, logging on, 3 retry attempts. Contact @team-lead with questions.
```

## Template: Agent State File

See `real-world-examples.md`'s "multi-agent-swarm Plugin" section for the canonical worked example of this pattern (`agent_name`/`task_number`/`pr_number`/`coordinator_session`/`enabled`/`dependencies` fields) — it also shows the hook implementation that reads this file, which this template alone doesn't cover.

## Template: Feature Flag Pattern

**.claude/experimental-features.local.md:**

```markdown
---
enabled: true
features:
  - ai_suggestions
  - auto_formatting
  - advanced_refactoring
experimental_mode: false
---

# Experimental Features Configuration

Current enabled features:
- AI-powered code suggestions
- Automatic code formatting
- Advanced refactoring tools

Experimental mode is OFF (stable features only).
```

## Usage in Hooks

These templates can be read by hooks:

```bash
# Check if plugin is configured
if [[ ! -f ".claude/my-plugin.local.md" ]]; then
  exit 0  # Not configured, skip hook
fi

# Read settings
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' ".claude/my-plugin.local.md")
ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//')

# Apply settings
if [[ "$ENABLED" == "true" ]]; then
  # Hook is active
  # ...
fi
```

## Gitignore

Always add to project `.gitignore`:

```gitignore
# Plugin settings (user-local, not committed)
.claude/*.local.md
.claude/*.local.json
```

## Editing Settings

Users can edit settings files manually:

```bash
# Edit settings
vim .claude/my-plugin.local.md

# Changes take effect after restart
exit  # Exit Claude Code
claude  # Restart
```

Changes require Claude Code restart - hooks can't be hot-swapped.
