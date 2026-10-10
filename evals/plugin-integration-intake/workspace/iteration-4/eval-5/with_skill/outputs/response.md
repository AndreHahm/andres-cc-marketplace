# Walkthrough: plugin-integration-intake, batch create of 3 Linear Issues

Files read: SKILL.md, references/wmgt-intake-batch-contract.md, references/intake-payload-schema.md. Dry run: nothing below is executed.

## Step 0. Classify the submission

- `operation` is absent, so it defaults to `create`.
- `records` has 3 items and there is no `content`, so this is a batch. `target_system` is `linear`, which is valid for a batch.
- `suggested_mapping` has `linear_target` and `rationale`. There is no `test_run`, so it is `false` and the production team applies.
- Every record has only `title`, `description` and `status`, all inside the create-record allowlist. There is no Goal, Roadmap, Project or Milestone, no `team`, `project` or `parent`, and no unrecognized field.
- Nothing in the payload reads as an instruction or a claim of prior approval. The `rationale` is treated as evidence only.
- The "approve all" answer is given for the one batch question only. It is not treated as covering anything earlier.

## Step 1. Unknown-source check (SKILL.md step 2, three steps in order)

1. **Allowlist** `^[a-z0-9][a-z0-9-]*$` against the raw values.
   - `workledger-kit` passes.
   - `syncing-open-items` passes.
   - No glob or path characters are present.
2. **Manifest comparison.**
   - Tool call: `Glob("plugins/*/.claude-plugin/plugin.json")`.
   - Expected output: one path per installed plugin, including `plugins/workledger-kit/.claude-plugin/plugin.json` and `plugins/analysis-kit/.claude-plugin/plugin.json`.
   - I `Read` each manifest and use only its `name` field. I compare by exact, case-sensitive equality with `workledger-kit`.
   - Expected result: exactly one match, in directory `workledger-kit`. Zero or two or more matches would be an unknown source and a structured handoff.
3. **Skill resolution.**
   - Tool call: `Glob("plugins/workledger-kit/skills/syncing-open-items/SKILL.md")`.
   - Expected output: exactly one hit, string-equal to that literal path. Anything else is an unknown source.

Result: the source passes the existence check. It is recorded as a caller-asserted claim, not an authenticated sender.

## Step 2. Malformed-content check

- No `content` alongside `records`, and `operation` is absent, which is valid.
- Records: 3, within 1 to 1000. Each has the required `title`, `description` and `status`.
- Result: pass.

## Step 3. Ambiguous-target check and slug resolution

- `linear_target` is "Acme/Widgets". For a `records` batch it must be an `owner/repo` slug, and it is.
- It is handed to `linear-work-management` for resolution (its "Resolving a repository slug" procedure). That skill runs the Local Override trust check, which this skill cannot run because it has no `git ls-files` grant.
- Tool call: `Skill(linear-work-management)`, with a request such as "resolve slug `Acme/Widgets` for operation linear.write, test_run=false".
- Resolution steps:
  - Normalize to lowercase with `.git` stripped, giving `acme/widgets`. It matches `^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$`.
  - `acme/widgets` is an exact key of `linear.repositories`.
  - `test_run` is false, so the team is `production_team_id`, `T-PROD`. `T-TEST` is not used.
  - `T-PROD` is in `linear.write` `team_ids` `[T-PROD]`.
  - `linear.write` is verified with a non-null `verified_at`.
  - The Local Override trust check passes.
- Expected returned value: `{ environment: "production", team_id: "T-PROD", trust_check: "passed", linear.write: {support_status: "verified", verified_at: <non-null>} }`.
- No ambiguity, so the optional `work-intake-classifier` dispatch is not offered and does not happen.
- Because the trust check has run, the preview scope is stated as verified, not "unverified, pending trust check".

## Step 4. Write the submission file (scratchpad)

- The skill says the file must go in the session scratchpad. The host-provided scratchpad is `C:\scratch\session`.
- I generate a fresh `batch_id`, for example `b-20261009-7f3a9c21` (it matches `^[A-Za-z0-9._-]{8,64}$`). It is not taken from the caller.
- Tool call: `Write("C:\scratch\session\wmgt-intake\b-20261009-7f3a9c21.json", ...)`.

```json
{ "operation": "create", "environment": "production", "team_id": "T-PROD",
  "batch_id": "b-20261009-7f3a9c21", "linear_target": "acme/widgets",
  "source_plugin": "workledger-kit", "source_skill": "syncing-open-items",
  "records": [
    {"title": "Follow up on flaky test", "description": "dedup_key: acme/widgets|pr#12|a1b2c3d4\nbody one", "status": "Backlog"},
    {"title": "Document retry policy", "description": "dedup_key: acme/widgets|pr#12|e5f6a7b8\nbody two", "status": "Backlog"},
    {"title": "Remove dead flag", "description": "dedup_key: acme/widgets|pr#13|c9d0e1f2\nbody three", "status": "Backlog"} ] }
```

- `Write` is in allowed-tools and the file is outside the repository.
- `wmgt-intake/` is the required subdirectory under the scratchpad.

## Step 5. Hash and verified output

1. Tool call: `Bash("${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py hash C:\scratch\session\wmgt-intake\b-20261009-7f3a9c21.json")`.
   - Expected output: a single JSON object, `{"ok": true, "hash": "<sha256>", "records": 3, "bytes": N}`.
   - I take `<sha256>` as H.
   - Fail-closed rule: if it errors, prints anything else, or reports `ok:false`, I stop with a structured handoff. I never compute the hash myself.
   - In this repo's own session, if `CLAUDE_PLUGIN_ROOT` is empty, the `.claude` mirror rule applies: use `$PWD/.claude/scripts/wmgt_batch_hash.py`.
2. Tool call: `Bash("... wmgt_batch_hash.py show <file> H")`.
   - Expected output: `{"ok":true, operation:"create", environment:"production", team_id:"T-PROD", source_plugin:"workledger-kit", source_skill:"syncing-open-items", records:3, batch_id:"b-20261009-7f3a9c21", bytes:N}`.
3. Tool call: `Bash("... wmgt_batch_hash.py preview <file> H 0 3")`.
   - Expected output: 3 rows with title, status, labels, priority, a 120-character description excerpt, and the full description of each record (all three are within the first three).
   - It is under the 100-row and 20000-byte limits, and `bytes` matches what arrived, so it is not cut short.
   - The preview is built only from this output, not from the set held in memory.

## Step 6. Preview shown in the reply, then the one approval question

The table goes into the reply text before the question, so it is in the transcript.

```
Batch create of 3 Linear Issues
Source (CALLER-ASSERTED, existence-checked only, not authenticated): workledger-kit / syncing-open-items
Environment: **production**   Team: **T-PROD** (acme/widgets)
Scope verified: Local Override trust check passed; linear.write verified, verified_at <value>
This batch preview is NOT identical to a direct request's per-record preview: all records are tabulated,
and full text is shown for the first three.
```

| # | Title | Status | Labels | Priority | Description excerpt |
|---|---|---|---|---|---|
| 0 | Follow up on flaky test | Backlog | none | none | dedup_key: acme/widgets\|pr#12\|a1b2c3d4 / body one |
| 1 | Document retry policy | Backlog | none | none | dedup_key: acme/widgets\|pr#12\|e5f6a7b8 / body two |
| 2 | Remove dead flag | Backlog | none | none | dedup_key: acme/widgets\|pr#13\|c9d0e1f2 / body three |

- Full descriptions of records 0 to 2 are shown (all three).
- Hashed file: `C:\scratch\session\wmgt-intake\b-20261009-7f3a9c21.json`. The approval covers that file, and the person may open it first.
- Credential, token or personal-data scan: none found (best effort).
- Hash: H (full value). Batch id: `b-20261009-7f3a9c21`.
- Tool call: `AskUserQuestion`.
  - Question: "Approve creating these 3 Issues in production team T-PROD (hash H, batch b-20261009-7f3a9c21)?"
  - Options: "Approve all 3 records" and "Reject". There is no "approve most".
- Person's answer: **approve all**.
- This is a fresh approval taken inside this intake invocation. Workledger-kit's own prior approval does not count.

## Step 7. Delegated write via linear-work-management (chunked)

Records: 3, so there is one chunk, within the 25-record and 20000-byte limit.

- Tool call: `Skill(linear-work-management)`, passing H, the submission file path, the chunk range 0 to 3, and `source_plugin=workledger-kit`.
- That skill independently runs `wmgt_batch_hash.py chunk <file> H 0 3`.
  - Expected output: `{"ok":true, operation:"create", environment:"production", team_id:"T-PROD", records:[3 records]}`.
- It checks the four conditions in the contract before skipping its per-record prompt:
  1. The file is directly inside `<scratchpad>/wmgt-intake/`.
  2. `T-PROD` is in the `linear.write` `team_ids`, and `linear.write` is verified with a non-null `verified_at`.
  3. The latest `AskUserQuestion` naming H was asked inside a `plugin-integration-intake` invocation, named production, T-PROD and 3 records, was answered "approve all", and has not been used before.
  4. The update re-read condition does not apply to a create.
- All four hold, so the per-record prompt is skipped. Intake itself makes no connector call.
- For each record it builds the write from the chunk output only, and each Issue is created in T-PROD with the status "Backlog" and its description with the `dedup_key` first line.
- After each write and read-back, it appends `{index, issue_id}` to `C:\scratch\session\wmgt-intake\<H>-b-20261009-7f3a9c21.progress.json`.
  - Illustrative IDs: PROD-101, PROD-102, PROD-103.
- Each write records its own transition per the Transition Contract, with `source_plugin = workledger-kit`, labeled as a caller-supplied claim.
- If a record failed, the batch would stop, report the index and error, and keep the progress file. A resume would be a new submission with a new `batch_id`, full re-validation and a full new preview. None of that is needed here.

## Step 8. Cleanup

- Tool call: `Bash("... wmgt_batch_hash.py purge C:\scratch\session <file>")`, covering the submission file and the progress file.
- Expected output: `{"ok":true, "removed":[...]}`. If it failed, I would say so and not claim the files are gone.

## Step 9. Result to the caller

```
Batch complete. hash=H, batch_id=b-20261009-7f3a9c21, environment=production, team=T-PROD, written 3/3.
0 -> PROD-101, 1 -> PROD-102, 2 -> PROD-103. No failed or stopped index. Scratch files purged.
Source recorded as caller-asserted claim: workledger-kit / syncing-open-items.
```

## Questions put to the person

Exactly one, the batch approval above. Answer: "approve all". No clarifying questions, no classifier-dispatch question, and no per-record prompts.

## Notes

- "Acme/Widgets" differs in case from the config key `acme/widgets`. This is handled by the documented normalization to lowercase before the exact-key match, not by fuzzy matching.
- `test_run` was not set, so `T-TEST` was never considered. Only the production environment is reported.
- Environment and team are stated in bold in the preview, as the skill requires.
