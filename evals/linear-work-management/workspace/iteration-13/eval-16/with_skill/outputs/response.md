# Delegated update, records 0-4 (dry run; no tool called)

`<ISSUE n>` is record n's Issue ID, `<HASH>` the approved hash; both come from the delegation and my own chunk output.

## 1. Gate checks

1. File condition: `/scratch/session/wmgt-intake/batch-0007-abc.json` is directly inside the scratchpad's `wmgt-intake`. I would run
   `${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py chunk /scratch/session/wmgt-intake/batch-0007-abc.json <HASH> 0 5`
   (the end index is exclusive) and use only what it prints. Holds.
2. Target: run the Local Override trust check, `git ls-files -- .claude/workmanagement-kit.local.json` (it must not be tracked; I take this as passing, since the scenario says the target resolves). The printed environment `production` selects T-PROD for `acme/widgets`; that matches the printed team_id, is in `team_ids`, and `linear.write` is verified with a non-null `verified_at`. Holds.
3. Approval: the latest question naming this hash was asked inside plugin-integration-intake, named production, T-PROD and 5 records, and was answered "approve all". No later reject or stop so far. Holds.
4. Each Issue is re-read immediately before its own write (below).
5. No record sets a label or status. Nothing to check.

**Questions I would ask: none.** The batch approval covers these records.

## 2. Records, in order

**Record 0: conflict, nothing written.**
- `get_issue(id=<ISSUE 0>)`: PR1 is attached, due date empty. `before.pr_link` is null, so PR1 should not be attached. The mismatch skips the whole record, including `due_date`; I do not write the date alone.
- No `save_issue` call. A conflict is not a failure, so continue.

**Record 1: written, by no-op (no connector write needed).**
- `get_issue(id=<ISSUE 1>)`: `https://github.com/Acme/Widgets/pull/2` is attached. URLs match case-insensitively, so this is PR2 and equals `before`.
- `links` is left out because it is already attached and `before` names it. Nothing else is in `set`, so no `save_issue` call.
- Read back: `get_issue(id=<ISSUE 1>)` to confirm PR2 is attached and the status is unchanged. Continue.

**Record 2: written, confirmed by read-back after a timeout.**
- `get_issue(id=<ISSUE 2>)`: attachments returned, no PR3; note the status.
- `save_issue(id=<ISSUE 2>, links=[{url: "https://github.com/acme/widgets/pull/3", title: "acme/widgets#3"}])`: times out.
- Do not retry. `get_issue(id=<ISSUE 2>)`: PR3 attached, everything else, status included, as before. Every requested field is as requested, so it counts as written. Continue, with no second send.

**Record 3: written, then the batch stops.**
- `get_issue(id=<ISSUE 3>)`: status Todo, no PR4. Matches `before`.
- `save_issue(id=<ISSUE 3>, links=[{url: "https://github.com/acme/widgets/pull/4", title: "acme/widgets#4"}])`
- `get_issue(id=<ISSUE 3>)`: PR4 attached, but status is Done. `set` did not ask for a status, so this is possible GitHub automation (not proven). The record is written as requested, and the batch stops. I do not revert Done: that is a material change nobody approved, and it is not accepted as plugin closure (`work-closed`) either.

**Record 4: not attempted, not written.**
- The stop comes before this record, so I make no write for it, although its re-read would match. No skip is silent: it is reported as unprocessed.

## 3. Result returned to plugin-integration-intake

Hash `<HASH>`, production, T-PROD, acme/widgets. **Batch stopped after record 3.**

| Index | Issue | Result | Detail |
|---|---|---|---|
| 0 | `<ISSUE 0>` | Conflict, skipped | PR1 already attached although `before` is null; due date not written |
| 1 | `<ISSUE 1>` | Written (no connector write) | PR2 already attached, in different case; read back |
| 2 | `<ISSUE 2>` | Written | Write timed out; read-back shows PR3 attached; not resent |
| 3 | `<ISSUE 3>` | Written; batch stopped | PR4 attached; status unexpectedly Todo to Done, possible GitHub automation |
| 4 | `<ISSUE 4>` | Not written | Batch stopped before it |

Totals: 3 reported written (two by a connector write, one already satisfied), 1 conflict, 1 unprocessed, 0 failed.

- Transition evidence: records 2 and 3 are the only real write calls. Their read-back evidence is in this report. I make no extra metadata write, because the approved `set` does not contain one and the intake gate does not exempt it. The attribution for each is the `source_plugin` printed by the chunk.
- The stop ends the approval. This hash must not be delegated again, for record 4 or any other.
- Record 4 (and record 0, if still wanted) needs a new submission with a new `batch_id`, fresh `before` snapshots, a new hash and a fresh "approve all".
- plugin-integration-intake keeps the progress file (written indexes 1, 2, 3; conflict 0) and keeps the submission and progress files until a resume supersedes them or the person abandons the batch, then purges them.
- For the person: check `<ISSUE 3>`'s Done status and the GitHub automation before any resume. Restoring Todo is a separate, separately approved request. The PR4 link cannot be removed through the connector.
