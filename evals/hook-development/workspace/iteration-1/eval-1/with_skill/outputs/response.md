# Frontmatter `hooks:` block for `.claude/skills/my-validator/SKILL.md`

`.claude/skills/my-validator/SKILL.md` is a **project-level skill** (no enclosing plugin), so
`$CLAUDE_PLUGIN_ROOT` is not available — the `hook-development` skill explicitly calls this out as
confirmed broken in that case. Use a relative path instead, resolved relative to the skill's own
directory (`.claude/skills/my-validator/`), which makes `./hooks/check.sh` resolve to
`.claude/skills/my-validator/hooks/check.sh` — exactly the script location requested.

```yaml
---
name: my-validator
description: <your existing description here>
hooks:
  PostToolUse:
    - matcher: "^(Write|Edit)$"
      hooks:
        - type: command
          command: "./hooks/check.sh"
          timeout: 5000
---
```

## Why this shape

- **Nested `hooks:` array** — `PostToolUse` maps to a list of matcher objects, each with its own
  nested `hooks: [...]` array of actual hook definitions. Omitting this inner array is the most common
  hooks.json/frontmatter mistake and causes the hook to silently do nothing.
- **`matcher: "^(Write|Edit)$"`** — fires only for the `Write` and `Edit` tools, per the request ("after
  every Write/Edit").
- **`command: "./hooks/check.sh"`** — a relative path, resolved relative to the skill's own directory,
  not `$CLAUDE_PLUGIN_ROOT` (unavailable/broken for a project-level skill with no enclosing plugin) and
  not `$CLAUDE_PROJECT_DIR` (works, but is unnecessarily verbose here since a plain relative path already
  resolves correctly from the skill directory).
- **`timeout: 5000`** — a reasonable explicit timeout (milliseconds) so the hook can't hang the tool call
  indefinitely; adjust to whatever `check.sh` actually needs.
- Hooks defined this way are registered only while the `my-validator` skill is active, per
  `hook-development`'s "Hook Frontmatter Hooks (skill/agent-embedded)" section.

## Script side note (not part of the frontmatter, but required for the hook to work)

`check.sh` must read its event data from **stdin**, not environment variables — the skill's own
"CRITICAL: Command Hooks Receive Data via Stdin" section:

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path')
# ...validation logic...
```

Make sure `.claude/skills/my-validator/hooks/check.sh` is executable (`chmod +x`) so Claude Code can run
it directly via the `command` hook type.
