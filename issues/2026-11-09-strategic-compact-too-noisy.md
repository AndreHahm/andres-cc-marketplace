## Summary
context-kit: `strategic-compact` is too noisy: a false "context ~90%" warning fires in every session, alerts are delivered through a blocking Stop hook that forces extra turns, and a typical session gets ~6 alerts.

## Environment
- **Product/Service**: context-kit (`strategic-compact` skill, `plugins/context-kit/hooks/` and `plugins/context-kit/scripts/context-monitor.py`)
- **Region/Version**: main at 913d7738; model claude-sonnet-5-5
- **Browser/OS**: Windows 11, Git Bash

## Reproduction Steps
1. Start any new session in this repo (with or without loading a handoff).
2. Make one or two tool calls.
3. Observe the "Context ~NN% (coarse proxy); auto-compaction is approaching" message (90% tier).
4. Work for 50+ tool calls, 30+ minutes, or make a commit: further `[StrategicCompact]` messages arrive, each relayed through a forced extra assistant turn.

## Expected Behavior
Alerts appear only when context is actually filling up, at most a few times per session, and without forcing extra turns.

## Actual Behavior
Median ~6 visible interruptions per session (max 17, 252 total over 43 sessions). The 90% warning is wrong in 43 of 43 sessions.

## Analysis

Method: 43 session transcripts modified since 2026-11-06 (project transcript directory), parsed for `hook_system_message` / `hook_additional_context` / `hook_blocking_error` attachments, `tool_use` counts, timestamps and assistant `usage` fields; plus the hook scripts and `context-monitor.py`. The analysis script lives in a session scratchpad, not in the repo.

### The three suspected causes: all confirmed

| # | Cause | Verdict | Evidence |
|---|---|---|---|
| 1 | Many tool calls (`git-kit`, `plugin-devkit`) | Confirmed | 21/43 sessions reach 100 or more tool calls (median 97). The 50 / 75 / 100 call alerts fired in 27 / 24 / 23 sessions. The "every 50 calls after 100" alert fired 30 times in 16 sessions. |
| 2 | Sessions longer than 30 minutes | Confirmed | 31/43 sessions ran 30 minutes or more (median 67). The time alert fired in 30 of them. It measures wall-clock time since start, so idle time counts. |
| 3 | "Context over 90%" when loading a handoff | Confirmed, but not specific to handoffs | The 90% warning fired in 43/43 sessions, always on tool call 1 or 2. The 13 handoff-load sessions look the same as the rest. |

### Root cause of the false 90% warning

`context-monitor.py` estimates usage as transcript file bytes / 4 against an assumed 200k-token window.

- The transcript file is already ~0.78 MB at the first tool call. About 400 KB of that is records that never reach the model: the `instructions` attachment (~248 KB), `prompt_snapshot` (~152 KB) and `api-request-blob` / `api-request-shape` entries.
- Real first-turn usage (assistant `usage` fields) is ~110k tokens in every session, so real usage at session start is ~10% of a larger window, not 97%.
- Real sessions reach 350k tokens (median) and 967k (max) without compaction, so the window is clearly larger than 200k. This is an inference; the window size was not read directly.
- The warning fires once per session and is wrong every time. The 40 / 55 / 65% "learn" thresholds are subsumed immediately by it.

### Other causes found

| Source | Frequency | Notes |
|---|---|---|
| Stop hook (`ctx-compact-stop-check.sh`) returns `decision: "block"` | 101 forced turns in 33 sessions | Forces an extra assistant turn just to relay the text. The PreToolUse alert is async and never surfaces itself in transcripts, so Stop is the real delivery path. |
| Commit milestone | ~88 times in 27 sessions (median 1, max 10) | Only a 5-minute cooldown. Not tied to context fullness. Sent twice (`systemMessage` + `additionalContext`). |
| Test-pass milestone | ~16 times in 4 sessions | Same double delivery. |
| Phase transition (10+ reads, then an edit) | 26 sessions | Happens in nearly every session. |
| Startup banner "Context management active" | every session | |
| Overlap | median ~6 per session | All of these say roughly "consider /compact". |

Only 12 `compact_boundary` events exist in all history. The tool-count and time alerts do not track context fullness at all.

## Impact
**High** - Interrupts nearly every session several times, adds forced extra turns (cost and latency), and the always-wrong 90% warning trains users to ignore real warnings.

## Suggested fixes (in order of impact)
1. Fix the percentage: use real `usage` token counts from the latest assistant message in the transcript, or at least exclude non-context record types and set the window from the model.
2. Stop delivering alerts through a blocking Stop hook (no forced extra turn). Use a non-blocking `systemMessage`, or drop the relay.
3. Gate the T1 / T2 / T3, every-50, time and phase alerts on real context percentage, or collapse them into one alert per session.
4. Drop or raise the cooldown on commit and test milestones, and send each once instead of on two channels.

Fixes 1 and 3 add configurable thresholds, so `.claude/rules/ask-before-config-decisions.md` applies: ask storage and format via `AskUserQuestion` before building any config-reading logic. Fixes 2 and 4 do not.

## Additional Context
Dedup check done: no existing open or closed issue covers this. Related but different: #352 (context-kit hook contract tests), #316 (mirror sync of `scripts/`), #618 (gaps deferred from PR #584).
