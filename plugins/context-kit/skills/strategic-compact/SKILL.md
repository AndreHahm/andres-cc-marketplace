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

## Quick Start

This skill isn't invoked directly — its hooks fire automatically. What you'll actually see:
a `[Strategic Compact]`-style suggestion after a phase transition, a milestone, or a configured
tool-call threshold. Act on it by running `/compact` (or `/clear` for an unrelated task), or ignore
it if you're mid-task — see "Avoid Compaction During" below.

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
  `context-window-analysis`'s job (see its own "When NOT to Use" section, which states this same
  distinction reciprocally)
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
| Configured tool-call threshold reached (T1/T2/T3, default 50/75/100, overridable via `STRATEGIC_COMPACT_T1`/`_T2`/`_T3` — see the plugin README) | Accumulated context likely stale |
| Context-mode switched (added 2026-09-21 — any confidently-detected dev/review/ship/admin change, not just a "hard" one; see "Context-mode switch events" below) | The prior mode's context is often no longer relevant to the new posture |
| A known `heavy_operation` skill is about to start (added 2026-09-21 — e.g. `plugin-auditor`, `plugin-lifecycle-downstream`; see "Skill-category events" below) | A nudge if you haven't compacted recently (informational only — the call itself is already committed to run regardless) |
| A known `session_analysis` skill is about to start (added 2026-09-21 — e.g. `starting-an-analysis`, `analyzing-plugin-components`; see "Skill-category events" below) | A nudge if you haven't compacted recently (informational only — the call itself is already committed to run regardless) |

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
(dev/review/ship/admin), not *when to compact*. As of 2026-09-21, the two intersect on **every**
confidently-detected mode switch, not only a "hard switch" — see "Context-mode switch events" below for
the full detection/throttling detail; `context-mode`'s own `detect_mode.py` writes a suggestion into this
skill's delivery mechanism on any single-candidate mode change. A "hard switch" (a genuinely heavy
transition, or context already large) remains a special case within that broader set — it also
independently matches this skill's own "Switching to unrelated task" trigger above, so the two signals
can coincide on the same turn rather than compete. Use `context-mode` when the question is "how cautious/
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

## Context-mode switch events (added 2026-09-21)

`context-mode`'s own `scripts/detect_mode.py` (a `UserPromptSubmit` hook) already runs every turn to
detect dev/review/ship/admin candidates. It's now also the detector for this event: on a turn where
**exactly one** candidate mode is confidently detected and it differs from the last confidently-detected
mode, it writes a `[StrategicCompact] Context-mode switched (<old> -> <new>)` suggestion, throttled to
once per 5 minutes (matching the milestone-suggestion cooldown). A turn with zero or multiple candidates
is too ambiguous to treat as a mode reading and leaves the tracked mode unchanged — it can never itself
look like a false "switch." This broadens the original, narrower design (only a "hard switch" — see
this skill's own "Relationship to context-mode" section above — deferred to this skill) to
**every** confidently-detected switch, since even an ordinary posture change can leave stale context
behind. See `context-mode`'s own SKILL.md ("Mid-session switching mechanics" and its "State and side
effects" note) for the full detection/state-file detail — this skill only owns the delivery mechanism
(the shared `pending-<hash>` file, relayed by `compact-stop-check.sh` below), not the detection logic
itself, which lives in `context-mode`'s own script.

## Skill-category events (added 2026-09-21)

A new hook, `compact-skill-category-detector.sh`, fires on `PreToolUse` for a Skill() call about to
start, classifying the invoked skill's name against two category lists and suggesting `/compact` if
it's been a while, with no cooldown (each Skill() invocation is a fresh, bounded event worth its own
suggestion, not a potentially-noisy repeated command the way a Bash milestone pattern can be).

**`PreToolUse`-only by design — there is no `PostToolUse` "finish" counterpart.** An earlier version of
this hook also fired on `PostToolUse`, claiming the skill had "finished." That claim was false almost
every time it fired: a Skill() call's own `PostToolUse` event fires once the skill's instructions have
loaded into the conversation as a message, not once the model has actually finished executing the
workflow those instructions describe (see `skill-development`'s `references/design-patterns.md`, "Skill
content lifecycle") — there is no hook event in Claude Code that fires on real workflow completion for
a foreground skill. Rather than keep a message that reads as factually wrong most of the time, the
finish phase was dropped entirely (found by Codex's automated PR review, 2026-09-21, against PR #368).

**Disclosed limitation — the remaining `start` suggestion is advisory, not a guarantee.** `PreToolUse`
fires before the Skill() call executes, but by the time it fires the decision to invoke that skill has
already been made — the call is about to run regardless of what the hook suggests. A `/compact` run in
response to the suggestion can't retroactively change the context the about-to-run skill will operate
against; it can only get the session into a better state for whatever comes *after* this particular
call. The wording below reflects this: it nudges toward compacting soon if it hasn't happened recently,
rather than claiming to precede or gate the specific Skill() call it fired on.

- **`heavy_operation`** — a skill that does multi-agent fan-out or a whole-plugin/whole-repo
  re-verification (e.g. `plugin-auditor`, `plugin-lifecycle-downstream`, `running-a-full-retrospective`).
- **`session_analysis`** — an `analysis-kit`-style skill that reads/analyzes session transcripts (e.g.
  `analyzing-sessions`, `starting-an-analysis`).

**Overlap priority:** a skill matching both lists resolves to `heavy_operation` (the higher-priority,
more resource-costly classification) — an analogous higher-priority-wins pattern to
`compact-milestone-detector.sh`'s own deploy>build>commit>test_pass chained-command resolution, though not
the identical mechanism: that script resolves multiple distinct events occurring together in one chained
command (a temporal "later wins"), while this is a static membership tiebreak between two config lists
for one skill name (no chaining involved). `analyzing-sessions` is a deliberate example of this: listed
under `heavy_operation`, not `session_analysis`, because its own multi-agent SWOT/self-critique dispatch
is itself heavy.

**Category-list configuration**, per `.claude/rules/ask-before-config-decisions.md`: git-tracked
defaults live at `hooks/context-kit.settings.json` (deliberately inside `hooks/`, a real plugin-mirror
component directory, rather than at the plugin root — see issue #316: a plugin-root-level file is
silently never mirrored into this repo's own `.claude/` dogfooding checkout, and this file would
otherwise inherit that exact gap). An optional, gitignored `.claude/context-kit.local.json` at the
installing project's own root **additively** extends both lists (adds project-specific skills, never
replaces the shipped defaults) — resolved via `${CLAUDE_PROJECT_DIR}`, matching this repo's own
`divergence_exceptions` precedent for why that variable, not `${CLAUDE_PLUGIN_ROOT}`, is correct for a
project-local file. Requires `jq`: classification needs real JSON array membership, not a regex
approximation, so this hook fails open (silently, no suggestion) when `jq` is unavailable rather than
attempt one. Each file is parsed independently before merging — a malformed local override file falls
back to the shipped defaults alone rather than disabling classification entirely (found by Codex +
CodeRabbit's automated PR reviews, 2026-09-21, against PR #368: the original combined-parse approach let
a broken local file take the shipped defaults down with it too).

**A `workflow_skill` category (skills that orchestrate other components, per
`plugin-rulebook-enforcement.md`'s own existing definition) was considered and deliberately dropped**,
not shipped even as an opt-in toggle: once the genuinely heavy workflow skills were classified under
`heavy_operation` by the overlap-priority rule above, what remained in a separate `workflow_skill`
category was exclusively lightweight coordination skills (e.g. `pr-to-linear`, `open-item-management`)
without enough distinct signal to justify their own dedicated compaction nudge.

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
[Hook detects: T1 (default 50) tool calls reached]
→ Suggest: "Session has 50+ tool calls. Consider /compact if context feels stale."
```

## Integration

Works automatically via plugin hooks. No manual configuration needed for the default behavior (see
the plugin README for the optional `CONTEXT_KIT_PLANS_DIR`/`CONTEXT_KIT_SESSION_LOGS_DIR` env vars).

See `references/state-and-side-effects.md` for the full disclosure of what these hooks write to disk,
where, and the data-only boundary governing state content read back — required reading before touching
any of this plugin's tracking-file logic.

See `references/hook-wiring.md` for this skill's own hook wiring by event (`SessionStart` through
`Stop`, including the `^Skill$`-matcher entry added 2026-09-21), the shared-tracking-file
locking convention, and the Windows PowerShell milestone-matcher fix.

**The `pending-<hash>` file is a queue, not a single slot (updated 2026-09-21).** Two writers
(`compact-track-and-suggest.sh`, `context-mode`'s `detect_mode.py`) can each append a suggestion to
this same file before `compact-stop-check.sh` drains it — a plain overwrite would let a later write
silently clobber an earlier, not-yet-delivered one (found by CodeRabbit's automated PR review,
2026-09-21, against PR #368: adding `detect_mode.py` as a second writer to a file only one hook
previously wrote to made this a real, no-longer-rare collision risk). Both writers now append
(`>>`/open-in-append-mode) rather than overwrite; `compact-stop-check.sh` reads every line, validates
each independently against the same strict single-line shape the original single-suggestion check
used, and delivers all still-valid lines in one `decision: block`, capped at 20 delivered suggestions
as a defense-in-depth bound (not a realistic accumulation scenario in practice).

## Reference Guide

| Resource | Purpose |
|---|---|
| `scripts/smoke_test.py` | This skill's own persisted hook-contract regression test |
| `references/hook-wiring.md` | Full hook wiring by event, the shared-tracking-file lock, and the Windows PowerShell milestone-matcher fix |
| `references/state-and-side-effects.md` | What every hook writes to disk, where, and the data-only boundary |
| `hooks/scripts/compact-session-init.sh` | `SessionStart` — initializes per-session tool-call tracking |
| `hooks/scripts/compact-track-and-suggest.sh` | `PreToolUse` — counts tool calls, detects phase transitions, generates suggestions |
| `hooks/scripts/compact-milestone-detector.sh` | `PostToolUse` — detects test/build/commit/deploy milestones |
| `hooks/scripts/compact-skill-category-detector.sh` | `PreToolUse` (matcher `^Skill$`) — detects a known `heavy_operation`/`session_analysis` skill about to start |
| `hooks/context-kit.settings.json` | Git-tracked default `heavy_operation`/`session_analysis` skill-category lists |
| `hooks/scripts/compact-instructions.sh` | `PreCompact` — emits compaction guidance |
| `hooks/scripts/compact-stop-check.sh` | `Stop` — delivers a pending suggestion, if any |
| `scripts/pre-compact.py` | `PreCompact` — captures plan state and appends a session-log note (if configured) |
| `scripts/post-compact-restore.py` | `SessionStart` (matcher `compact\|resume`) — restores captured plan state |
| `scripts/context-monitor.py` | `PostToolUse` — live context-window health, shared with `context-window-analysis` |
| `context-mode`'s `scripts/detect_mode.py` | `UserPromptSubmit` (owned by `context-mode`) — as of 2026-09-21, also detects a confidently-detected mode switch and writes into this skill's own delivery mechanism |

## Testing & Validation

**`evals/strategic-compact/evals.json` exists, but doesn't exercise this skill's actual hook-driven
behavior — by design, not omission** (fixed 2026-09-21: this section previously said the file didn't
exist at all, which contradicted the recorded-run sentence two sentences later; found by CodeRabbit's
automated PR review against PR #368). This skill's actual behavior is hook-driven automation (6 Bash
scripts + 3 shared Python hooks, all wired via `hooks/hooks.json`, plus `context-mode`'s own
`detect_mode.py` as of 2026-09-21), not model-invoked guidance a `skill-tester` blind-comparison eval
measures — there's no "with skill vs. without skill" prompt-completion difference to compare, since the
skill never depends on the model reading and following its own body text to act; the hooks fire
deterministically regardless. A `skill-tester` Quick Workflow run was performed anyway on 2026-09-21 (at
explicit user request, to confirm the mismatch directly rather than by assertion) — 6/6 assertions
passed with 0/21 of this skill's own declared scenarios actually exercised (originally reported as
0/10; see `evals/strategic-compact/evals.json`'s own `coverage_note` for the recount history), matching
this exact reasoning. Recorded at `evals/strategic-compact/evals.json`. The meaningful test surface is the hook
scripts' own input/output contracts, verified directly
(stdin → stdout/exit-code, against realistic and adversarial JSON payloads) rather than via an
LLM-judged eval — see `hook-development/scripts/test-hook.sh`. The checklist below documents that
direct-verification surface, and the persisted `scripts/smoke_test.py` exercises
`compact-milestone-detector.sh`, `compact-skill-category-detector.sh`, `compact-stop-check.sh`, and
`compact-session-init.sh` directly
against this same stdin/stdout contract, plus imports and cross-checks `context-monitor.py`'s
`get_session_dir()` implementation. `context-mode`'s own `scripts/smoke_test.py` separately covers
`detect_mode.py`'s new mode-switch-suggestion side effect. **Known gap (hook-reviewer, 2026-09-18):** `compact-track-and-
suggest.sh` (the most complex script — async, cross-process locking), `compact-instructions.sh`,
`pre-compact.py`, and `post-compact-restore.py` have no direct stdin/stdout contract test of their
own yet — only incidental coverage via shared helper functions and constant cross-checks. Tracked as
an open item, not silently claimed as covered.

**Last dated run record:** `scripts/smoke_test.py` — 29/29 checks passing as of 2026-09-21 (added
`check_powershell_tool_payload_still_triggers_milestone` for the Windows PowerShell-matcher fix, 6
`check_skill_category_*` checks for the new heavy_operation/session_analysis events,
`check_skill_category_unset_plugin_root_fails_open` and `check_session_init_resets_mode_file_on_startup`
for 2 fixes found by scripts-reviewer's own pass on this batch,
`check_no_hook_script_falls_back_to_cksum` for a `cross-model-review` finding on the same batch, and —
from Codex + CodeRabbit's automated PR reviews on PR #368 —
`check_skill_category_malformed_local_json_falls_back_to_defaults` and
`check_stop_hook_delivers_multiple_queued_suggestions`, plus renaming the two
`check_skill_category_*_start_and_finish` checks to `*_start` and rewriting
`check_skill_category_priority_heavy_over_session_analysis` and
`check_prefixed_content_with_hostile_tail_is_discarded` for the finish-phase removal and pending-file
queue rewrite respectively).
`context-mode`'s own `scripts/smoke_test.py` — 14/14 checks passing as of 2026-09-21 (6 pre-existing +
6 `check_mode_switch_*`/gate checks for the context-mode-switch event,
`check_mode_switch_future_timestamp_self_heals` for the same scripts-reviewer pass, plus
`check_mode_switch_pending_write_is_additive` for CodeRabbit's automated PR review on PR #368).

**Verify this skill's hooks activate on:**
- A session starting (`SessionStart`, any source) — tool-call tracking initializes; a `compact`/
  `resume` source additionally triggers the restore hook.
- Any tool call — `PreToolUse` tracking fires on every call (matcher `.*`); `context-monitor.py`
  additionally fires on every successful tool call (`PostToolUse`, matcher `.*`).
- A `Bash` **or `PowerShell`** command matching a known test/build/commit/deploy pattern (e.g.
  `pytest`, `git commit`, `npm run build`) — `compact-milestone-detector.sh` fires on `PostToolUse`
  for either tool (matcher `^(Bash|PowerShell)$`; see "Windows PowerShell coverage" above).
- A `Skill()` call to a known `heavy_operation`/`session_analysis` skill about to start —
  `compact-skill-category-detector.sh` fires on `PreToolUse`, matcher `^Skill$` (see "Skill-category
  events" above).
- A confidently-detected context-mode switch (exactly one candidate, differing from the last one) —
  `context-mode`'s `detect_mode.py` writes into this skill's own delivery mechanism, throttled to once
  per 5 minutes (see "Context-mode switch events" above).
- A compaction event (manual `/compact` or automatic) — both `PreCompact` hooks fire; the matching
  `SessionStart` restore hook fires on the following turn.

**Verify this skill's hooks do NOT fire a false positive on:**
- A `Stop` event where `stop_hook_active` is already `true` — must exit cleanly, never re-block.
- A Bash command containing an unrelated word that happens to substring-match a milestone-detection
  pattern (e.g. `majestic`, `cmake build`) — `compact-milestone-detector.sh`'s test/build/deploy
  patterns use `grep -w` (whole-word matching), not `\b...\b`: BSD grep (macOS's default
  `/usr/bin/grep`) doesn't support the GNU-only `\b` escape at all, so `-w` is the portable choice
  that still stops these from producing a false milestone suggestion.
- A `Skill()` call to a skill not in either category list — `compact-skill-category-detector.sh`
  produces no output at all.
- A context-mode turn with zero or multiple candidates — never updates the tracked mode or emits a
  switch suggestion, since it's too ambiguous to treat as a confident mode reading.

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
- [ ] A `git commit` (or other milestone-pattern command) run via the **`PowerShell`** tool produces
      the same milestone suggestion as the identical command run via `Bash` — never silently dropped
      because `tool_name` was `PowerShell`.
- [ ] A compaction event followed by a `SessionStart` with `source=compact` restores the
      previously-captured plan state (when `CONTEXT_KIT_PLANS_DIR` is configured) via
      `additionalContext`, with no crash if no state was ever captured.
- [ ] An env var like `STRATEGIC_COMPACT_T1` set to a non-numeric or malicious value falls back to
      its default rather than corrupting the tracking file or executing as shell code.
- [ ] A `heavy_operation`/`session_analysis` skill produces its `PreToolUse` start suggestion — there is
      no `PostToolUse` finish counterpart to test (dropped 2026-09-21; see "Skill-category events").
- [ ] A skill matching both category lists resolves to `heavy_operation`, never `session_analysis`, when
      a genuine overlap actually exists between the two lists — not merely a skill that only appears in
      one of them.
- [ ] A `.claude/context-kit.local.json` entry adds to, never replaces, the tracked-default category
      lists — a tracked-default skill still classifies correctly even when a local override is present,
      including when that local override file is malformed JSON.
- [ ] A confidently-detected context-mode switch produces exactly one suggestion per 5-minute window,
      not a repeated suggestion on every subsequent switch within that window — while the tracked
      "current mode" itself still updates every time, even while throttled.
- [ ] Two suggestions queued in the same `pending-<hash>` file before `compact-stop-check.sh` drains it
      (e.g. a threshold suggestion and a context-mode-switch suggestion arriving close together) are
      both delivered in one `decision: block` — neither silently overwrites the other.
- [ ] A malformed line appended to the pending file alongside an otherwise-valid one is dropped on its
      own, without discarding the still-valid queued suggestion(s) next to it.
