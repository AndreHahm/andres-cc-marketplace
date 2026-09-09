---
name: strategic-compact
description: >-
  Context management intelligence for Claude Code sessions. ACTIVATE when context filling up, phase
  transitions detected, user mentions "running out of context" or "conversation too long". Suggests
  strategic compaction timing - manual compact at phase transitions beats auto-compact at arbitrary
  points.
---

# Strategic Compact

Intelligent context management that suggests compaction at optimal moments.

## Core Principle

**Manual compaction at strategic points > Auto-compaction at arbitrary points**

Auto-compact triggers at context limits, often mid-task. Strategic compaction preserves context through logical phases and compacts at natural transition points.

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
the plugin README for the optional `CONTEXT_KIT_PLANS_DIR`/`CONTEXT_KIT_SESSION_LOGS_DIR`/
`CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT` env vars). The full hook wiring, by event:

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
- **`PostToolUse`** — `compact-milestone-detector.sh` (matcher `Bash`) detects milestones (tests
  passing, commits, builds, deploys) from the command that just ran. `context-monitor.py` (matcher
  `Bash|Agent|Task`) separately estimates overall context-window usage (a coarse percentage, from
  transcript size or a tool-call-count fallback) and nudges at 40/55/65/80/90% thresholds.
- **`PreCompact`** — `compact-instructions.sh` writes stderr guidance on what to preserve through
  compaction. `pre-compact.py` captures the active plan's state (see `SessionStart` above) for
  `post-compact-restore.py` to restore afterward.
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

**A second, opt-in blocking path exists.** `pre-compact.py` can also block compaction once, when
`CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT=1` is set and the active plan's status is still DRAFT — off by
default, since blocking the harness's automatic compaction can strand a user at the context ceiling.
It blocks at most once per DRAFT plan.

## Testing & Validation

**No `evals/strategic-compact/evals.json` — by design, not omission.** This skill's actual behavior
is hook-driven automation (5 Bash scripts + 3 shared Python hooks, all wired via `hooks/hooks.json`),
not model-invoked guidance a `skill-tester` blind-comparison eval measures — there's no "with skill
vs. without skill" prompt-completion difference to compare, since the skill never depends on the
model reading and following its own body text to act; the hooks fire deterministically regardless.
The meaningful test surface is the hook scripts' own input/output contracts, verified directly
(stdin → stdout/exit-code, against realistic and adversarial JSON payloads) rather than via an
LLM-judged eval — see `hook-development/scripts/test-hook.sh` and this plugin's own Build-time
verification record. The checklist below documents that direct-verification surface.

**Verify this skill's hooks activate on:**
- A session starting (`SessionStart`, any source) — tool-call tracking initializes; a `compact`/
  `resume` source additionally triggers the restore hook.
- Any tool call — `PreToolUse` tracking fires on every call (matcher `.*`); `context-monitor.py`
  additionally fires on `Bash`/`Agent`/`Task` (`PostToolUse`).
- A `Bash` command matching a known test/build/commit/deploy pattern (e.g. `pytest`, `git commit`,
  `npm run build`) — `compact-milestone-detector.sh` fires on `PostToolUse`.
- A compaction event (manual `/compact` or automatic) — both `PreCompact` hooks fire; the matching
  `SessionStart` restore hook fires on the following turn.

**Verify this skill's hooks do NOT fire a false positive on:**
- A failing test or failing build command — `compact-milestone-detector.sh` gates `test_pass`/
  `build` milestone detection on `tool_response.success` being `true`; a failing command must not
  produce a "milestone reached" suggestion.
- A `Stop` event where `stop_hook_active` is already `true` — must exit cleanly, never re-block.

**Pass criteria:**
- [ ] A session with 50+ tool calls produces exactly one threshold suggestion per configured
      threshold (`T1`/`T2`/`T3`), not a repeated suggestion on every call past the threshold.
- [ ] A `pytest`/`npm test`/etc. command with `tool_response.success: false` produces no
      "Tests passed" suggestion.
- [ ] A compaction event followed by a `SessionStart` with `source=compact` restores the
      previously-captured plan state (when `CONTEXT_KIT_PLANS_DIR` is configured) via
      `additionalContext`, with no crash if no state was ever captured.
- [ ] An env var like `STRATEGIC_COMPACT_T1` set to a non-numeric or malicious value falls back to
      its default rather than corrupting the tracking file or executing as shell code.
