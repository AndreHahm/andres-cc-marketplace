# Performance Metrics

How to interpret `critical_path_analyzer.py`'s `elapsed`/`active`/`overlapping`/`waiting` output and
`token_time_aggregator.py`'s level-aware `by_level`/`levels_present`/`scope_note` for the Performance &
Cost report section.

## Critical-Path Fields, Per Session

- **`elapsed_seconds`** -- wall-clock time from the earliest known span start to the latest known span end
  in this session. `null` when no span in the session has both a start and an end.
- **`active_seconds`** -- the *union* of every known span's interval, not the sum. Two spans that overlap
  by 5 seconds don't each contribute their full duration to `active_seconds` -- the overlapping portion is
  counted once. This is what makes `active_seconds` a genuine "how much wall-clock time had *something*
  happening" figure rather than an inflated sum that double-counts parallel work.
- **`overlapping_seconds`** -- total wall-clock time covered by 2+ concurrent known spans. This is a
  direct measure of realized parallelism, not a defect by itself (see the SKILL.md Gotchas section).
- **`waiting_seconds`** -- `elapsed_seconds` minus `active_seconds`: time within the session's own elapsed
  window where nothing measurable was happening. `null` whenever `elapsed_seconds` itself is `null`.
- **`known_spans`/`unknown_spans`** -- counts, never folded into any duration. A span missing `start` or
  `end` contributes only to `unknown_spans`.

## Identifying Findings From These Fields

- **Latency outlier**: a single span whose own duration (`end` - `start`) is disproportionate to the rest
  of the session's spans -- cite the specific span's label and duration, not just the session-level
  aggregate.
- **Serial bottleneck**: `overlapping_seconds` is 0 or low relative to `waiting_seconds`, and multiple
  spans plausibly could have run concurrently (different subjects, no stated dependency between them) but
  didn't -- this is the *ineffective* parallelism finding, not overlap itself.
- **Ineffective parallelism**: the inverse case -- spans dispatched in parallel that ended up serialized
  anyway (e.g. a shared resource bottleneck), visible as `overlapping_seconds` far lower than what the
  dispatch pattern implied was intended.
- **Instrumentation gap**: `unknown_spans` is a meaningful fraction of the total -- report this as a
  recommendation to add timestamps, not as a performance finding about the work itself.

## Level Availability (`token_time_aggregator.py`)

`levels_present` lists exactly which of `whole_session`/`skill`/`subagent`/`tool` this run actually has
usage data for. Before writing any cost claim in the report:

1. Check whether `whole_session` is in `levels_present`. If not, the report must say whole-session cost is
   unavailable -- never present a `subagent`-level total as if it were the whole session's cost.
2. Read `scope_note` directly rather than re-deriving the same disclosure in different words -- it already
   states which levels are present and the substitution warning.
3. Never convert `total_tokens` into a dollar figure unless the caller explicitly supplied a rate; state
   cost in tokens (and, separately, wall-clock time) when no rate exists.
