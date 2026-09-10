# Recovery Metrics

How to interpret `failure_aggregator.py`'s `recoveries`/`recovery_details`/`unresolved_failures`/
`repeated_failures` output fields for the Reliability & Stability report section.

## Recovery Matching

The script matches each failure to the *next* success for the same `subject` (FIFO: the oldest
still-unmatched failure for a subject is the one a following success is treated as recovering). This
means:

- A subject that fails once and then succeeds has exactly one recovery.
- A subject that fails, fails again, then succeeds once has one recovery (the first failure) and one
  entry left in `unresolved_failures` (the second) -- the single success can't recover two failures.
- A subject with no following success anywhere in the supplied events stays in `unresolved_failures` --
  this does **not** mean it never recovered; it means recovery, if any, happened outside what this run's
  events actually cover. State this scope limitation in the report rather than implying the failure was
  never fixed.

## `time_to_recovery_seconds`

Computed only when both the failing event's and the recovering event's `timestamp` are present and
parseable. `null` otherwise -- never estimated from surrounding context, adjacent events' timing, or a
typical-case assumption. When reporting a `null` time-to-recovery, say plainly that recovery time is
unknown for that item rather than omitting the field or defaulting it to zero.

## `repeated_failures`

A subject with 2+ failure events in the supplied scope, regardless of whether any of them recovered. This
is a distinct signal from "unresolved" -- a subject can be both repeated (failed 3 times) and eventually
resolved (the 4th attempt succeeded), or repeated and still unresolved. Report both facts about the same
subject together rather than only the more alarming one.

## Reading These Together in a Finding

A single Reliability & Stability finding about one subject typically draws from more than one of these
fields at once -- e.g. "Bash(pytest) failed 3 times (repeated_failures), category tool, the last failure
was never followed by a success in this run's own events (unresolved_failures)." Don't split these into
separate findings per field; the subject is the unit of analysis, not the metric.
