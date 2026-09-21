# Hook Wiring By Event

Extracted from `SKILL.md`'s own `## Integration` section (per `skill-reviewer`, 2026-09-21) to keep
that file within its own R13 line-budget tier. See `state-and-side-effects.md` for what these hooks
write to disk and the data-only boundary governing state read back from it.

This skill's own hook wiring, by event (not necessarily every other entry `hooks.json` carries for
sibling skills — e.g. `context-mode`'s `UserPromptSubmit` hook lives in the same file):

- **`UserPromptSubmit`** — not this skill's own hook (`context-mode`'s `scripts/detect_mode.py` owns
  it), but as of 2026-09-21 it also writes into this skill's own delivery mechanism on a
  confidently-detected mode switch — see `SKILL.md`'s "Context-mode switch events" section.
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
  what actually delivers it to the user, not this hook's own return value. `compact-skill-category-detector.sh
  start` (matcher `^Skill$`, added 2026-09-21 — see `SKILL.md`'s "Skill-category events" section)
  separately detects a
  known `heavy_operation`/`session_analysis` skill about to start. Unlike `compact-track-and-suggest.sh`,
  this one runs synchronously (not `async`) — its own cost (jq parsing two small config files plus a
  tracking-file existence check) is reasoned as comparable to `context-monitor.py`'s own measured
  83-97ms tier, not independently live-benchmarked; disclosed as an assumption, not a measurement.
- **`PostToolUse`** — `compact-milestone-detector.sh` (matcher `^(Bash|PowerShell)$`, broadened
  2026-09-21 — see "Windows PowerShell coverage" below) detects milestones (tests passing, commits,
  builds, deploys) from the command that just ran. `compact-skill-category-detector.sh finish` (matcher
  `^Skill$`, added 2026-09-21) detects a known `heavy_operation`/`session_analysis` skill that just
  completed, delivering its own suggestion directly via this call's synchronous JSON output — unlike the
  milestone/threshold suggestions above, it never touches the pending-file/`Stop`-hook relay at all,
  since a `PostToolUse` hook that isn't `async` can already deliver `additionalContext` synchronously
  and reliably. `context-monitor.py` (matcher
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

**Windows PowerShell coverage (fixed 2026-09-21):** `compact-milestone-detector.sh`'s `PostToolUse`
matcher was `^Bash$` only from this skill's first version through 2026-09-20. On a Windows session
where the environment's own guidance steers git/npm/etc. invocations through the **PowerShell** tool
rather than `Bash` (see the `PowerShell` tool's own description: "This tool is for terminal
operations via PowerShell: git, npm, docker, and PS cmdlets") — which `git-kit`'s `commit` skill's
`git commit` call follows — the milestone detector never fired at all for those commands: `PostToolUse`
with matcher `^Bash$` never dispatches for a `tool_name: "PowerShell"` event, so `commit`/`test_pass`/
`build`/`deploy` milestones went undetected with no error (silent, since `onError: "warn"` only
surfaces a hook's own execution failure, not "the hook was never invoked"). `git-kit`'s own
`guard-raw-commit.sh` already treats `Bash` and `PowerShell` as equally valid sources for a raw `git
commit` invocation (`hooks/scripts/guard-raw-commit.sh` line 67) — the matcher here now matches that
precedent: `^(Bash|PowerShell)$`. `compact-milestone-detector.sh`'s own command-extraction
(`.tool_input.command` via `jq`) needed no change — the PowerShell tool's `tool_input` schema uses the
same `command` field name Bash does, and the milestone-pattern regexes match on the literal
program-invocation text (`git commit`, `pytest`, etc.), which is unaffected by which shell tool
carried it.
