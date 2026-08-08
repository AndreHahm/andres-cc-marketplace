---
description: Show the stored final output for a finished Codex job in this repository
argument-hint: '[job-id]'
disable-model-invocation: true
allowed-tools: Bash(node:*), Glob
---

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" result "$ARGUMENTS"`

Present the full command output to the user. Do not summarize or condense it. Preserve all details including:
- Job ID and status
- The complete result payload, including verdict, summary, findings, details, artifacts, and next steps
- File paths and line numbers exactly as reported
- Any error messages or parse errors
- Follow-up commands such as `/codex-kit:status <id>` and `/codex-kit:review`

After the result, list the 3 most recent report files from `${CLAUDE_PLUGIN_DATA}/reviews/` for timestamp-correlation with this job, without asserting which one matches — the user decides by comparing timestamps.
