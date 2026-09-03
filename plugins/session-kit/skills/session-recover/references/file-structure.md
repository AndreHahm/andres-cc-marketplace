# Claude Code Local File Structure

Ground-truth reference for `~/.claude/` directory layout and JSONL session format.

## Directory Layout

See [schema-examples.md#directory-layout](schema-examples.md#directory-layout) for the full tree.

## Path Normalization

Project paths are encoded by replacing every path separator with `-`. On POSIX this is just `/`; on
Windows, Claude Code's own encoding also replaces `\` and `:` (e.g. `C:\Dev\proj` → `C--Dev-proj`).
This skill's own `scripts/extract_resume_context.py` imports `session-kit`'s shared
`scripts/session_store.py::encode_project_path` (aliased as `normalize_path`) rather than reimplementing
it — one function, one docstring, which is the canonical source for this behavior rather than restating
it here, since a second hand-written copy of this fact is exactly what drifted out of date before.

| Original | Normalized |
|----------|-----------|
| `/path/to/project` | `-path-to-project` |
| `/another/workspace/app` | `-another-workspace-app` |

## sessions-index.json Schema

See [schema-examples.md#sessions-indexjson-schema](schema-examples.md#sessions-indexjson-schema) for the full example.

Key fields for session identification:
- `sessionId` — UUID v4 format
- `firstPrompt` — first user message (best for topic matching)
- `summary` — auto-generated summary of the session
- `modified` — last activity timestamp (ISO 8601)
- `gitBranch` — git branch at session time
- `isSidechain` — `false` for main conversations

## Compaction in Session Files

Claude Code uses server-side compaction. When context fills up, two consecutive lines appear:

### Line 1: compact_boundary marker

```json
{
  "type": "system",
  "subtype": "compact_boundary",
  "parentUuid": null,
  "logicalParentUuid": "prev-uuid",
  "compactMetadata": {
    "trigger": "input_tokens",
    "preTokens": 180000
  }
}
```

### Line 2: Compact summary (special user message)

```json
{
  "type": "user",
  "isCompactSummary": true,
  "isVisibleInTranscriptOnly": true,
  "message": {
    "role": "user",
    "content": "This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.\n\nAnalysis:\n1. **Initial Request**: User asked to...\n2. **Progress**: Completed X, Y, Z...\n3. **Current state**: Working on..."
  }
}
```

Key properties:
- **`isCompactSummary: true`** — most reliable way to identify compact summaries
- **`isVisibleInTranscriptOnly: true`** — not sent to the API, only stored in the transcript
- Summary is always a plain string in `.message.content` (not an array)
- Typically 12K-31K characters (high-density information)
- A long session may have multiple compact boundaries (4+ is common for 10MB+ sessions)
- The **last** compact boundary's summary reflects the most recent state
- Messages after the last boundary are the "hot zone" — they were in Claude's live context

## Session JSONL Message Types

Each `.jsonl` file has one JSON object per line. Common types:

### file-history-snapshot (always first line)

```json
{
  "type": "file-history-snapshot",
  "messageId": "uuid",
  "snapshot": { "trackedFileBackups": {}, "timestamp": "..." },
  "isSnapshotUpdate": false
}
```

### User message

See [schema-examples.md#user-message-full-example](schema-examples.md#user-message-full-example) for the full example.

**Important**: `.message.content` can be:
- A **string** for plain text user messages
- An **array** of content blocks for tool results and multi-part messages:
  ```json
  "content": [
    { "type": "tool_result", "tool_use_id": "toolu_...", "content": "..." },
    { "type": "text", "text": "now do X" }
  ]
  ```

### Assistant message

See [schema-examples.md#assistant-message-full-example](schema-examples.md#assistant-message-full-example) for the full example.

Content block types in assistant messages:
- `thinking` — internal reasoning (skip when extracting actionable context)
- `text` — visible response to user (extract this)
- `tool_use` — tool invocations (useful for understanding what was done)

### Noise types (filtered, not part of the conversational schema)

`extract_resume_context.py`'s `NOISE_TYPES` filters four message types when extracting conversational
content: `progress`, `queue-operation`, `file-history-snapshot` (documented above as a real first-line
schema element — it's real, but treated as noise for the purposes of reconstructing "what was
discussed"), and `last-prompt`. It also filters `api_error`/`turn_duration`/`stop_hook_summary` system
subtypes. This is the complete, canonical list — see `extract_resume_context.py`'s own `NOISE_TYPES`
constant as the source of truth.

### Tool result (user message with tool output)

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      { "type": "tool_result", "tool_use_id": "toolu_...", "content": "command output..." }
    ]
  }
}
```

## history.jsonl Schema

Global prompt log. Does NOT contain session IDs — only useful for finding when a prompt was issued and
in which project:

```json
{
  "display": "/init ",
  "pastedContents": {},
  "timestamp": 1758996122446,
  "project": "/path/to/project"
}
```
