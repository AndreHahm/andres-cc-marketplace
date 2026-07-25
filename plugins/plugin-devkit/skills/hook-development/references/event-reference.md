# Complete Event Reference

Detailed documentation of all Claude Code events, when they fire, and what data is available.

## Table of Contents

- [Hook Type List](#hook-type-list)
- [Tool Events](#tool-events)
  - [PreToolUse](#pretooluse)
  - [PostToolUse](#posttooluse)
  - [PostToolUseFailure](#posttoolusefailure)
- [Prompt Events](#prompt-events)
  - [UserPromptSubmit](#userpromptsubmit)
- [Session Events](#session-events)
  - [SessionStart](#sessionstart)
  - [SessionEnd](#sessionend)
  - [PreCompact](#precompact)
- [Permission Events](#permission-events)
  - [PermissionRequest](#permissionrequest)
- [Notification Events](#notification-events)
  - [Notification](#notification)
- [Lifecycle Events](#lifecycle-events)
  - [Stop](#stop)
- [Subagent Events](#subagent-events)
  - [SubagentStart](#subagentstart)
  - [SubagentStop](#subagentstop)
- [Newer Events](#newer-events)
- [Worktree Events](#worktree-events)
  - [WorktreeCreate](#worktreecreate)
- [No-Matcher-Support Events](#no-matcher-support-events)
- [Hook Type / Event Compatibility Matrix](#hook-type--event-compatibility-matrix)
- [Event Data Availability Matrix](#event-data-availability-matrix)
- [Common Event Selection Mistakes](#common-event-selection-mistakes)
- [Timing Diagram: Complete Event Sequence](#timing-diagram-complete-event-sequence)
- [Event Selection Decision Tree](#event-selection-decision-tree)

---

## Hook Type List

Valid values for a handler's `type` field: `command`, `http`, `mcp_tool`, `prompt`, `agent`.

`mcp_tool` calls an installed MCP server tool as the hook action and requires two additional fields:

| Field | Required | Description |
|---|---|---|
| `server` | yes | MCP server name |
| `tool` | yes | Tool name on that server |

See `references/mcp-tools.md` for the full `mcp_tool` reference.

---

## Tool Events

### PreToolUse

**When:** Before any tool executes (can block execution)

**Availability:** All Claude Code tools (Read, Write, Edit, Bash, Glob, Grep, etc.)

**Event data available (see `command-hook-input-parsing.md` for the full stdin schema):**
```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.js",
    "content": "..."
  }
}
```

**Common use cases:**
- Validate input before tool runs (e.g., reject dangerous paths)
- Block sensitive operations (e.g., prevent deleting from root)
- Audit what tools are being called
- Rate limiting (e.g., max N bash commands per minute)

**Blocking capability:** Yes, can prevent tool from executing

**Performance:** Must be <100ms (happens before every tool)

**Typical execution time:** <50ms for validation logic

**Example matcher:**
```json
{
  "matcher": "^(Write|Edit|Bash)$"  // Validate these tool types
}
```

---

### PostToolUse

**When:** After tool successfully completes

**Availability:** All Claude Code tools

**Event data available (see `command-hook-input-parsing.md` for the full stdin schema):**
```json
{
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.js",
    "content": "..."
  },
  "tool_response": "File written successfully"
}
```

**`tool_name` for sub-dispatch tools:** a matcher targeting an `Agent()` or `Skill()` dispatch (not just the built-in file/shell tools shown above) should match on the literal strings `"Agent"` and `"Skill"` — confirmed directly against a real session transcript (`grep -o '"name":"[A-Za-z_]*"' <session>.jsonl` showed both appearing exactly this way, alongside `AskUserQuestion` serializing as `"name":"AskUserQuestion"`), not inferred from documentation alone. See `plugins/plugin-devkit/hooks/r26-expensive-action-check.py`'s header comment for the verification note this was first confirmed in.

**Common use cases:**
- Format code after write (prettier, black)
- Lint after edit
- Log tool usage
- Trigger post-processing
- Update metrics/telemetry

**Blocking capability:** No (tool already executed)

**Frequency:** High (every successful tool use)

**Performance:** Typical 1-2 seconds for formatting, but multiplied by frequency

**Important:** Don't make this too expensive; runs on EVERY tool use

**Example matcher:**
```json
{
  "matcher": "^(Write|Edit)$"  // Format on write/edit only
}
```

---

### PostToolUseFailure

**When:** After tool fails with error

**Availability:** All Claude Code tools

**Event data available (see `command-hook-input-parsing.md` for the full stdin schema):**
```json
{
  "hook_event_name": "PostToolUseFailure",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test"
  },
  "error": {
    "message": "Command failed with exit code 1",
    "code": 1,
    "stderr": "Test output..."
  }
}
```

**Common use cases:**
- Error recovery (retry with different approach)
- Error logging/alerting
- Helpful error messages
- Cleanup after failure
- User notification

**Blocking capability:** No (error already occurred)

**Frequency:** Lower than PostToolUse (only on failures)

**Important:** Result is immutable; can't fix the error in hook

**Example matcher:**
```json
{
  "matcher": "^Bash$"  // Handle bash errors specially
}
```

---

## Prompt Events

### UserPromptSubmit

**When:** User submits a prompt to Claude

**Availability:** All user prompts

**Event data available:**
```json
{
  "hook_event_name": "UserPromptSubmit",
  "session_id": "abc123",
  "prompt": "Write a function that sorts an array",
  "cwd": "/current/dir"
}
```

**Common use cases:**
- Validate prompt input (reject if contains harmful content)
- Parse special commands (e.g., "/analyze" triggers different flow)
- Rate limiting (prevent prompt spam)
- Logging/analytics
- Security checks

**Blocking capability:** Yes, can prevent Claude from processing prompt

**Frequency:** Once per user input

**Performance:** Must be <100ms (happens before processing)

**Example matcher:**
```json
{
  "matcher": "commit|push|deploy"  // Special handling for deployment commands
}
```

---

## Session Events

### SessionStart

**When:** Claude Code session begins

**Availability:** Once per session

**Event data available:**
```json
{
  "hook_event_name": "SessionStart",
  "session_id": "abc123",
  "cwd": "/current/dir"
}
```

**Common use cases:**
- Initialize plugin state
- Setup logging
- Check plugin configuration
- Verify dependencies
- Load caches

**Blocking capability:** No

**Frequency:** Once per session

**Important:** Early in session; dependencies might not be ready yet

**Example matcher:**
```json
{
  "matcher": ".*"  // Always initialize
}
```

---

### SessionEnd

**When:** Claude Code session ends (user closes, etc.)

**Availability:** Once per session

**Event data available:**
```json
{
  "hook_event_name": "SessionEnd",
  "session_id": "abc123",
  "cwd": "/current/dir"
}
```

**Common use cases:**
- Cleanup temporary files
- Archive logs
- Upload metrics
- Save state
- Close connections

**Blocking capability:** No (session ending regardless)

**Frequency:** Once per session

**Important:** Last chance to clean up; don't block session close

**Example matcher:**
```json
{
  "matcher": ".*"  // Always cleanup on session end
}
```

---

### PreCompact

**When:** Before conversation history is compacted

**Availability:** When history compaction triggered

**Event data available:**
```json
{
  "historySize": 50000,
  "messageCount": 25,
  "compactingTo": 10000,
  "timestamp": 1234567890
}
```

**Common use cases:**
- Backup conversation history
- Archive logs
- Summarize conversation
- Extract important data before compaction
- Trigger cleanup

**Blocking capability:** Yes, can prevent compaction

**Frequency:** Rare (only when history grows large)

**Important:** Runs on large histories; be quick

**Example matcher:**
```json
{
  "matcher": ".*"  // Backup before compacting
}
```

---

## Permission Events

### PermissionRequest

**When:** Claude Code requests user permission

**Availability:** When permissions needed (tool access, network, etc.)

**Event data available:**
```json
{
  "permission": "bash",
  "description": "Claude wants to run bash commands",
  "reason": "Running tests",
  "timestamp": 1234567890
}
```

**Common use cases:**
- Automatic approval workflow
- Audit logging
- Custom permission logic
- Rate limiting permissions
- Integration with enterprise systems

**Blocking capability:** Can approve/deny

**Frequency:** As needed (permissions vary)

**Important:** User might already be responding; be quick

**Example matcher:**
```json
{
  "matcher": "bash"  // Special handling for bash permission
}
```

---

## Notification Events

### Notification

**When:** Claude Code sends notification to user

**Availability:** Various notifications

**Event data available:**
```json
{
  "type": "warning|error|info|success",
  "title": "Test Failed",
  "message": "Some tests failed. Review output.",
  "timestamp": 1234567890
}
```

**Common use cases:**
- Route notifications (email, Slack, etc.)
- Filter notifications (only errors)
- Suppress notifications
- Enhance notifications with context
- Create audit log

**Blocking capability:** No (notification already created)

**Frequency:** Varies by usage

**Example matcher:**
```json
{
  "matcher": "error"  // Route errors to monitoring system
}
```

---

## Lifecycle Events

### Stop

**When:** Claude Code stop signal received (user clicks stop, timeout, etc.)

**Availability:** When stop requested

**Event data available:**
```json
{
  "reason": "user|timeout|error",
  "currentOperation": "writing_file",
  "timestamp": 1234567890
}
```

**Common use cases:**
- Cleanup current operation
- Flush logs
- Finalize state
- Send final metrics
- Cancel pending operations

**Blocking capability:** Can prevent stop

**Frequency:** Rare (only when stopping)

**Important:** Should be very quick (user expecting to stop)

**Example matcher:**
```json
{
  "matcher": ".*"  // Always cleanup on stop
}
```

---

## Subagent Events

### SubagentStart

**When:** Subagent is started

**Availability:** When subagent created

**Event data available:**
```json
{
  "agentId": "agent_...",
  "agentType": "general-purpose|explore|plan",
  "description": "Exploring codebase",
  "tools": ["Read", "Glob", "Grep"],
  "timestamp": 1234567890
}
```

**Common use cases:**
- Log subagent creation
- Audit who is creating agents
- Set resource limits
- Monitor agent count
- Integration with external systems

**Blocking capability:** Can prevent subagent start

**Frequency:** When subagents created

**Example matcher:**
```json
{
  "matcher": ".*"  // Monitor all subagents
}
```

---

### SubagentStop

**When:** Subagent stops

**Availability:** When subagent ends

**Event data available:**
```json
{
  "agentId": "agent_...",
  "agentType": "general-purpose|explore|plan",
  "duration": 45000,
  "status": "success|error|timeout",
  "timestamp": 1234567890
}
```

**Common use cases:**
- Log subagent completion
- Resource cleanup
- Metrics collection
- Error handling
- Summary generation

**Blocking capability:** Can prevent subagent stop

**Frequency:** When subagents end

**Example matcher:**
```json
{
  "matcher": ".*"  // Cleanup after subagents
}
```

---

## Newer Events

Beyond the events documented above, current Claude Code hook events also include `Setup`, `UserPromptExpansion`, `PostToolBatch`, `MessageDisplay`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `WorktreeRemove`, `CwdChanged`, `PermissionDenied`, `StopFailure`, `InstructionsLoaded`, `ConfigChange`, `FileChanged`, `PostCompact`, `Elicitation`, and `ElicitationResult` (verified against code.claude.com/docs/en/hooks 2026-07-05 — see .claude/plugin-rulebook-audit-decisions.md for the audit that reconciled this list). This brings the total documented event count to 30; the dedicated sections above and the compatibility/availability matrices below don't yet cover all of them — verify matcher support and data availability for these against current docs before relying on an assumption not shown elsewhere in this file.

---

## Worktree Events

### WorktreeCreate

**When:** After a new git worktree is created.

**Non-standard behavior:** Unlike other events, `WorktreeCreate` does not use the standard allow/block decision model. The hook **must return the absolute path to the created worktree** — see `references/decision-schemas.md` for the response schema.

---

## No-Matcher-Support Events

These events always fire and do not support a `matcher` field: `Stop`, `UserPromptSubmit`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `CwdChanged`. Verify this list against current docs — new events may be added without matcher support.

---

## Hook Type / Event Compatibility Matrix

Not every hook type is valid for every event; validate the combination, not just the event name and handler type independently.

| Event | command | http | mcp_tool | prompt | agent |
|---|---|---|---|---|---|
| `PreToolUse` | Yes | Yes | Yes | Yes | Yes |
| `PostToolUse` | Yes | Yes | Yes | Yes | Yes |
| `PostToolUseFailure` | Yes | Yes | Yes | Yes | Yes |
| `UserPromptSubmit` | Yes | Yes | Yes | Yes | Yes |
| `SessionStart` | Yes | No | Yes | No | No |
| `Setup` | Yes | No | Yes | No | No |
| `SessionEnd` | Yes | Yes | Yes | No | No |
| `PreCompact` | Yes | No | Yes | No | No |
| `PermissionRequest` | Yes | Yes | Yes | Yes | No |
| `Notification` | Yes | Yes | Yes | No | No |
| `Stop` / `SubagentStop` | Yes | Yes | Yes | Yes | Yes |
| `WorktreeCreate` | Yes | No | Yes | No | No |

`SessionStart` and `Setup` support only `command` and `mcp_tool` — they fire too early in the session for `http`, `prompt`, or `agent` handlers to be reliable. Verify this matrix against current docs before relying on a type/event combination not shown here.

---

## Event Data Availability Matrix

| Event | Tool Name | Arguments | Result | Error | Context | Time |
|-------|-----------|-----------|--------|-------|---------|------|
| PreToolUse | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| PostToolUse | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| PostToolUseFailure | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ |
| UserPromptSubmit | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| SessionStart | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| SessionEnd | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| PreCompact | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| PermissionRequest | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| Notification | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| Stop | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| SubagentStart | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| SubagentStop | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |

---

## Common Event Selection Mistakes

❌ **Mistake: Using PostToolUse for validation**
```json
{
  "event": "PostToolUse",  // Tool already executed
  "matcher": "^Bash$",
  "hooks": [{
    "type": "command",
    "command": "validate.sh"
  }]
}
```
Problem: Tool already ran; can't prevent bad commands

✓ **Correct: Use PreToolUse for validation**
```json
{
  "event": "PreToolUse",  // Before execution
  "matcher": "^Bash$",
  "hooks": [{
    "type": "command",
    "command": "validate.sh"
  }]
}
```

---

❌ **Mistake: PostToolUseFailure to fix error**
```json
{
  "event": "PostToolUseFailure",
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "fix.sh"  // Can't fix the result now
  }]
}
```
Problem: Tool failed; error already happened

✓ **Correct: Use for cleanup/logging**
```json
{
  "event": "PostToolUseFailure",
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "cleanup.sh"  // Cleanup after failure
  }]
}
```

---

## Timing Diagram: Complete Event Sequence

```
┌─ Session Start
│
├─ UserPromptSubmit (user input)
│ ├─ PreToolUse: Bash (validate)
│ ├─ Bash: npm test
│ └─ PostToolUse: Bash (log)
│
├─ UserPromptSubmit (more input)
│ ├─ PreToolUse: Write (validate)
│ ├─ Write: file.js
│ └─ PostToolUse: Write (format)
│ ├─ PreToolUse: Bash (validate)
│ ├─ Bash: npm lint
│ └─ PostToolUse: Bash (log)
│
├─ PreCompact (history large)
│ └─ Pre-compact backup
│
└─ Session End (cleanup)
```

---

## Event Selection Decision Tree

**R18 note:** this block (25 content lines) sits in R18's Warning tier (`>20`, `<=30`) — advisory-only, does not reach the `>30` Critical threshold an exception would be needed to justify. It's a single coherent decision tree; splitting it would make it unreadable.

```
What do you want to do?

├─ Validate before execution?
│  └─ PreToolUse
│
├─ Process after success?
│  └─ PostToolUse
│
├─ Handle error?
│  └─ PostToolUseFailure
│
├─ Validate user input?
│  └─ UserPromptSubmit
│
├─ Initialize on session start?
│  └─ SessionStart
│
├─ Cleanup on session end?
│  └─ SessionEnd
│
├─ Backup history?
│  └─ PreCompact
│
└─ Other specialized case?
   └─ PermissionRequest/Notification/Stop/Subagent*
```
