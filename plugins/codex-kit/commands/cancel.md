---
description: Cancel an active background Codex job in this repository
argument-hint: '[job-id]'
disable-model-invocation: true
allowed-tools: Bash(node:*), AskUserQuestion
---

If no job-id was passed in `$ARGUMENTS`, first check `/codex-kit:status --all` output for active jobs. If more than one is active, `AskUserQuestion` to disambiguate which one to cancel before proceeding — never guess or cancel all of them.

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" cancel "$ARGUMENTS"`

Present the result verbatim. Cancellation is not instant, and cancelling a `codex-rescue` job does **not** revert any file changes already made — if the user needs to undo changes, they must `git restore` manually; say so if a rescue-kind job is being cancelled.
