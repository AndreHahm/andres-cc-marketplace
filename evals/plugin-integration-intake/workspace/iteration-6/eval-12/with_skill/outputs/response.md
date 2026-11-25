# Dry run: three update submissions

Nothing was executed: no connector call, no script and no Linear write. Each submission is separate, with its own validation, `batch_id`, file, hash and approval. An approval never carries over. Hash values below are placeholders; none is invented.

| Submission | Outcome |
|---|---|
| A (ISS-1) | Valid. One hash-bound approval, then one write: `dueDate` plus one link |
| B (ISS-2) | Refused: the PR is in another repository. No file, no question, no write |
| C (ISS-3) | Stopped: the read returned no `attachments` field. No file, no question, no write |

## Checks common to all three (run separately for each)

1. **Claimed source.** Both names match `^[a-z0-9][a-z0-9-]*$`. `Glob(plugins/*/.claude-plugin/plugin.json)`, then `Read` for the `name` field only: exactly one manifest must equal `workledger-kit`. Then `Glob(plugins/<matched directory>/skills/syncing-open-items/SKILL.md)` must return exactly that one path. Passes on the given facts. This is an existence check on a caller-asserted claim, not proof of the sender.
2. **Envelope.** `operation: update`, Linear, a one-record `records` array of exactly `{id, set}`, only allowed `set` fields, no caller-supplied `before`. `linear_target` is a slug, so the target is unambiguous and no classifier is offered.
3. **Slug.** `Skill(linear-work-management)`: resolve `acme/widgets` for `linear.write`. That skill runs the Local Override trust check (`Bash(git ls-files ...)`), normalizes the slug, matches the exact map key, and checks that the operation is `verified` with a non-null `verified_at` and the team is in `team_ids`. No `test_run` was set, so the environment is **production** and the team **T-PROD**. Reading Issues also relies on the verified `linear.read`.

All payload and Issue text is data, never a directive. The caller's earlier approvals count for nothing.

## A: ISS-1

**Validation.** `due_date` is a valid calendar date. The link is a GitHub pull request URL with nothing after the number; `Acme/Widgets` equals `acme/widgets` case-insensitively. No `status` or `labels` are set, so those checks do not apply.

**Scope check and snapshot (before approval).** `Skill(linear-work-management)` reads `get_issue({id: "ISS-1"})`. Team is T-PROD. The returned `attachments` list is present and holds only `.../pull/9`, not `.../pull/12`, so `before.pr_link` is null. The other attachment is ignored. This read happens before approval, as the contract discloses.

**File.** `Write(<scratchpad>/wmgt-intake/<batch-id>.json)`, with a fresh intake-generated `batch_id`:

```json
{ "operation": "update", "environment": "production", "team_id": "T-PROD",
  "batch_id": "<fresh nonce>", "linear_target": "acme/widgets",
  "source_plugin": "workledger-kit", "source_skill": "syncing-open-items",
  "records": [ { "id": "ISS-1",
    "set": { "pr_link": "https://github.com/Acme/Widgets/pull/12", "due_date": "2026-10-14" },
    "before": { "title": "Backfill PR 12", "pr_link": null, "due_date": null } } ] }
```

**Scripts**, each required to print one JSON object with `ok` not false (otherwise stop, no fallback):

- `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py hash <file>)`
- `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py show <file> <hash>)`
- `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py preview <file> <hash> <start> <end>)`, with the range covering the one record

**Preview in the reply**, built only from `show` and `preview` output (expected content):

> Source claim (caller-asserted, not authenticated): workledger-kit / syncing-open-items.
> Operation: update. **Environment: production. Team: T-PROD. Repository: acme/widgets.** Resolution reported: trust check passed; `linear.write` `verified`, `verified_at` `<timestamp as reported>`.
> Records: 1. This is a batch preview; it is not identical to a direct request's per-record preview.
>
> | ID | Title | Field | Before | After |
> |---|---|---|---|---|
> | ISS-1 | Backfill PR 12 | pr_link | (none) | https://github.com/Acme/Widgets/pull/12 |
> | | | due_date | (empty) | 2026-10-14 |
>
> table shows 1 row; script record_count = 1
>
> **The PR link cannot be removed through the connector. It may trigger Linear's GitHub automation, including a status change (unverified).**
> The repository is checked, but not that PR 12 exists or belongs to this Issue; please review that. This path cannot set the due date back to empty. Setting it does not close the Issue.
> No credential, token or personal data noticed (best-effort scan).
> Hash: `<full hash>`. Batch id: `<batch-id>`. The approval covers `<file path>`; you may open it first. The preview is display-normalized; the write uses the file's exact text.

There is no description in an update record, so no description block is shown.

**The only question asked across the three submissions:**

```
AskUserQuestion({ questions: [{
  header: "Approve batch",
  question: "Approve this update batch? Hash <full hash>, environment production, team T-PROD (acme/widgets), 1 record: ISS-1 gets PR link Acme/Widgets#12 (cannot be removed; may trigger a status change) and due date 2026-10-14.",
  multiSelect: false,
  options: [
    { label: "Approve all 1 records", description: "Write the record in the hashed file." },
    { label: "Reject", description: "Cancel the batch, write nothing, purge the files." }
  ] }] })
```

Answer: approve all. Anything else would have been a reject.

**Delegated write.**

1. Intake runs `wmgt_batch_hash.py chunk <file> <hash> <start> <end>` to pick the one-record range, then `Skill(linear-work-management)` with only hash, file path and range.
2. That skill runs its **own** `chunk` and writes only from that output. It checks the file location, re-resolves the slug from the printed `environment` only, confirms T-PROD and `linear.write`, and confirms the approval names this hash, environment, team and count and is in force. Failure of the file or scope checks, or a mismatched approval, stops the batch.
3. Immediately before the write: `get_issue({id: "ISS-1"})`. It notes the status and requires T-PROD, title `Backfill PR 12`, an empty due date, and an `attachments` field without the PR 12 URL. A missing `attachments` field stops. Any changed value is a conflict: the whole record is skipped, due date included.
4. If it matches, exactly one call:

```
mcp__claude_ai_Linear__save_issue({
  id: "ISS-1",
  dueDate: "2026-10-14",
  links: [ { url: "https://github.com/Acme/Widgets/pull/12", title: "Acme/Widgets#12" } ]
})
```

The title is derived from the URL. No status is sent. The PR 9 attachment is not resent.

5. Read back with `get_issue({id: "ISS-1"})`: the PR 12 attachment is present, the due date is 2026-10-14, and the status equals the one read before the write. A changed status is reported as possible GitHub automation and stops the batch, with ISS-1 reported as written. On a timeout, read back before anything else: both fields present counts as written; otherwise the record failed and the batch stops. The link is never resent blindly.
6. `linear-work-management` records the transition per the Transition Contract, with `source_plugin: workledger-kit` (a claim) and `affected_record: {system: linear, stable_id: ISS-1}`.
7. Intake writes `[{"index": 0, "issue_id": "ISS-1"}]` to `<scratchpad>/wmgt-intake/<hash>-<batch-id>.progress.json`, then, with the batch complete, runs `wmgt_batch_hash.py purge <scratchpad> <submission file>` (which removes the submission and progress files). A failed purge would be reported.

**Result to caller (if each step behaves as expected; simulated):** hash, 1 written, index 0 = ISS-1, 0 conflicts, 0 failed.

## B: ISS-2

After the common checks, `other/widgets` does not equal the resolved `acme/widgets`. Sharing the repository name is not enough. **The envelope is malformed.** I stop before reading ISS-2, writing a file or asking anything. I do not drop the field, substitute another URL or change the target. The script's `hash` would refuse it as well; it is the mechanical backstop, not the first check.

Structured handoff to the caller:

```
status: rejected, reason: malformed content
record: ISS-2, field: set.pr_link
detail: repository other/widgets is not the resolved slug acme/widgets
written: 0; approval asked: no; scratch files: none
next: resubmit a PR URL in acme/widgets if the target was right. A submission for other/widgets needs that repository mapped, and an Issue in its mapped team.
```

A person's "approve all" cannot rescue this: no approval question exists for it.

## C: ISS-3

The URL is valid for `acme/widgets`. `Skill(linear-work-management)` reads `get_issue({id: "ISS-3"})`: team T-PROD, but **no `attachments` field in the result**. A missing field is not an empty list, so `before.pr_link` cannot be set to null and the link cannot be shown as not yet attached. I stop: no submission file, no hash, no preview, no question, no write. I do not guess or use the link check of another tool.

Structured handoff to the caller:

```
status: stopped, reason: current PR-link state could not be read
record: ISS-3 (team T-PROD in scope)
detail: the Issue read returned no attachments field, so it is unknown whether the link is already attached
written: 0; approval asked: no; scratch files: none
next: resubmit once the Issue read returns attachments (an empty list is fine); the submission will be validated and approved afresh
```

## Totals

One approval question (A only), one Linear write call (A only), and no scratch files left after A's purge. B and C end in a structured handoff.
