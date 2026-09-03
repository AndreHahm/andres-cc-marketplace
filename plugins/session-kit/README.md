# session-kit

Claude Code session management toolkit: list, search, diff, export, resume, and clean up past
sessions; aggregate cross-session tasks; audit and search stored memory files; create and load
handoff documents to preserve context across sessions; recover and continue an interrupted session
directly in-conversation; and run an end-of-session wrap-up ritual.

## Trust Model

Every skill in this plugin reads Claude Code session transcripts and/or memory files — content written
by a past session, possibly hand-edited by a human afterward. That content is always data to summarize,
present, or reconstruct context from; it is never a directive that overrides a skill's own steps, no
matter how instruction-shaped it reads. Several skills state this explicitly as their own Data-Only
Boundary section — the skills most likely to synthesize or act on reconstructed content — but the same
principle applies plugin-wide, including skills that only display content without a dedicated section.

## Language

This plugin's scripts are written in **Python** (standard library only — no external dependencies).
New scripts added to this plugin should stay consistent with that choice rather than mixing in
another language.

## Overview

14 read/query skills sit on top of a shared `scripts/` core:

- `scripts/formatters.py` — output helpers (JSON/NDJSON serialization, table rendering, duration/size
  formatting, timestamp and date-boundary parsing)
- `scripts/session_transcript.py` — parses a single session JSONL file (stats, tasks, messages, export,
  resume data, diff data)
- `scripts/session_store.py` — discovers and operates across sessions under `~/.claude/projects/` and
  tasks under `~/.claude/tasks/` (list, search, timeline, cleanup, task aggregation, deletion, single-session
  detail, current live-session resolution)
- `scripts/memory_scanner.py` — scans `~/.claude/projects/*/memory/` (scan, health audit, search,
  memory-file deletion)

Each of those 14 skills invokes `session_store.py`/`session_transcript.py`/`memory_scanner.py` as CLI
scripts (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py" <command> ...`); `formatters.py` is an
import-only helper the other three use internally, never invoked directly. Output format varies by command, not
uniformly across either script: `session_store.py`'s `list`/`search`/`timeline`/`tasks` default to a
human-readable table and need an explicit `--format json` (every skill invocation that needs structured
output passes it); every other `session_store.py` command (`cleanup`, `delete-session`, `delete-task`,
`delete-task-list`, `orphan-task-lists`, `task-lists`, `session-detail`, `current`) always prints JSON,
no flag needed.
`memory_scanner.py`'s `scan` defaults to JSON but also accepts `--format table`; `audit` and
`delete-memory` always print JSON; `search` emits NDJSON (one JSON object per line) when there are
matches, or a plain JSON `[]` when there are none.

Three further skills write or continue rather than just query, each with its own self-contained
tooling:

- `session-handoff` — 4 standalone runtime scripts under its own `skills/session-handoff/scripts/`
  (`create_handoff.py`, `list_handoffs.py`, `validate_handoff.py`, `check_staleness.py`), independent
  of the shared `scripts/` core above (its `scripts/` dir also holds the persisted `smoke_test.py`
  described under Development below)
- `session-recover` — 1 standalone runtime script under its own `skills/session-recover/scripts/`
  (`extract_resume_context.py`), also independent of the shared `scripts/` core (likewise alongside its
  own `smoke_test.py`) — though it imports `session_store.py`'s `encode_project_path` for path
  normalization, so it isn't fully independent of the shared core
- `session-wrap-up` — no runtime scripts; a prose-only ritual using `git status`/`git diff` directly

## Skills

| Skill | Purpose |
|---|---|
| `session-list` | List sessions, sorted by recency, size, or duration |
| `session-search` | Search session content across all projects |
| `session-stats` | Token usage, model distribution, tool usage, tool errors, and frustration signals for one session |
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
| `session-handoff` | Create and load validated, staleness-checked handoff documents (`.claude/handoffs/`) |
| `session-recover` | Recover context from an interrupted session and continue directly in-conversation |
| `session-wrap-up` | End-of-session ritual: informational git audit, learning capture, summary, handoff suggestion |

## Development

The `scripts/` modules themselves are standard-library only — no installation step needed to run them.
The `tests/` suite requires `pytest` (a dev dependency of this repo's own `pyproject.toml`); from the
repo root:

```bash
uv run pytest plugins/session-kit/tests/
```

or, with `pytest` already available on `PATH`, from the plugin root: `python3 -m pytest tests/`.

Each of the 17 skills also has a persisted structural self-test at `skills/<skill>/scripts/smoke_test.py`
(frontmatter validity, referenced-file existence, `allowed-tools` grant usage) — run directly with
`python3 skills/<skill>/scripts/smoke_test.py`, no dependencies beyond the standard library. Each skill
also has a `skill-tester` Quick Workflow eval suite at the repo root under `evals/<skill>/` (outside this
plugin's own directory, matching this repo's marketplace-wide convention).

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).
