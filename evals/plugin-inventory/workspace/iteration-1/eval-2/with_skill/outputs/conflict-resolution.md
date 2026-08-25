# Resolving a `conflict` Operation (Missing Active Component)

## The scenario

`plugin-inventory.py plan <plugin_dir> <inventory_path>` compared the canonical inventory against the
current filesystem/manifest discovery and found a component whose inventory record is `status: "active"`
but whose recorded `path` no longer exists on disk. Per `scripts/plugin-inventory.py`'s `build_plan()`,
this surfaces as a `conflict` entry shaped like:

```json
{
  "operation": "conflict",
  "id": "component_abc123",
  "name": "some-skill",
  "type": "skill",
  "reason": "active record's discovered path is missing -- requires a rename, supersede, retire, or restoration decision, not an automatic retirement",
  "requires_approval": true
}
```

## Why it can't be applied as-is

Per SKILL.md's Plan mode section and Failure Handling section:

> A `conflict` entry (an active record whose discovered path went missing) is never applied as-is and
> never auto-resolved — instead, once the human picks a resolution (rename, supersede, retire, or
> restore), construct a `status-transition` operation in its place.

And from Failure Handling:

> **Missing active component** (a `conflict` operation): requires a rename/supersede/retire/restore
> decision, applied as a `status-transition` operation ... never auto-retired just because its discovered
> path disappeared, and never applied as the bare `conflict` shape itself.

So the resolution procedure is:

1. Present the `conflict` entry to the user via `AskUserQuestion` — the four possible resolutions are
   **rename** (the component moved/was renamed and should be matched to a newly-discovered candidate),
   **supersede** (replaced by a different component that takes over its role), **retire** (genuinely gone,
   no replacement), or **restore** (the path loss was a mistake — e.g. an uncommitted deletion — and the
   component is still current). This is a human judgment call; the script never guesses.
2. Once the user picks a resolution — for this task, **retiring the component** (path is genuinely gone,
   no replacement) — construct a `status-transition` operation, not a bare `update` on `status` (a bare
   `update` would leave `status_history` stale and fail `validate_inventory`'s
   `open_period_value(status_history) == status` invariant).
3. Write that operation into the approved-plan JSON file (the `<approved_plan.json>` the Apply step's
   command line names), alongside any other approved operations from the same plan pass, each keeping its
   own shape (`add`/`update`/`status-transition`/`no-op`).
4. Run `apply` with the **same `expected_hash`** this same `plan` invocation returned — never a hash from
   an earlier run (stale-hash rejection; see `.claude/rules/recheck-state-before-side-effecting-action.md`).

## The exact `status-transition` operation to write (retire)

Confirmed against `apply_status_transition()` in `scripts/plugin-inventory.py` (lines 241-261), which reads
`operation["id"]`, `operation["new_status"]`, `operation["reason"]`, and optionally `operation["evidence"]`,
`operation["valid_from"]`, `operation["closed_valid_to"]`, `operation["superseded_by_id"]`:

```json
{
  "operation": "status-transition",
  "id": "component_abc123",
  "new_status": "retired",
  "reason": "discovered filesystem path no longer exists; user confirmed the component is genuinely removed, not renamed/superseded/restored",
  "evidence": []
}
```

Notes on the fields:
- `id` — must match the `id` from the original `conflict` entry (`component_abc123` above), not a name/type key.
- `new_status` — `"retired"` for this resolution (the other three legal values per the skill's own
  enumeration are `"superseded"`, `"active"` (restore), or a rename path via `update`+`status-transition`
  combination as the user's decision dictates).
- `reason` — free text explaining why; required by `apply_status_transition` (`operation["reason"]` has no
  default and will `KeyError` if omitted).
- `evidence` — optional list (defaults to `[]` in the script); since the original filesystem path is gone,
  there is no live path to cite, so an empty list (or a citation to the last-known path / the `plan` output
  itself) is appropriate.
- `superseded_by_id` — omitted entirely for a retire resolution; only included when `new_status` is
  `"superseded"`, per the SKILL.md operation shape (`"superseded_by_id": "<id, only for supersede>"`).
- `valid_from` / `closed_valid_to` — both optional; if omitted, `apply_status_transition` defaults
  `valid_from` to today's date via `_today()` and leaves `closed_valid_to` unset (script decides the
  close boundary of the prior open period itself).

This operation is written into the approved-plan JSON file as one entry in the `operations` array — it
**replaces** the bare `conflict` entry from `plan`'s output; the `conflict` shape itself is never included
in what gets applied.

Example approved-plan file content (`approved_plan.json`), showing this one resolved operation alongside
how a `no-op` from the same plan pass would sit next to it unchanged:

```json
{
  "operations": [
    {
      "operation": "status-transition",
      "id": "component_abc123",
      "new_status": "retired",
      "reason": "discovered filesystem path no longer exists; user confirmed the component is genuinely removed, not renamed/superseded/restored",
      "evidence": []
    }
  ]
}
```

(The exact top-level wrapper shape follows whatever `apply`'s CLI expects to read from
`<approved_plan.json>` — a list/array of approved operation objects, each retaining its own
`operation` field so `apply_plan()`'s dispatch (`add` / `update` / `status-transition` / `no-op`) can
route it correctly.)

## The exact apply command

```bash
python scripts/plugin-inventory.py apply <inventory_path> <approved_plan.json> <expected_hash>
```

Concretely, e.g.:

```bash
python scripts/plugin-inventory.py apply \
  plugins/my-plugin/.claude-plugin/plugin-inventory.json \
  approved_plan.json \
  a1b2c3d4e5f6...  # the exact "expected_hash" value THIS plan invocation returned
```

Critical constraint (per SKILL.md's Apply section and the stale-check rule): `expected_hash` **must be
the exact value this same `plan` pass returned**, never reused from an earlier run. `apply` re-reads the
inventory itself and rejects a mismatched hash (`current_hash != args.expected_hash` in the apply CLI
path) rather than merging — if a mismatch happens (e.g. the file changed between `plan` and `apply`),
the correct response is to re-run `plan` fresh, re-collect approvals, and retry with the newly-returned
hash — never retry with the old one.

## Why not a bare `update`

A bare `{"operation": "update", "id": "...", "field": "status", "new_value": "retired"}` would set
`component["status"]` directly (via `apply_update`) without touching `status_history` at all. That would
leave the previously-open `status_history` period (`valid_to: null`, value `"active"`) stale while the
record's current `status` says `"retired"` — `validate_inventory`'s own invariant check
(`models.open_period_value(component["status_history"], "status") != component["status"]`) would then
reject the write. Only `status-transition` (via `history.close_and_append_status_period`) closes the old
period and opens a new one atomically with the status change, which is exactly why the skill documents
`status-transition` as the *only* correct shape for resolving a `conflict`.
