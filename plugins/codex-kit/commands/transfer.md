---
description: Transfer the current Claude Code session into a resumable Codex thread
argument-hint: '[--source <claude-jsonl>]'
disable-model-invocation: true
allowed-tools: Bash(node */scripts/codex-companion.mjs:*), AskUserQuestion
---

Raw slash-command arguments: `$ARGUMENTS`

Validate `$ARGUMENTS` against the whitelist in the `argument-hint` above (`--source <claude-jsonl>`) before running anything — do not interpolate the raw argument string into a shell command. If `--source` is present, its value must match the allowlist `^[A-Za-z0-9._~\-\/\\: ]+$` (letters, digits, `.`, `_`, `~`, `-`, `/`, `\`, `:`, and spaces only — `~` is included so a home-relative path like `~/.claude/projects/.../session.jsonl` still validates; the same allowlist-not-denylist discipline `status`/`result`/`cancel` use for their `job-id` argument) — reject/`AskUserQuestion` if it doesn't match or if any other flag is given.

**Confirm via `AskUserQuestion` before running the transfer** — every time, not just the first call in the session (this is this command's named exception to `codex-prompt-protocol/references/shared-skill-conventions.md` §3's session-level first-send gate: the egress here is large enough to warrant asking every time, not only once). This sends the **entire** Claude Code session transcript (every message, file content, and command output that appeared in it) to Codex — the largest single data-egress path in this plugin. State plainly which transcript will be sent (the current session, or the `--source` path if one was given) before asking. Options: "Send the full session transcript to Codex" / "Cancel". Only after confirmation, run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" transfer
```

(append `--source "<validated path>"` as its own quoted argument if one was given — never as a single unquoted `$ARGUMENTS` blob.)

Present the command output to the user exactly as returned. Preserve the Codex session ID and the `codex resume <session-id>` command verbatim — never hand-reconstruct it.
