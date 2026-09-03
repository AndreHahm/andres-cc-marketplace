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

## When NOT to Use

- Wants to see session details in the conversation, not a file/transcript output → use `session-detail`
  instead

## Step 1: Resolve the session

If no session specified, use the current one:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" current
```

Use the `path` field from the result. This resolves the live session directly (via its own session
ID), not by matching the current directory against a project name — safe even when the current
working directory doesn't match where the session actually started (e.g. a worktree created mid-session).

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

Eval suite: `evals/session-export/` — 3 scenarios, `skill-tester` Quick Workflow blind comparison. Evals
1-2 passed. Eval 3 ("export this session, including my pending task list") found a real, unresolved gap:
this skill's own workflow never documents how to include task-list data in an export — the underlying
`session_transcript.py` `export` subcommand has no task-inclusion flag, and the separate `tasks`
subcommand this plugin's shared scripts do provide is never referenced anywhere in this skill's Export
steps. Not fixed as part of this eval addition — see
`evals/session-export/workspace/iteration-2/eval-3/with_skill/grading.json` for the full analysis;
flagged for a component-owner follow-up.

**Last dated run record:** `evals/session-export/workspace/iteration-2/eval-{1,2,3}/with_skill/grading.json`,
2026-09-03. `scripts/smoke_test.py` structural self-check also passing as of the same date.

**Verify this skill activates on:**
- "export this session"
- "create a transcript of this conversation"
- "save my session history to a file"

**Verify it does NOT activate on:**
- "show session details for X" (no file output wanted) → `session-detail`

**Quality gates:**
- [ ] Step 1's `current` call needs no `--format` flag — the command always emits JSON
- [ ] `--output` examples never use a bare relative filename
