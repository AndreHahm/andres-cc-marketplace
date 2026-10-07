# Approve and Submit (Phases 7-8)

This file is a **safety gate**: the only place the skill hands anything toward Linear. The contracts it relies
on (payload shape, capability flags) were read in Phase 1. `P-` is the per-repository file-name prefix from
`collect-and-plan.md`.

## Phase 7: Submit

**Entry:** at least one batch has an approved plan hash, and `intake_capabilities.batch` and
`intake_capabilities.query` are both true. If either is false, do not submit: leave the proposals files in the
working folder, tell the user which capability is missing and that submission waits for it, and go to "If
nothing was submitted" below.

1. **Re-check the state you are about to act on.** Run `${CLAUDE_PLUGIN_ROOT}/scripts/wlgr_config.py` again.
   If `problems` is non-empty, or `repos` or `intake_capabilities` differ from what Phase 1 showed, stop and
   report the difference: the local config can change during a long run, and it is trusted only because it
   is untracked. Then run `wlgr_open_items.py plan-hash P-issues-p.json` and require it to equal the approved
   hash; if it differs, stop that batch and return to the Phase 6 preview.
2. **Build the intake payload** from the proposals file: for each proposal, `content` is `title`,
   `description`, `status`, `labels` and `priority` (omit `priority` when null). Do not send `dedup_key`
   (it is already the first line of `description`) or `ambiguous` (intake rejects unrecognized fields). Set
   `source_plugin: workledger-kit`, `source_skill: syncing-open-items`, `target_system: linear` and
   `suggested_mapping.linear_target: <owner>/<repo>`. Do not call a Linear or Notion connector.
3. Hand the batch to `plugin-integration-intake` (`Skill(plugin-integration-intake)`). Intake shows its own
   preview and asks for its own live approval; the Phase 6 approval does not substitute. If the user
   declines there, record the batch as declined.
4. **There is no resume file.** If a run is interrupted, start again at Phase 5: the dedup against a fresh
   `P-existing.json` classifies everything that already landed as `duplicate` and drops it, so only the
   unsubmitted items remain in the next plan, and the approval is bound to that new, exact set.

**Exit:** each batch is submitted, declined, or not offered (missing capability).

## Phase 8: Verify

**Entry:** at least one batch was submitted.

1. Read the issues back through intake's query operation into a fresh `P-existing.json` (`Write`), and run
   `wlgr_open_items.py classify P-issues-a.json P-existing.json P-issues-k.json` (likewise the other
   sources). Every submitted key must now be `duplicate`. Report any submitted key that is not (missing); do
   not retry silently. `classify` keeps only the first issue it finds for a key, so it cannot show a key that
   matches several issues.
2. Report per batch: submitted, declined, pending and drift found, and name the working-folder files.

**Exit:** a per-batch report naming every key not confirmed.

## If nothing was submitted

Say so plainly with the reason (plan mode, missing `query`, or all batches declined), list the proposals files
written, and say which capability flag to enable once the matching Wave 3a work has shipped.
