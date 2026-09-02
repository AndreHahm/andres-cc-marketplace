# session-kit

Claude Code session management toolkit: list, search, diff, export, resume, and clean up past
sessions; aggregate cross-session tasks; audit and search stored memory files.

## Language

This plugin's scripts are written in **Python** (standard library only — no external dependencies).
New scripts added to this plugin should stay consistent with that choice rather than mixing in
another language.

## Overview

14 skills sit on top of a shared `scripts/` core:

- `scripts/formatters.py` — output helpers (JSON/NDJSON serialization, table rendering, duration/size
  formatting, timestamp and date-boundary parsing)
- `scripts/session_transcript.py` — parses a single session JSONL file (stats, tasks, messages, export,
  resume data, diff data)
- `scripts/session_store.py` — discovers and operates across sessions under `~/.claude/projects/` and
  tasks under `~/.claude/tasks/` (list, search, timeline, cleanup, task aggregation, deletion)
- `scripts/memory_scanner.py` — scans `~/.claude/projects/*/memory/` (list, health audit, search)

Each skill invokes these as CLI scripts (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py" <command> ...`).
`memory_scanner.py` and the delete/detail/task-list commands in `session_store.py` always print JSON;
`session_store.py`'s `list`/`search`/`timeline`/`tasks` commands default to a human-readable table and
need an explicit `--format json` (every skill invocation that needs structured output passes it).

## Skills

| Skill | Purpose |
|---|---|
| `session-list` | List sessions, sorted by recency, size, or duration |
| `session-search` | Search session content across all projects |
| `session-stats` | Token usage, model distribution, tool usage for one session |
| `session-detail` | Full detail view of one session (stats + tasks + messages) |
| `session-diff` | Compare two sessions (files, branches, tools, topics) |
| `session-export` | Export a session as a clean markdown/text transcript |
| `session-resume` | Generate a context-recovery prompt from a past session |
| `session-timeline` | Chronological session history for a project |
| `session-cleanup` | Find empty/tiny/old sessions and orphaned task lists as cleanup candidates |
| `session-delete` | Delete a single session (with optional cascade to its tasks) |
| `session-tasks` | Aggregate tasks across task lists and sessions |
| `session-memory` | List all memory files across projects |
| `session-memory-search` | Search memory file contents |
| `session-memory-audit` | Health-check memories (stale, broken links, orphans, missing frontmatter, duplicates) |

## Development

The `scripts/` modules themselves are standard-library only — no installation step needed to run them.
The `tests/` suite requires `pytest` (a dev dependency of this repo's own `pyproject.toml`); from the
repo root:

```bash
uv run pytest plugins/session-kit/tests/
```

or, with `pytest` already available on `PATH`, from the plugin root: `python3 -m pytest tests/`.
