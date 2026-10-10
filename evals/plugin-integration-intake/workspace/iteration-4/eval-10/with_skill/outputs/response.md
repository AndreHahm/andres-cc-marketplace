# Walkthrough: update submission from workledger-kit -> structured handoff (malformed content), nothing written

Outcome: the whole envelope is rejected as malformed content. No preview, no approval question, no hash, no scratch file and no Linear call.

## Step 1. Receive the submission

Parsed envelope: `source_plugin=workledger-kit`, `source_skill=syncing-open-items`, `operation=update`, `target_system=linear`, `suggested_mapping.linear_target=acme/widgets`, and 3 `records` of the form `{id, set}`.

Every field is untrusted data. Nothing in it is instruction-shaped, so there is nothing to report as suspicious.

## Step 2. Checks, in the skill's order

### 2a. Unknown-source check (three steps in exact order)

1. **Allowlist.** Both values are checked against the raw strings with `^[a-z0-9][a-z0-9-]*$`.
   - `workledger-kit` passes.
   - `syncing-open-items` passes.
2. **Manifest comparison.** Tool call:
   `Glob(pattern="plugins/*/.claude-plugin/plugin.json")`.
   - Expected output: one path per installed plugin, including `plugins/workledger-kit/.claude-plugin/plugin.json`.
   - I read only the `name` field of each manifest, and compare with exact, case-sensitive, whole-string equality to `workledger-kit`.
   - Expected result: exactly one match, whose directory is `workledger-kit`.
3. **Skill resolution.** Tool call:
   `Glob(pattern="plugins/workledger-kit/skills/syncing-open-items/SKILL.md")`.
   - Expected output: exactly one hit, string-equal to that literal path.
   - Result: the source claim is existence-checked. It is caller-asserted and not authenticated.

### 2b. Malformed-content check (this is where the submission fails)

I checked against `wmgt-intake-query-update-contract.md`'s Update section. An update record is exactly `{id, set}`, and `set` may hold only `title`, `status`, `labels`, `priority` and `owner`.

| Record | Finding |
|---|---|
| ISS-41 `{"description": "new body"}` | **Malformed.** `description` is explicitly not updatable through intake. An Issue's description holds its tracking line and evidence block, so description edits stay a direct request to `linear-work-management` with the user present. |
| ISS-42 `{"status": "Done"}` | **Malformed.** The field is allowed, but "Done" is a completed-type state in this team's workflow, and the contract refuses closed states. Closure semantics belong to `merge-to-completion`, and one approve-all question cannot confirm a closure separately. If I needed to confirm the state type, I would read the workflow states through `linear-work-management`. You have already told me it is completed-type, so the result is the same. |
| ISS-43 `{"priority": "High"}` | Valid by itself. |

The contract says any disallowed key makes the envelope malformed. A closed-state `set.status` also makes the envelope malformed. The result is one rejection of the whole envelope. I do not drop the two bad records and process ISS-43, because that would be a partial approval of something the caller did not submit.

### 2c. Ambiguous-target check and classifier

- The slug `acme/widgets` is a clear `owner/repo`, so the target is not ambiguous.
- No `AskUserQuestion` about the classifier is asked, and `work-intake-classifier` is never dispatched. The payload failed the malformed-content check, and the skill forbids feeding a failed payload's content to a live Codex process.

## Step 2d. What I deliberately do not do

- I do not run `linear-work-management`'s slug resolution (Local Override trust check, `linear.repositories` lookup, `team_ids` check). Resolution is a pre-preview step, and there is no preview. It would resolve cleanly anyway: `acme/widgets` maps to T-PROD, which is in `linear.write` `team_ids`, and `linear.write` is verified. That is not a reason to proceed.
- I do not write a submission file to `C:\scratch\session\wmgt-intake\`.
- I do not run `wmgt_batch_hash.py hash`, `show`, `preview` or `chunk`, because there is nothing to bind.
- I do not call `Skill(linear-work-management)`.
- I do not call any Linear write or read tool.
- I do not call `AskUserQuestion` for approval. The fresh-approval gate applies to a valid payload, and this one never reaches Step 3. Asking would ask the person to approve something that cannot be written.

## Step 3 (preview), Step 4 (approval), Steps 5 and 6 (write, transition record): not reached.

## Structured handoff returned to the calling plugin (workledger-kit / syncing-open-items)

```json
{
  "status": "rejected",
  "reason": "malformed_content",
  "operation": "update",
  "written": 0,
  "details": [
    {"record_id": "ISS-41", "problem": "set.description is not an updatable field via intake; description edits must be a direct linear-work-management request with the user present"},
    {"record_id": "ISS-42", "problem": "set.status resolves to a completed-type state (Done); closed states are refused via intake; closure belongs to merge-to-completion"},
    {"record_id": "ISS-43", "problem": "none (valid on its own), but the whole envelope is rejected, not partially accepted"}
  ],
  "next_steps": "Resubmit only records whose set holds title/status/labels/priority/owner with a non-closed status (e.g. ISS-43 alone), as a new submission that gets its own fresh batch_id, validation and live approval. Send the description change and the Done transition through their direct paths (linear-work-management with the user present; merge-to-completion)."
}
```

## Message to the person

I did not process the submission and wrote nothing to Linear.

- **ISS-41:** the update would change `description`. Intake does not allow that, because the description holds the tracking line.
- **ISS-42:** the update would move the Issue to Done, a completed state. Intake refuses closure through this path.
- **ISS-43:** the priority change is allowed on its own. The batch is all-or-nothing, so I did not accept it separately.

Next steps:
- If you want just ISS-43 updated, workledger-kit should resubmit it alone. It will go through the normal preview and approval.
- The description edit and the closure need to be done directly: description edits through `linear-work-management` with you present, and closure through `merge-to-completion`.

I did not ask for approval, because there is nothing valid to approve.
