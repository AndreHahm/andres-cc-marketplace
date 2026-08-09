---
description: Cancel an active background Codex job in this repository
argument-hint: '[job-id]'
disable-model-invocation: true
allowed-tools: Bash(node:*), AskUserQuestion
---

Raw slash-command arguments: `$ARGUMENTS`

Validate `$ARGUMENTS` against the whitelist in the `argument-hint` above (`[job-id]`) before running anything — do not interpolate the raw argument string into a shell command. A `job-id`, if present, must match `^[A-Za-z0-9._-]+$`; reject/`AskUserQuestion` on anything else.

If no job-id was given, run `node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" status --all --json` yourself first (via your own Bash tool call) to check for active jobs. If more than one is active, `AskUserQuestion` to disambiguate which one to cancel before proceeding — never guess or cancel all of them. If exactly one is active, use its id. If none are active, tell the user and stop.

Once a specific job-id is determined (from `$ARGUMENTS` or from disambiguation above), run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" cancel "<validated job-id>"
```

Present the result verbatim. Cancellation is not instant, and cancelling a `codex-rescue` job does **not** revert any file changes already made — if the user needs to undo changes, they must `git restore` manually; say so if a rescue-kind job is being cancelled.
