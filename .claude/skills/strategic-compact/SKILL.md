---
name: strategic-compact
description: >-
  Context management intelligence for Claude Code sessions. ACTIVATE when context filling up, phase
  transitions detected, user mentions "running out of context" or "conversation too long". Suggests
  strategic compaction timing - manual compact at phase transitions beats auto-compact at arbitrary
  points.
allowed-tools: Read
---

# Strategic Compact

Intelligent context management that suggests compaction at optimal moments.

## Core Principle

**Manual compaction at strategic points > Auto-compaction at arbitrary points**

Auto-compact triggers at context limits, often mid-task. Strategic compaction preserves context through logical phases and compacts at natural transition points.

## When to Use

- Context is actively filling up in the current session (phase transitions, rising tool-call counts)
- The user mentions "running out of context" or "conversation too long"
- Deciding whether *now* is a good moment to compact/clear

## When NOT to Use

- A broader skills/CLAUDE.md/plugin/MCP footprint audit ("context warnings appear", periodic health
  checks) — that's `context-audit`'s job. This skill only fires the automatic, hook-driven
  compaction-timing suggestion when context is actively filling up in the current session; it never
  inventories what's contributing to that fullness. "Is my skills/CLAUDE.md/plugin footprint too
  heavy" → `context-audit`; "should I compact now because this session's context is filling up" →
  this skill.
- A live, in-the-moment read of the current window's percentage-full state — that's
  `context-window-analysis`'s job (see its own "Relationship to strategic-compact" section)
- A behavioral-posture question (dev/review/ship/admin) — see "Relationship to context-mode" below

## When to Suggest Compaction

### Optimal Compaction Points

| Trigger | Reason |
|---------|--------|
| Exploration complete, implementation starting | Exploration context rarely needed for coding |
| Milestone completed | Clean slate for next phase |
| Plan finalized and documented | Plan captured, context can reset |
| Debug session resolved | Debug traces clutter future work |
| Switching to unrelated task | Previous context not relevant |
| 50+ tool calls in session | Accumulated context likely stale |

### Avoid Compaction During

| Scenario | Why |
|----------|-----|
| Mid-implementation | Loses code context and decisions |
| Active debugging | Loses diagnostic information |
| Incomplete task | May need earlier context |
| Code review in progress | Loses review thread |

## Compaction Options

### /compact (Quick)
- Built-in summarization
- Frees context immediately
- May lose some nuance
- `context-kit` automatically captures the active plan's status/current-task (if
  `CONTEXT_KIT_PLANS_DIR` is configured — see the plugin README) before compaction and re-injects it
  after, via its own `pre-compact.py`/`post-compact-restore.py` hooks. This is a lightweight,
  automatic capture, not a full handoff document.

### session-kit's session-handoff (Recommended for complex work, if session-kit is installed)
For anything richer than the automatic plan-status capture above — a full record of decisions made,
what worked/didn't, and next steps — the `session-kit` plugin's `session-handoff` skill is the
recommended pairing, if installed. It's model-invoked, not a slash command: trigger phrases like
"create handoff", "save state", or "I need to pause" cause it to write a validated,
staleness-checked handoff document to `.claude/handoffs/` (not `HANDOFF.md`). A fresh agent then
loads it back with `session-kit`'s own resume trigger. This is an optional pairing —
`context-kit` has no hard dependency on `session-kit` being installed, and its own automatic
capture/restore above works independently.

### /clear (Fresh start)
- Complete reset
- Best when switching tasks entirely

## Relationship to context-mode

`context-kit`'s `context-mode` skill governs a different axis — *what behavioral posture to operate in*
(dev/review/ship/admin), not *when to compact*. The two intersect only at a "hard switch": when
`context-mode` detects a genuinely heavy mode transition (or context is already large), it defers to
this skill's own "Switching to unrelated task" trigger above (suggest `/compact`/`/clear`) rather than
duplicating compaction-timing logic itself. Use `context-mode` when the question is "how cautious/
verbose should I be right now"; use this skill when the question is "should I compact or clear now."

## Relationship to context-engineering

`context-engineering` owns the manually-applied Write/Select/Compress/Isolate conceptual framework —
planning what to persist/retrieve/compress before or during a task. This skill only supplies the
automatic, hook-driven layer that detects a good compaction *moment* and suggests acting on it; it does
not decide *what* to persist or how to structure a context budget. "How should I structure/budget
context for this task" → `context-engineering`; "is now a good moment to compact" → this skill.

## Relationship to context-window-analysis

For a manually-triggered, point-in-time read of the current window's actual health (percentage full,
composition breakdown) rather than an automatic nudge, see `context-window-analysis` — this skill only
fires the automatic hook-driven suggestion; it doesn't answer "how full is my context right now" on
demand.

## Phase Detection Patterns

Detect phase transitions by monitoring:

```
EXPLORATION → IMPLEMENTATION
- Many Read/Grep/Glob calls → Edit/Write calls starting
- Questions answered → Code being written

IMPLEMENTATION → TESTING
- Edit/Write heavy → Bash(test) calls
- Feature code done → Verification starting

DEBUGGING → RESOLUTION
- Error investigation → Fix confirmed working
- Multiple attempts → Success achieved
```

## Automatic Behavior

This skill works with hooks that:

1. **Track tool usage** - Counts tool calls per session
2. **Detect phase transitions** - Monitors tool patterns
3. **Inject suggestions** - Adds context-aware recommendations
4. **Capture and restore state across compaction** - See Integration below

## Usage Patterns

### After Exploration
```text
[Hook detects: 10+ Read/Grep calls, first Edit coming]
→ Suggest: "Exploration complete. Consider /compact before implementation."
```

### After Milestone
```text
[Hook detects: Tests passing after implementation]
→ Suggest: "Milestone reached. Good time for /compact or session-kit's session-handoff."
```

### Context Threshold
```text
[Hook detects: 50 tool calls reached]
→ Suggest: "Session has 50+ tool calls. Consider /compact if context feels stale."
```

## Integration

Works automatically via plugin hooks. No manual configuration needed for the default behavior (see
the plugin README for the optional `CONTEXT_KIT_PLANS_DIR`/`CONTEXT_KIT_SESSION_LOGS_DIR` env vars).

**State and side effects (disclosed, found by security-reviewer, 2026-09-17):** these hooks write to
and read from `~/.claude/strategic-compact/` — per-session tool-call counters, thresholds, and
generated suggestion text only, nothing else. `compact-session-init.sh` deletes `session-*` files
older than 24 hours from that directory on every session start (`find ... -mtime +1 -delete`), and a
stale-lock bust (`rm -rf`) can remove a lock directory under the same path. On macOS/Linux, a detected
suggestion can also spawn a desktop-notification process (`osascript`/`notify-send`) — best-effort,
fails silently if unavailable.

The full hook wiring, by event:

- **`SessionStart`** — `compact-session-init.sh` (always) initializes tool-call tracking for the new
  session. `post-compact-restore.py` (matcher `compact|resume`) reads back whatever
  `pre-compact.py` captured before the compaction that just happened, and re-injects it via
  `additionalContext` — the active plan's status/current-task, if `CONTEXT_KIT_PLANS_DIR` is
  configured.
- **`PreToolUse`** — `compact-track-and-suggest.sh` (matcher `.*`, every tool call) tracks
  exploration-vs-implementation phase and detects threshold/phase-transition suggestions. This hook
  runs **`async`** — measured at ~550-750ms per invocation on Windows (bash-subprocess spawn
  overhead), well above `PreToolUse`'s documented budget, so it no longer blocks the tool call it's
  attached to or synchronously injects `additionalContext`. It still writes any detected suggestion to
  a pending-suggestion file synchronously within its own (backgrounded) run — the `Stop` hook below is
  what actually delivers it to the user, not this hook's own return value.
- **`PostToolUse`** — `compact-milestone-detector.sh` (matcher `^Bash$`) detects milestones (tests
  passing, commits, builds, deploys) from the command that just ran. `context-monitor.py` (matcher
  `.*`, every tool call) separately estimates overall context-window usage (a coarse percentage,
  from transcript size or a tool-call-count fallback) and nudges at 40/55/65/80/90% thresholds — its
  own throttling (60s between checks below the warning threshold, once per threshold above it) gates
  the *emit*, not the interpreter launch itself, and matters more once scoped this broadly rather
  than only to `Bash|Agent|Task`: without it, a read-heavy session (e.g. `Read`/`Grep`/`Glob`-only)
  would never get a context-usage nudge at all. Unlike `compact-track-and-suggest.sh` (measured at
  550-750ms on Windows, which required `async: true`), this hook's own real per-invocation cost was
  directly benchmarked (10 runs, this platform): **83-97ms, mean ~88ms** — an order of magnitude
  cheaper, well within `PostToolUse`'s synchronous budget, so it stays synchronous by measurement,
  not by assumption. `context-window-analysis`'s own Context Health Thresholds table mirrors these
  same constants — re-check that table too whenever `context-monitor.py`'s thresholds change here.
- **`PreCompact`** — `compact-instructions.sh` writes best-effort stderr/`systemMessage` guidance on
  what to preserve through compaction; this is a nudge, not a guarantee (stderr is verbose-mode-only
  by default). `PreCompact` **does** support `hookSpecificOutput.additionalContext` per Claude Code's
  own docs — `compact-instructions.sh` simply doesn't use it (an implementation choice, not a contract
  limitation; see the script's own comment). The plugin's actual state-preservation guarantee is
  `pre-compact.py`, which captures the active plan's state (see `SessionStart` above) for
  `post-compact-restore.py` to restore afterward via `additionalContext` on `SessionStart`.
- **`Stop`** — `compact-stop-check.sh` checks for a pending suggestion that hasn't reached the user
  yet and **blocks the stop once** (`{"decision": "block", ...}`) when one exists, guarded by
  `stop_hook_active` so it never re-triggers itself on the resulting continuation. This is the
  suggestion's actual delivery mechanism (see the `PreToolUse` note above), though not an absolute
  guarantee: since `compact-track-and-suggest.sh` now runs async, its background write of the
  pending-suggestion file could in principle still be in flight when `Stop` fires immediately after
  (e.g. a suggestion detected on the very last tool call of a turn). In practice the write completes
  well within the hook's own timeout, so this is a narrow, disclosed edge case, not a routine failure
  mode.

`compact-track-and-suggest.sh` and `compact-milestone-detector.sh` share one tracking file per
session; a `mkdir`-based lock (bounded retries, fail-open, with stale-lock detection for a
crashed/killed prior invocation) guards every read-modify-write against the two hooks racing each
other when Claude Code dispatches multiple tool calls in close succession.

## Testing & Validation

**No `evals/strategic-compact/evals.json` — by design, not omission.** This skill's actual behavior
is hook-driven automation (5 Bash scripts + 3 shared Python hooks, all wired via `hooks/hooks.json`),
not model-invoked guidance a `skill-tester` blind-comparison eval measures — there's no "with skill
vs. without skill" prompt-completion difference to compare, since the skill never depends on the
model reading and following its own body text to act; the hooks fire deterministically regardless.
The meaningful test surface is the hook scripts' own input/output contracts, verified directly
(stdin → stdout/exit-code, against realistic and adversarial JSON payloads) rather than via an
LLM-judged eval — see `hook-development/scripts/test-hook.sh`. The checklist below documents that
direct-verification surface, and the persisted `scripts/smoke_test.py` exercises
`compact-milestone-detector.sh`, `compact-stop-check.sh`, and `compact-session-init.sh` directly
against this same stdin/stdout contract, plus imports and cross-checks all 3 shared Python hooks
(`context-monitor.py`, `pre-compact.py`, `post-compact-restore.py`).

**Last dated run record:** `scripts/smoke_test.py` — 14/14 checks passing as of 2026-09-17.

**Verify this skill's hooks activate on:**
- A session starting (`SessionStart`, any source) — tool-call tracking initializes; a `compact`/
  `resume` source additionally triggers the restore hook.
- Any tool call — `PreToolUse` tracking fires on every call (matcher `.*`); `context-monitor.py`
  additionally fires on every successful tool call (`PostToolUse`, matcher `.*`).
- A `Bash` command matching a known test/build/commit/deploy pattern (e.g. `pytest`, `git commit`,
  `npm run build`) — `compact-milestone-detector.sh` fires on `PostToolUse`.
- A compaction event (manual `/compact` or automatic) — both `PreCompact` hooks fire; the matching
  `SessionStart` restore hook fires on the following turn.

**Verify this skill's hooks do NOT fire a false positive on:**
- A `Stop` event where `stop_hook_active` is already `true` — must exit cleanly, never re-block.
- A Bash command containing an unrelated word that happens to substring-match a milestone-detection
  pattern (e.g. `majestic`, `cmake build`) — `compact-milestone-detector.sh`'s test/build/deploy
  patterns use `grep -w` (whole-word matching), not `\b...\b`: BSD grep (macOS's default
  `/usr/bin/grep`) doesn't support the GNU-only `\b` escape at all, so `-w` is the portable choice
  that still stops these from producing a false milestone suggestion.

**Note on test/build milestone detection:** `compact-milestone-detector.sh` is wired to `PostToolUse`
only (not `PostToolUseFailure`) — this event fires only after a tool call completes successfully, so a
failing Bash test/build command never reaches this hook at all, and `test_pass`/`build` milestone
detection needs no separate success check of its own. An earlier version gated these two milestone
types on `.tool_response.success`, a field that doesn't exist on a real Bash `PostToolUse` payload —
that check was always false in practice, silently disabling both milestone types entirely; it was
removed rather than fixed to check a real field, since `PostToolUse` already guarantees success.

**Quality gates:**
- [ ] A session with 50+ tool calls produces exactly one threshold suggestion per configured
      threshold (`T1`/`T2`/`T3`), not a repeated suggestion on every call past the threshold.
- [ ] A successful `pytest`/`npm test`/etc. command produces a `test_pass` milestone suggestion (once
      per 5-minute window); a successful `npm run build`/`cargo build`/etc. command produces a `build`
      milestone suggestion the same way.
- [ ] A compaction event followed by a `SessionStart` with `source=compact` restores the
      previously-captured plan state (when `CONTEXT_KIT_PLANS_DIR` is configured) via
      `additionalContext`, with no crash if no state was ever captured.
- [ ] An env var like `STRATEGIC_COMPACT_T1` set to a non-numeric or malicious value falls back to
      its default rather than corrupting the tracking file or executing as shell code.
