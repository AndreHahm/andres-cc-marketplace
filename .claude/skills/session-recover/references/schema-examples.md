# Session Recover — Extracted Schema Examples

Longer JSON/directory-tree examples referenced from
[file-structure.md](file-structure.md), extracted per plugin-rulebook R18 (inline code blocks
over 10 lines are flagged for extraction to `references/`). Each example below is referenced
from file-structure.md's own section of the same name — read that file first for the
surrounding explanation; this file holds only the full-length examples themselves.

## Directory Layout

```
~/.claude/
  projects/                           # Per-project session storage (primary)
    <normalized-path>/
      sessions-index.json             # Master index of all sessions
      <session-id>.jsonl              # Session transcript
      <session-id>/                   # Session subdirectory (optional)
        subagents/
          agent-<agent-id>.meta.json  # Agent metadata
          agent-<agent-id>.jsonl      # Agent transcript
        tool-results/
          toolu_<tool-id>.txt         # Large tool outputs
      memory/                         # Persistent memory files (MEMORY.md, etc.)
  history.jsonl                       # Global prompt history (no session IDs)
  tasks/                              # Task tracking (per-session lock/highwatermark)
  plans/                              # Plan documents (random-name.md)
  debug/                              # Per-session debug logs (<session-id>.txt)
  transcripts/                        # Global tool operation logs (ses_<id>.jsonl)
  file-history/                       # File modification backups
  todos/                              # Todo items
```

## sessions-index.json Schema

Condensed to the 6 fields file-structure.md's "Key fields for session identification" list documents
below — `fullPath`, `fileMtime`, `created`, and `projectPath` also exist on every entry but aren't shown
here since they're not identification-relevant:

```json
{
  "version": 1,
  "entries": [
    { "sessionId": "20089b2a-...", "firstPrompt": "fix the login bug", "summary": "Fixed auth redirect...", "modified": "2026-03-07T12:21:43.806Z", "gitBranch": "main", "isSidechain": false }
  ],
  "originalPath": "/path/to/project"
}
```

## User message (full example)

Condensed to the fields `extract_user_text` actually reads (`message.role`, `message.content`) plus
identity/ordering fields (`uuid`, `timestamp`). `parentUuid`, `isSidechain`, `cwd`, top-level `sessionId`,
`version`, and `gitBranch` also exist on every real user message but aren't consumed by extraction logic:

```json
{
  "type": "user",
  "message": { "role": "user", "content": "fix the login bug" },
  "uuid": "msg-uuid",
  "timestamp": "2026-03-07T03:25:03.477Z"
}
```

## Assistant message (full example)

```json
{
  "type": "assistant",
  "message": { "role": "assistant", "model": "claude-opus-4-6", "content": [
    { "type": "thinking", "thinking": "internal reasoning..." },
    { "type": "text", "text": "visible response text" },
    { "type": "tool_use", "id": "toolu_...", "name": "Bash", "input": { "command": "..." } }
  ]}
}
```
