# context-kit

Context-window management and behavioral-mode switching for Claude Code sessions — an automatic,
hook-driven layer, 5 model-invoked skills covering footprint auditing, failure diagnosis, the
Write/Select/Compress/Isolate framework, targeted retrieval, and live context-window health, plus a
`context-mode` skill that switches operating posture (dev/review/ship/admin) mid-session.

`context-kit` tracks tool-call and context usage through a session, suggests strategic compaction at
natural phase transitions and milestones (rather than letting auto-compact fire at an arbitrary point),
and captures/restores key session state (active plan, current task) across a compaction event. Beyond the
automatic layer, it also ships skills for auditing a project's own skill/CLAUDE.md/plugin footprint,
diagnosing active context-degradation patterns, planning context budgets, choosing targeted retrieval
strategies (@ mentions vs. search), and checking the current window's live health.

This is a multi-wave build. Waves shipped so far:

**Wave 1 — automatic layer:**

- **`strategic-compact`** — a skill plus 5 hook-driven shell scripts that track tool-call phase
  (exploration → implementation), detect milestones (tests passing, a commit, a build, a deploy), and
  suggest `/compact` at good stopping points. One of the hooks (`Stop`) blocks once to make sure a
  pending suggestion actually reaches the user before the turn ends.
- **3 additional Python hooks**, wired via the same `hooks/hooks.json`: a `PostToolUse` context-usage
  monitor (coarse percentage estimate, throttled threshold nudges), a `PreCompact` state-capture hook,
  and a `SessionStart` (`source=compact` or `resume`) state-restore hook.

**Wave 2 — 5 model-invoked skills:**

- **`context-audit`** — audits skills/CLAUDE.md/plugin/MCP footprint and scores it (A-F). Defers session
  token/model/tool-usage analysis and memory-content health to `session-kit`'s `session-stats`/
  `session-memory-audit` (if installed) rather than duplicating them.
- **`context-degradation`** — diagnoses active context failures (lost-in-middle, poisoning, distraction,
  confusion, clash) and maps each to the `context-engineering` operation that mitigates it.
- **`context-engineering`** — the canonical Write/Select/Compress/Isolate framework for planning a
  context budget, compaction strategy, and partitioning approach.
- **`context-optimization`** — @ mentions and semantic search for targeted, precise retrieval; one
  concrete instance of `context-engineering`'s "Select" operation.
- **`context-window-analysis`** — a live, in-the-moment check of the current context window's health and
  remediation options, narrower in scope than `context-audit`'s broader footprint audit.

**Wave 3 — behavioral-mode switching:**

- **`context-mode`** — switches operating posture (dev/review/ship/admin, first-pass scope) mid-session
  without needing a fresh session. A `UserPromptSubmit` hook (`scripts/detect_mode.py`)
  substring-matches the submitted prompt against `triggers.json`'s phrase lists and injects a
  `[Context-Mode candidate(s): ...]` tag into context via `additionalContext`; the skill activates only
  off that hook-delivered tag for the current turn — never from the same string merely appearing in
  file, tool-output, or fetched content — or an explicit user request. `research`/`plan`/`draft`/`doc`
  modes are deferred to a later pass; too little real-transcript evidence to build detection against
  yet. **The 4 mode profiles are written specifically for this marketplace's own toolset** (git-kit,
  plugin-devkit) rather than generic guidance — installing `context-kit` standalone in an unrelated
  repo will surface references to tools that don't exist there; see `context-mode`'s own SKILL.md for
  the full disclosure.

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

`strategic-compact`'s hooks also write to `~/.claude/strategic-compact/` (per-session tool-call
counters, thresholds, and generated suggestion text only) and delete `session-*` files older than 24
hours from that directory on every session start. On macOS/Linux, a detected suggestion can also
trigger a best-effort desktop notification (`osascript`/`notify-send`).

## Declared plugin language

Python. New scripts added to this plugin should be Python going forward, per this marketplace's
`require-declared-plugin-language.md` convention.

**Disclosed exceptions:**
- `strategic-compact`'s 5 hook scripts (`hooks/scripts/*.sh`) are Bash. They were an already-written,
  working, non-trivial component pulled in from a prior design/review pass at this plugin's creation, and
  were not rewritten to Python as part of this build — rewriting working hook logic purely to match a
  naming convention wasn't worth the risk.
- `context-audit`'s `scripts/audit-context.sh` (Wave 2) is also Bash. It's a static-inventory scanner
  (`find`/`wc`/`jq`-based) carried over unchanged from the plugin's own source draft; a rewrite to Python
  wasn't part of Wave 2's scope, which fixed the script's content (dropping a duplicated session-analysis
  mode, a `--top` arithmetic bug) without changing its language.

Both are disclosed, intentional exceptions, not oversights.

## Pairing with session-kit

`context-kit`'s automatic capture/restore (Wave 1) and `session-kit`'s user-invoked
`session-handoff`/`session-wrap-up` skills both address "preserve context across a boundary," via
different mechanisms (automatic hooks vs. explicit user action) and different storage
(`~/.claude/sessions/<hash>/` vs. `.claude/handoffs/`). Both work independently — `session-kit` ships no
hooks, so there's no mechanical collision. Whether `context-kit`'s automatic layer should eventually hand
off to `session-kit`'s handoff format is an open cross-plugin design question for a future pass, not
resolved in this wave.

Wave 2's skills extend this pairing, each independently (conditional on `session-kit` being installed —
`context-kit` has no hard dependency on it): `context-audit` defers session-token/model/tool-usage
analysis and memory-content health to `session-kit`'s `session-stats`/`session-memory-audit`, rather than
duplicating them; `context-window-analysis` separately offers `session-kit`'s `session-handoff` as one
optional escalation path when context is critical. Neither skill duplicates the other's session-kit
integration.

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).
