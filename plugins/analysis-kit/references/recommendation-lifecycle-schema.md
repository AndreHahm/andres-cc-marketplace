# Recommendation Lifecycle Schema

The event shape, status vocabulary, and transition rules `scripts/recommendation_registry.py`
enforces, and the reference `tracking-recommendation-lifecycle` and `comparing-sessions`' realized-impact
section both consult.

## Registry Location

`.claude/output/analysis-kit-recommendations/events.jsonl` by default -- deliberately **not** scoped
under any one skill's own `.claude/output/<skill>/` directory, since the registry tracks recommendations
regardless of which analysis-kit skill originated them.

## File Format

JSON Lines: one JSON object per line, one line per lifecycle event. **Append-only** -- a status change
never rewrites or removes a prior line; the full history for a `recommendation_id` is every line naming
it, in file order. Each append is a single buffered `write()` call, guarded by a companion
`<registry>.lock` file acquired via a retry-with-timeout loop over plain `os.open(O_CREAT|O_EXCL)` --
portable across Windows and POSIX, no `fcntl`/`msvcrt` branching, no new dependency (AKR-NFR-002). A
writer that cannot acquire the lock within its timeout raises rather than silently dropping the event
(AKR-019). A lock older than 5 minutes is treated as orphaned (its writer crashed before releasing it)
and broken automatically, rather than deadlocking every future writer permanently. Read-only operations
(`show`/`list`/`validate`) take the same lock before reading, so a reader never observes a write in
progress.

## Event Fields

| Field | Required | Meaning |
|---|---|---|
| `recommendation_id` | Yes | Stable ID, assigned once by `generating-analysis-recommendations` when a plan entry is written; never re-derived from prose similarity |
| `timestamp` | Yes | ISO-8601 |
| `status` | Yes | One of the nine statuses below |
| `source_report` | No | Path to the persisted report the recommendation traces back to |
| `actor` | No | Who/what made this status change (a user decision, an agent's own observation) |
| `rationale` | No | Why this status change happened |
| `evidence` | No | What was checked to justify this status change (never a bare claim -- see Honesty below) |
| `expected_effect` | No | What the recommendation was expected to accomplish, recorded at `accepted`/`implemented` time |
| `observed_effect` | No | What was actually observed afterward, recorded at `measured` time |

A historical record missing any optional field is valid on its own terms -- reading an older registry
never requires migrating it to add fields that didn't exist when it was written (AKR-NFR-005).

## Status Vocabulary

`proposed`, `accepted`, `declined`, `implemented`, `verified`, `measured`, `closed`, `reopened`,
`superseded`.

**Implemented is distinct from verified; verified is distinct from measured.** Implemented means the fix
landed. Verified means a check confirmed the fix actually does what it claims (the same "evidence, not a
claim" discipline `analyzing-verification-effectiveness` already applies to any other verification claim
in this plugin). Measured means a *later* session's actual behavior was observed and compared against
the recommendation's own `expected_effect` -- this is what `comparing-sessions`' realized-impact section
reads.

## Transition Diagram

```
(no prior event) --> proposed
proposed         --> accepted | declined | superseded
accepted         --> implemented | declined | superseded
implemented      --> verified | superseded
verified         --> measured | superseded
measured         --> closed | superseded
declined         --> reopened | superseded
closed           --> reopened | superseded
reopened         --> accepted | implemented | superseded
superseded       --> (terminal -- nothing follows)
```

Every recommendation's first event must be `proposed` -- there is no other valid entry point. `superseded`
is reachable from every non-terminal status (a newer recommendation replaces this one, at whatever stage
it was at) and is itself terminal. `reopened` is a real status, not just a transition label -- a
recurring issue reopens a `closed` or `declined` recommendation, and the reopened item then re-enters the
pipeline via `accepted` (the normal case) or `implemented` (if the fix was already redone and just needs
re-verifying).

## Honesty Discipline (AKR-NFR-004)

`tracking-recommendation-lifecycle` never infers a status from a weaker signal than the status actually
requires: a commit landing is not itself `verified` (a commit message is a claim, not evidence -- same
principle `analyzing-verification-effectiveness` already applies), and a passing test is not itself
`measured` (a test confirms the fix works in isolation; `measured` means a later real session's behavior
was actually observed). When asked to append `verified`/`measured` without adequate evidence behind it,
the skill asks for that evidence first rather than accepting the status change on a bare assertion.

## CLI Operations

`scripts/recommendation_registry.py --registry <path> <command>`:

| Command | Purpose |
|---|---|
| `init` | Create the registry file (and parent directories) if it doesn't exist yet -- idempotent |
| `append --recommendation-id --status [optional fields...]` | Validate the transition against the ID's current status, then append one event |
| `show --recommendation-id` | Print the full event history for one ID |
| `list` | Print every tracked ID's current (latest) status |
| `validate` | Replay the whole registry and report any invalid transitions found |
