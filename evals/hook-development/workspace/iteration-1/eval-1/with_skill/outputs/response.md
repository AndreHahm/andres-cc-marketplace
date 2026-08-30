# Frontmatter `hooks:` block for `.claude/skills/my-validator/SKILL.md`

Since `my-validator` is a **project-level skill** (not part of any plugin), `${CLAUDE_PLUGIN_ROOT}` must not be used — it is not confirmed available inside a SKILL.md-embedded `hooks:` block, and is confirmed to resolve unpredictably (duplicated-path failure) for exactly this case: a project-level skill with no enclosing plugin. A bare relative path (e.g. `./hooks/check.sh` or `hooks/check.sh`) must also not be used, since hook handlers run in the live session's current working directory, not the skill's own directory.

The correct variable is `$CLAUDE_PROJECT_DIR`, combined with the full path from the project root to the script — this is documented as stable regardless of cwd.

## Exact frontmatter block

```yaml
---
name: my-validator
description: <your skill's description>
hooks:
  PostToolUse:
    - matcher: "^(Write|Edit)$"
      hooks:
        - type: command
          command: "${CLAUDE_PROJECT_DIR}/.claude/skills/my-validator/hooks/check.sh"
          timeout: 5000
---
```

## Notes on each piece

- **`matcher: "^(Write|Edit)$"`** — fires on either a `Write` or an `Edit` tool call. This is a regex matcher, not a literal list, so it needs the anchors/alternation shown (a bare `Write|Edit` without anchors would also work but is less precise).
- **`hooks:` (inner array)** — required nesting: even a single hook must live inside its own `hooks: [...]` array under the matcher entry. Omitting this nested array is the #1 JSON/YAML structural mistake for hook configs.
- **`command`** — uses `${CLAUDE_PROJECT_DIR}` (not `${CLAUDE_PLUGIN_ROOT}`, not a bare relative path) followed by the explicit path from the project root: `.claude/skills/my-validator/hooks/check.sh`. This matches where the script actually lives on disk for this project-level skill.
- **`timeout`** — optional; 5000ms shown as a reasonable default for a validation script. Adjust based on what `check.sh` actually does.

## Reminder for `check.sh` itself

The script must read event data from **stdin as JSON**, not environment variables:

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path')
# ... validation logic using $FILE_PATH ...
```

This hook is registered only while the `my-validator` skill is active (component-scoped hook behavior, as opposed to a marketplace/plugin-level `hooks/hooks.json`).
