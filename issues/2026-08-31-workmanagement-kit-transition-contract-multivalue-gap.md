## Summary
`FOUNDATION_CONTRACTS.md`'s Transition Contract schema is single-valued (one `affected_record` per entry) but two skills' own documented procedures need more than that shape can hold — found by a mandatory pre-push `cross-model-review` pass.

## Context
- **Product/Service**: `workmanagement-kit` plugin (`plugins/workmanagement-kit/`), specifically `FOUNDATION_CONTRACTS.md`'s Transition Contract section and its two dependent skills: `work-linking`, `open-item-management`
- **Related work**: pre-push `cross-model-review` (Claude + Codex), iteration 3, on branch `feature/workmanagement-kit-wave1-scaffold`

## What Happened

`FOUNDATION_CONTRACTS.md`'s Transition Contract schema (`transition_id`, `operation_id`,
`affected_record: {system, stable_id}` — singular, `source_plugin`, `verification_evidence`,
`recorded_at`) is explicitly documented as "not a separate log" — one entry represents one write's
own evidence. Two skills' own documented procedures need more than that single-valued shape can
hold:

1. `work-linking/SKILL.md`'s Linking section states: "A link is a pair of stable IDs plus an
   authority label... Record links per `FOUNDATION_CONTRACTS.md`'s Transition Contract schema so a
   later drift check has something to compare against." The schema has no authority-label field and
   only one `affected_record` (not a pair). The instruction names a schema that doesn't structurally
   support what it's being asked to store.
2. `open-item-management/SKILL.md` step 6 requires "the disposition of every item" from a batch to
   be recorded on the single source record via the same `transition-id`-tagged property model — but
   a multi-item disposition pass has multiple outcomes to record against one source record, and the
   Transition Contract's single-valued fields would overwrite each other rather than accumulate.

Both gaps were found independently during the same review pass: the first by Codex's Phase 1
fresh-eyes pass, confirmed by Claude's Phase 2 cross-examination; the second (same root cause,
applied to `open-item-management`) found independently by Codex's own Phase 2 challenger pass.

## Proposed Fix

Either:
- **(a)** Extend the Transition Contract schema to support repeatable/array-based entries — a
  counterpart-record + authority-label pair for links; an array of one-entry-per-item for batch
  dispositions — updating `FOUNDATION_CONTRACTS.md` and both dependent skills to match; or
- **(b)** Introduce a dedicated linked-record/disposition-history mechanism separate from the
  single-write Transition Contract, with `work-linking`/`open-item-management`'s own text corrected
  to point at whichever mechanism is chosen.

Also verify `notion-knowledge-management/SKILL.md`'s own citations of the Transition Contract for
consistency once the schema shape is decided, since it's a third consumer of the same shared
contract.

## Impact
**Medium** — no data loss (nothing has attempted this write path live yet, since Foundational Setup
hasn't happened), but the plugin's own documented drift-check and disposition-tracking behavior
cannot actually be implemented as currently specified for its two most structurally-affected skills.

## Additional Context
Deliberately deferred rather than fixed inline in the PR that surfaced it — this is real design work
needing a schema decision, not an isolated correction. A smaller, unrelated finding from the same
review pass (`plugin-integration-intake`'s `source_skill` existence check) was fixed inline instead.

References: `plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md`'s Transition Contract section,
`plugins/workmanagement-kit/skills/work-linking/SKILL.md`'s Linking section,
`plugins/workmanagement-kit/skills/open-item-management/SKILL.md` step 6.
