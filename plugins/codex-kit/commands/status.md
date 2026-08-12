---
description: >-
  Show active and recent Codex jobs for this repository, including
  review-gate status
argument-hint: '[job-id] [--wait] [--timeout-ms <ms>] [--all]'
disable-model-invocation: true
allowed-tools: Bash(node */scripts/codex-companion.mjs:*), Glob
---

Raw slash-command arguments: `$ARGUMENTS`

Validate `$ARGUMENTS` against the whitelist in the `argument-hint` above (`[job-id]`, `--wait`, `--timeout-ms <ms>`, `--all`) before running anything — do not interpolate the raw argument string into a shell command. A `job-id`, if present, must match `^[A-Za-z0-9._-]+$`; `--timeout-ms`'s value must be a positive integer. Reject/`AskUserQuestion` on anything else, then run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" status
```

(append the validated `<job-id>`/`--wait`/`--timeout-ms "<value>"`/`--all` as separate, individually-quoted arguments — never as a single unquoted `$ARGUMENTS` blob.)

If the user did not pass a job ID:
- Render the command output as a single Markdown table for the current and past runs in this session.
- Keep it compact. Do not include progress blocks or extra prose outside the table.
- Preserve the actionable fields from the command output, including job ID, kind, status, phase, elapsed or duration, summary, and follow-up commands.
- After the table, list the 10 most recent report files from `${CLAUDE_PLUGIN_DATA}/reviews/` (filename + timestamp), noting these are **not** asserted to be 1:1 with the jobs above — a failed run may lack a report, and a `-failed.md` report may not correspond to a listed job.

If the user did pass a job ID:
- Present the full command output to the user.
- Do not summarize or condense it.
