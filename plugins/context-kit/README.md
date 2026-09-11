# context-kit

Automatic, hook-driven context-window management for Claude Code sessions.

`context-kit` tracks tool-call and context usage through a session, suggests strategic compaction at
natural phase transitions and milestones (rather than letting auto-compact fire at an arbitrary point),
and captures/restores key session state (active plan, current task) across a compaction event.

This is Wave 1 of a multi-wave build. This wave ships:

- **`strategic-compact`** — a skill plus 5 hook-driven shell scripts that track tool-call phase
  (exploration → implementation), detect milestones (tests passing, a commit, a build, a deploy), and
  suggest `/compact` at good stopping points. One of the hooks (`Stop`) blocks once to make sure a
  pending suggestion actually reaches the user before the turn ends.
- **3 additional Python hooks**, wired via the same `hooks/hooks.json`: a `PostToolUse` context-usage
  monitor (coarse percentage estimate, throttled threshold nudges), a `PreCompact` state-capture hook,
  and a `SessionStart` (`source=compact`) state-restore hook.

Later waves add more context-management skills (`context-audit`, `context-degradation`,
`context-engineering`, `context-optimization`, `context-window-analyze`) and a `context-mode` skill for
task-phase-aware behavioral switching.

## Installation

Install via this marketplace, or point Claude Code at this plugin directory directly for local
development:

```bash
claude --plugin-dir /path/to/andres-cc-marketplace/plugins/context-kit
```

Once installed, `context-kit` works automatically — no manual invocation. A typical suggestion looks
like:

```
[StrategicCompact] 50 tool calls reached. If context feels cluttered, this is a good checkpoint for /compact.
```

## Configuration

All configuration is via environment variables — no config file. Every variable is optional; unset
values fall back to safe, no-op-if-unconfigured defaults:

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDE_CONTEXT_WINDOW_TOKENS` | `200000` | Context-window size used to estimate usage percentage in `context-monitor.py` |
| `CLAUDE_CONTEXT_MAX_TOOL_CALLS` | `400` | Fallback tool-call-count proxy when a transcript file isn't available |
| `STRATEGIC_COMPACT_T1` / `_T2` / `_T3` | `50` / `75` / `100` | Tool-call-count thresholds for `strategic-compact`'s suggestions |
| `STRATEGIC_COMPACT_TIME` | `1800` (30 min) | Time-based suggestion threshold, in seconds |
| `CONTEXT_KIT_PLANS_DIR` | unset (feature inert) | Optional plan-file directory (absolute, or relative to `$CLAUDE_PROJECT_DIR`) `pre-compact.py`/`post-compact-restore.py` scan for an active plan's status/current-task |
| `CONTEXT_KIT_SESSION_LOGS_DIR` | unset (feature inert) | Optional session-log directory (same path rules) for a compaction note and the most-recent-log pointer surfaced on restore |

`CONTEXT_KIT_PLANS_DIR`/`CONTEXT_KIT_SESSION_LOGS_DIR` have no invented universal default — this plugin
doesn't assume any particular project's plan/log convention. Set them if your project keeps plan/log
files somewhere `context-kit` should read.

## Declared plugin language

Python. New scripts added to this plugin should be Python going forward, per this marketplace's
`require-declared-plugin-language.md` convention.

**Disclosed exception:** `strategic-compact`'s 5 hook scripts (`hooks/scripts/*.sh`) are Bash. They were
an already-written, working, non-trivial component pulled in from a prior design/review pass at this
plugin's creation, and were not rewritten to Python as part of this build — rewriting working hook logic
purely to match a naming convention wasn't worth the risk. They're a disclosed, intentional exception,
not an oversight.

## Pairing with session-kit

`context-kit`'s automatic capture/restore (this wave) and `session-kit`'s user-invoked
`session-handoff`/`session-wrap-up` skills both address "preserve context across a boundary," via
different mechanisms (automatic hooks vs. explicit user action) and different storage
(`~/.claude/sessions/<hash>/` vs. `.claude/handoffs/`). Both work independently — `session-kit` ships no
hooks, so there's no mechanical collision. Whether `context-kit`'s automatic layer should eventually hand
off to `session-kit`'s handoff format is an open cross-plugin design question for a future pass, not
resolved in this wave.

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).
