---
description: Transfer the current Claude Code session into a resumable Codex thread
argument-hint: '[--source <claude-jsonl>]'
disable-model-invocation: true
allowed-tools: Bash(node:*)
---

Raw slash-command arguments: `$ARGUMENTS`

Validate `$ARGUMENTS` against the whitelist in the `argument-hint` above (`--source <claude-jsonl>`) before running anything — do not interpolate the raw argument string into a shell command. If `--source` is present, its value must be a plausible file path containing none of `` $ ` ; | & < > `` — reject/`AskUserQuestion` if it does or if any other flag is given. Then run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" transfer
```

(append `--source "<validated path>"` as its own quoted argument if one was given — never as a single unquoted `$ARGUMENTS` blob.)

Present the command output to the user exactly as returned. Preserve the Codex session ID and the `codex resume <session-id>` command verbatim — never hand-reconstruct it.
