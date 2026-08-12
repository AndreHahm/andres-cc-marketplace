---
description: Show the stored final output for a finished Codex job in this repository
argument-hint: '[job-id]'
disable-model-invocation: true
allowed-tools: Bash(node */scripts/codex-companion.mjs:*), Glob
---

Raw slash-command arguments: `$ARGUMENTS`

Validate `$ARGUMENTS` against the whitelist in the `argument-hint` above (`[job-id]`) before running anything — do not interpolate the raw argument string into a shell command. A `job-id`, if present, must match `^[A-Za-z0-9._-]+$`. Reject/`AskUserQuestion` on anything else, then run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" result
```

(append the validated `<job-id>` as its own quoted argument if one was given — never as a single unquoted `$ARGUMENTS` blob.)

Present the full command output to the user. Do not summarize or condense it. Preserve all details including:
- Job ID and status
- The complete result payload, including verdict, summary, findings, details, artifacts, and next steps
- File paths and line numbers exactly as reported
- Any error messages or parse errors
- Follow-up commands such as `/codex-kit:status <id>` and `/codex-kit:review`

After the result, list the 3 most recent report files from `${CLAUDE_PLUGIN_DATA}/reviews/` for timestamp-correlation with this job, without asserting which one matches — the user decides by comparing timestamps.
