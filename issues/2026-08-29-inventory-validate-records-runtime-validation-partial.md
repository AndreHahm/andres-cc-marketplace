## Summary
`validate_records` (shared by `marketplace-inventory.py` and `plugin-inventory.py` via `inventory_common/reconcile.py`) checks only a handful of record-shape invariants — it still omits ID format, component-type shape, several field shapes, and required history-period metadata beyond what PR #238 just added for `repair-history`'s own replacement periods specifically.

## Environment
- **Product/Service**: `plugins/plugin-devkit/scripts/inventory_common/reconcile.py` (`validate_records`), consumed by `marketplace-inventory.py` and `plugin-inventory.py`'s `bootstrap`/`apply`/`import-grading`/`check`/`repair-history` subcommands
- **Region/Version**: N/A

## Reproduction Steps
N/A — not a reproducible bug, a scope gap. Found via Devin AI's automated review of PR #238
(`.claude/scripts/inventory_common/reconcile.py:207-208`, comment id
`ANALYSIS_pr-review-job-59db05ffd8b44af3b1eb7d67f4784165_0002`): "Runtime validation remains partial —
The new provenance check covers one schema constraint. `validate_records` still omits IDs, component
types, field shapes, and required period metadata."

## Expected Behavior
N/A (not a bug) — flagging a scope gap for a decision on whether/when to close it.

## Actual Behavior
`validate_records` (see `reconcile.py`) currently checks: duplicate `id`, `status` enum, `functional_role`
enum (when present), `compatibility.level` enum entries, `provenance` shape (object, added this PR),
`status_history`/`naming_history` period well-formedness (open-period cardinality, date shapes/ordering —
via `models.validate_history_periods`), open-period-matches-current-value, active-record uniqueness, and
score/security_score consistency against their own histories. It does **not** check:
- `id` format (the `<type_prefix>_<8-hex>` shape `models.generate_id` produces)
- component-type-specific shape (e.g. that a `"skill"`-type component's `path` actually points at a
  `SKILL.md`, vs. an `"agent"`-type component pointing at a `.md` file directly)
- several field shapes beyond `compatibility`/`provenance` (e.g. `domains`/`domain` as a real list of
  strings, `source`/`path` as a real string)
- required non-date period metadata on `status_history`/`naming_history` entries that are **already
  stored on disk** — PR #238 added `models.validate_history_period_fields` (status enum, non-empty
  `reason`, list `evidence`) but scoped it deliberately narrowly: it's only called from
  `cmd_repair_history` against a *replacement* file being written, never wired into `validate_records`
  itself, specifically to avoid retroactively invalidating any pre-existing on-disk history that predates
  this stricter rule.

## Impact
**Low** — no known instance of an actually-malformed record slipping through today (every real inventory
in this repo passes `check` with `drift_count: 0`), but the validation surface is narrower than a reader
might assume from `validate_records`'s name, and a hand-edited or programmatically-corrupted inventory
file could still pass `check`/`apply` despite one of these unvalidated shapes being wrong.

## Additional Context
Not fixed as part of PR #238 — genuinely too large for that PR's own scope (a full schema-hardening pass
across every record field, plus a decision on whether to retroactively validate already-stored history
periods or grandfather them in). Two follow-ups worth separating if this is picked up:
1. **Forward-only tightening**: extend `validate_history_period_fields`-style checks to newly-written
   `status_history`/`naming_history` entries from every write path (`status-transition`, not just
   `repair-history`), without touching already-stored data.
2. **Retroactive audit**: a one-time `check`-mode report of which existing periods in this repo's own 5
   real inventories would fail the stricter field checks, before deciding whether/how to backfill them.

Related: `plugins/plugin-devkit/scripts/inventory_common/reconcile.py`'s `validate_records`; `models.py`'s
`validate_history_period_fields` (new in PR #238); Devin AI review comment on PR #238
(`https://github.com/AndreHahm/andres-cc-marketplace/pull/238#discussion_r3887299992`).

## Review Finding Source
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/238
- Head SHA at time of finding: `b55b07a3e5dbe37b39fa69e4a23beb00169fe3b2`
- Thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/238#discussion_r3887299992
- Reviewer: Devin AI (devin-ai-integration[bot])
- Stated severity: Analysis (informational, not flagged as a bug)
