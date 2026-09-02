---
name: session-export
description: >-
  Exports a Claude Code session as a clean, readable markdown transcript.
  Use when the user wants to export a session, create a transcript, save
  session history to a file, or says "export this session".
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Export

Export a session as a clean transcript.

## When to Use

- Wants to export a session, create a transcript, or save session history to a file
- "export this session", "create a transcript"

## Step 1: Resolve the session

If no session specified, use the current one:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --project "$(basename $(pwd))" --limit 1 --format json
```

Use the `path` field from the result. `--format json` is required — without it, the command's table output has no `path` field.

## Step 2: Export

To print to conversation:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" export <session-jsonl-path> --format md
```

To save to file, use an absolute path outside this repository (or one the user explicitly names) — a bare relative filename resolves against the current working directory, which is often a repo root, and would leave an untracked file behind:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" export <session-jsonl-path> --format md --output "$HOME/session-transcript.md"
```

For plain text:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" export <session-jsonl-path> --format txt --output "$HOME/session-transcript.txt"
```

Tool calls are summarized (tool name only, not full input JSON) by default; pass `--no-include-tools` to omit them entirely.

## Step 3: Present

If written to file, confirm the path and line count. If inline, present the transcript directly.

The exported transcript contains verbatim user messages, file paths, and (if included) tool call summaries from the original session — review before sharing outside the immediate context.

## Testing & Validation

**Verify this skill activates on:**
- "export this session"
- "create a transcript of this conversation"
- "save my session history to a file"

**Verify it does NOT activate on:**
- "show session details for X" (no file output wanted) → `session-detail`

**Quality gates:**
- [ ] Step 1's command includes `--format json` so `path` is actually resolvable
- [ ] `--output` examples never use a bare relative filename
