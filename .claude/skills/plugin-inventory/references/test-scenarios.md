# Test Scenarios

Full 28-scenario test walkthrough for `plugin-inventory`, extracted from `SKILL.md`'s own
`## Testing & Validation` section per `plugin-rulebook`'s R30 (content beyond R29's required
trigger-example lists must move to `references/` or `evals.json`, not stay inline in `SKILL.md`).

1. **Discovery, live** — run `discover` against this repo's own `plugins/plugin-devkit`; confirm every
   `skills/<name>/SKILL.md` directory, every `agents/*.md`, and every `commands/*.md` file appears
   exactly once, sorted, with no duplicates
2. **Bootstrap + Check round-trip** — bootstrap a fresh inventory from a real plugin directory, then run
   `check` immediately after with no filesystem changes; confirm `drift_count` is `0`
3. **Plan/Apply, add operation** — add a new skill directory to a test fixture plugin; confirm `plan`
   proposes exactly one `add` operation with `requires_approval: true`, and `apply` with that operation
   approved creates exactly one new component record with a freshly-generated `component_*` ID
4. **Stale hash rejection** — call `apply` with a hash that doesn't match the current file; confirm it
   exits non-zero with a clear message and makes no write
5. **Import grading, dedup** — import the same report twice for the same component; confirm the second
   import reports `quality_score_appended: false`/`security_score_appended: false` and the score is
   unchanged, not duplicated in history
6. **Conflict, missing active component** — remove a component's path from the fixture filesystem while
   its inventory record stays `active`; confirm `plan` emits a `conflict` operation, never a silent
   auto-retirement
7. **History invariants** — confirm every component's `status_history`/`naming_history` has exactly one
   open period (`valid_to: null`) whose value matches the record's current `status`/`name`
8. **Status transition** — apply a `status-transition` operation (e.g. `active` -> `deprecated`);
   confirm the previously-open status period closes and the new one opens, both consistent with the
   record's new current `status`
9. **Repair history, structurally invalid replacement rejected** — call `repair-history` with a
   replacement array containing two open periods; confirm it's rejected before any write
10. **Enum rejection** — set a component's `functional_role` to a value outside the controlled
    vocabulary; confirm `validate_inventory` rejects it before any write
11. **Self-check** — `scripts/smoke_test.py` passes (this skill's own persisted smoke test, including a
    live bootstrap+check round-trip against this repo's own `plugin-devkit` plugin), re-run after any
    SKILL.md or script edit
12. **Conflict, non-active record reappears** — a discovered candidate matches an existing
    `planned`/`retired`/`deprecated`/`superseded` record (e.g. a planned component that has now actually
    been built); confirm `plan` emits a `conflict`, never a silent `no-op`
13. **Check, clean rejection on an invalid inventory** — hand-corrupt an on-disk inventory (e.g. an
    out-of-vocabulary `functional_role`); confirm `check` exits non-zero with a clean rejection message,
    never an uncaught Python traceback
14. **Apply rejects an out-of-allowlist `update` field** — construct an approved plan with an `update`
    operation naming `status_history` (or any other non-allowlisted field) directly; confirm `apply`
    rejects it before any write, never silently overwriting append-only history
15. **Import grading rejects an out-of-range/non-numeric score** — construct a plugin-grader report with
    `final_score` set to `999`, a negative number, or a boolean; confirm `import-grading` rejects it
    before any write, current scores/history unchanged
16. **Status transition with rename** — apply a `status-transition` operation carrying `new_name`;
    confirm both `name` and `naming_history` update atomically (the previously-open period closes, a new
    one opens with the new name)
17. **Import grading rejects an ambiguous name-based target** — construct an inventory where a retired
    and an active component share the same `(name, type)`; confirm `import-grading` refuses to guess
    rather than silently updating whichever one happens to come first in array order
18. **Import grading rejects a non-string `graded_at`** — construct a plugin-grader report with
    `graded_at` set to an integer; confirm `import-grading` rejects it on the first import, before it
    could otherwise crash a later import with a type-mismatch error
19. **Import grading rejects a non-UTC-offset `graded_at`** — construct a plugin-grader report with a
    syntactically valid but non-`'Z'` ISO timestamp (e.g. `+10:00`); confirm `import-grading` rejects it
    on the first import — a bare non-empty-string check would let two differently-offset (but each
    individually valid) timestamps through, which then sort in the wrong chronological order under
    `history.py`'s raw lexicographic sort/max
20. **Reconciliation prefers the active record on a duplicate key** — when a retired record shares
    `(name, type)` with the active record that superseded it, and the retired one comes later in array
    order, a discovered candidate matching the active record's path must resolve to a clean `no-op` —
    not a spurious conflict against the shadowed-by-array-order retired record
21. **Check rejects a malformed compatibility shape** — a component whose `compatibility` field is a
    list instead of a dict must make `check` exit non-zero with a clean rejection message, never an
    uncaught Python traceback
22. **Bootstrap refuses an already-existing inventory** — calling `bootstrap` twice against the same
    path must make the second call fail closed with "refusing to bootstrap: ... already exists" and
    leave the first call's file untouched
23. **Repair history rejects a stale/wrong `--expected-hash`** — call `repair-history` with a
    well-formed `--confirm`/replacement but an `--expected-hash` that doesn't match the live inventory's
    current `json_store.compute_hash`; confirm it's rejected before any write with a `stale repair`
    message — found by a live PR review (#238) as a gap in the original `--confirm`-only gate, which had
    no defense against a repair approved from a snapshot that changed before the command actually ran
24. **Repair history rejects an invalid `status` enum value** — a replacement `status_history` period
    whose `status` value isn't in `STATUS_VALUES` (e.g. `"totally-invalid"`); confirm it's rejected
    before any write — `validate_history_periods` alone only checks date shapes/ordering, not the status
    enum itself
25. **Repair history rejects a period missing `reason`** — a replacement period with no `reason` field
    (or a non-list `evidence`); confirm it's rejected before any write — `validate_history_periods`
    alone never checks these fields at all
26. **Repair history rejects a stale/wrong `--expected-replacement-hash`** — call `repair-history` with
    a valid `--expected-hash` but an `--expected-replacement-hash` that doesn't match the actual
    replacement file's `json_store.compute_hash`; confirm it's rejected before any write — found by a
    live `security-reviewer` pass on PR #238 as a gap `--expected-hash` alone left open: it only bound
    the inventory's pre-repair state, never the replacement content itself
27. **Repair history rejects an `evidence` list with a non-string item** — a replacement period whose
    `evidence` array contains a non-string element (e.g. a nested object); confirm it's rejected before
    any write — the schema declares `evidence` as an array of strings, and validating only the container
    (not its items) would let arbitrary nested JSON into the append-only audit history
28. **Repair history succeeds against a hand-corrupted current inventory** — a component's on-disk
    `status_history` is hand-corrupted to two open periods (bypassing the CLI entirely, simulating a bug
    in an earlier run), then `repair-history` is invoked with a valid replacement; confirm it succeeds
    and `check` reports `0` drift afterward — found by a live `security-reviewer` pass on PR #238 as a
    self-lockout bug: the original implementation pre-validated the *current* inventory with
    `validate_inventory` before doing anything else, which would have rejected the malformed file
    outright and locked the operator out of the one command meant to fix it
