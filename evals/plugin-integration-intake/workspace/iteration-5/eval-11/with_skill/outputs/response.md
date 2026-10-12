# Eval 11 walkthrough: resume of a stopped 60-record create batch (dry run)

Nothing below was executed. Every tool call is a plan with the output I would expect. No Linear or Notion tool is called, no script is run, and nothing is written before the approval.

I read SKILL.md, `references/wmgt-intake-batch-contract.md`, `references/wmgt-intake-query-update-contract.md`, `references/intake-payload-schema.md` and `linear-work-management/references/wmgt-linear-slug-resolution.md`.

## Step 0: Classify the request

The calling plugin (workledger-kit) re-submits the complete envelope. Per the batch contract, a resume is a re-submission through intake with a new `batch_id`, never "a file was found" and never the old approval or file. The old progress file is not consulted.

- I treat this as a brand-new submission, with a new `batch_id`.
- I do NOT open or Read the old submission file or the old progress file in `C:\scratch\session\wmgt-intake\`.
- The earlier approval is not reused. Every write re-enters the live approval gate.
- The old files are only purged once this resume supersedes them (see Step 9).

Order from the contract: validate (SKILL.md step 2), resolve the slug, run the exact-key dedup queries, run the pre-hash checks, write a new file, hash it, show and preview, ask one approval.

## Step 1: Envelope validation (SKILL.md step 2)

The envelope is: `source_plugin` workledger-kit, `source_skill` syncing-open-items, `target_system` linear, `operation` create, `suggested_mapping.linear_target` acme/widgets, `records` with 60 entries.

1. Allowlist check on the raw values, with `^[a-z0-9][a-z0-9-]*$` in full.
   - `workledger-kit` passes.
   - `syncing-open-items` passes.
2. Manifest `name` comparison, with the plan to match exactly one manifest.
   - Tool call: `Glob` with pattern `plugins/*/.claude-plugin/plugin.json`.
   - Expected output: the manifests of all installed plugins, including `plugins/workledger-kit/.claude-plugin/plugin.json` and `plugins/analysis-kit/.claude-plugin/plugin.json`.
   - I `Read` only the `name` field of each. Exactly one equals `workledger-kit` by case-sensitive whole-string equality. The matched directory is `plugins/workledger-kit`.
3. Skill resolution against that directory.
   - Tool call: `Glob` with pattern `plugins/workledger-kit/skills/syncing-open-items/SKILL.md`.
   - Expected output: exactly one hit, string-equal to that literal path. This passes.
4. The classifier dispatch (`work-intake-classifier`) is not used. The target is an unambiguous `owner/repo` slug, so there is no ambiguity to resolve.
5. Malformed-content check.
   - `operation` is `create`, which is valid.
   - `records` has 60 entries (limit 1 to 1000), and there is no `content` field. The target is Linear.
   - Each record holds only `title`, `description`, `status`, `priority`, `labels`.
   - No Goal, Roadmap, Project or Milestone creation.
   - Labels are only bug or chore.
   - `linear_target` is a slug, so it is not an ambiguous target.
   - No instruction-shaped text is found in the records. Any such text would be reported as suspicious and never acted on.

Result: valid. Questions asked: none.

## Step 2: Slug resolution, delegated to linear-work-management

- Call: `Skill(linear-work-management)`. Arguments: "Resolve slug `acme/widgets` for operation `linear.write`, environment per caller `test_run` (absent, so false, so production). Return a rejection, or environment, team ID and verification statement. Write nothing."
- It follows `wmgt-linear-slug-resolution.md`:
  1. Local Override trust check. It passes.
  2. Normalize: `acme/widgets` is already lowercase with no `.git`, and matches the regex.
  3. Exact key in `linear.repositories`: found (the only key).
  4. `linear.write` is verified with a non-null `verified_at`.
  5. Environment is production, so the team is `production_team_id` T-PROD. This is provisional, because it comes from the caller's `test_run` and is re-derived from the file later.
  6. T-PROD is in `linear.write` `team_ids` [T-PROD].
- Expected output: `{environment: "production", team_id: "T-PROD", verified: "trust check passed; linear.write verified, verified_at non-null; T-PROD in team_ids"}`.

The query phase also needs `linear.read` verified with a non-null `verified_at`, and the team inside `linear.read`'s `team_ids`. Both hold: [T-PROD].

## Step 3: Exact-key dedup queries (resume step 4)

Records 0-57 have a first line `dedup_key: acme/widgets|<source-ref>|<8 hex>`, which is 58 keys. Records 58-59 have no `dedup_key` line.

Key validation first:
- Each key is the text after `dedup_key: `, with trailing whitespace and CR removed.
- The first part equals the resolved slug (compared lowercased): `acme/widgets`.
- The source-ref is 1 to 100 characters with no `|`, CR or LF.
- The fingerprint is 8 hex characters, which matches `^[A-Za-z0-9._-]{8,64}$`.
- All 58 are well formed and name acme/widgets. If any were malformed or named another repository, the resume would stop with a structured handoff.

Grouping: at most 50 keys per group, so 58 keys give 2 groups.
- Group 1: keys of records 0-49 (50 keys).
- Group 2: keys of records 50-57 (8 keys).

Each group is run through `linear-work-management`.
- Call: `Skill(linear-work-management)`. Arguments: "Exact-key query. Team T-PROD, environment production, operation linear.read. Keys: [group 1]. For each key search the team with the FULL key string as the search term and a small result limit, and keep a hit only if the first line of its description is `dedup_key: <key>` (trailing whitespace and CR stripped, repository part compared case-insensitively). Return per key `{key, match_count, ids}` (at most 3 IDs, nothing else)."
- Underlying connector call it makes, one per key: `mcp__claude_ai_Linear__list_issues` with `{team: "T-PROD", query: "<full key>", limit: 5}`. For group 1 this is 50 searches, and for group 2 it is 8.
- Expected output group 1: records 0-24 each return `{key, match_count: 1, ids: ["ISS-1xx"]}`, record 0 mapping to ISS-101 through record 24 to ISS-125. Records 25-49 return `match_count: 0, ids: []`.
- Expected output group 2: all 8 keys return `match_count: 0, ids: []`.

If any query had been rejected (for example `linear.read` not verified), or the first-line check could not be applied, I would stop with a structured handoff and never treat it as "no match". Neither happens here.

Disclosed residual: each search hit's text enters the shared model context. Only IDs are used downstream.

Result of the diff against Linear:
- Dropped (already held by Linear): records 0-24, 25 records, listed with their Issue IDs (ISS-101 to ISS-125).
- Remaining: records 25-59, 35 records.
  - 33 records (25-57) have a dedup_key and no match.
  - 2 records (58, 59) have no `dedup_key` line, so they cannot be checked and may duplicate existing Issues. These are flagged in the preview.
- Not every record was dropped, so there is no completion-only report, and an approval is needed.

## Step 4: Pre-hash checks through linear-work-management

Call: `Skill(linear-work-management)`. Arguments: "Pre-hash checks for the 35 remaining records on team T-PROD (read only): (a) every label matches exactly one existing label of the team, (b) no record `status` resolves to a completed or canceled state."

- Labels: `mcp__claude_ai_Linear__list_issue_labels` with `{team: "T-PROD"}`. Expected: the labels bug and chore, each exactly once. Every record's labels (bug or chore only) match exactly one label each. This passes. No label is created (a batch approval never covers creating a label).
- Statuses: `mcp__claude_ai_Linear__list_issue_statuses` with `{team: "T-PROD"}`, expected to return the team's workflow states with their types. The eval gives no record statuses, so I assume they are open states such as Todo. None resolves to a completed or canceled state. This passes. A record with a Done or Canceled status would make the envelope malformed.
- `dedup_key` well-formed check on the 33 remaining keyed records: passes (already validated in Step 3). Records 58-59 have no `dedup_key:` first line, so the check does not apply to them. They are flagged as possible duplicates.

Result: all checks pass. Questions asked: none.

## Step 5: Write the new submission file

- A fresh `batch_id`, for example `resume-7c4e91ab52d0`. It matches `^[A-Za-z0-9._-]{8,64}$`, is generated by intake, and is not taken from the caller or the old file.
- Tool call: `Write`.
  - Path: `C:\scratch\session\wmgt-intake\resume-7c4e91ab52d0.json`. It is inside the session scratchpad, not in any repository.
  - Content:

```json
{ "operation": "create", "environment": "production", "team_id": "T-PROD",
  "batch_id": "resume-7c4e91ab52d0", "linear_target": "acme/widgets",
  "source_plugin": "workledger-kit", "source_skill": "syncing-open-items",
  "records": [ "the 35 remaining records (original indexes 25-59, now 0-34), each only title, description, status, priority, labels" ] }
```

- Expected output: file created. The environment `production` and team `T-PROD` are now frozen into the hashed file. From here on the caller's `test_run` plays no part.
- Chunk indexes now refer to this new file (35 records, indexes 0-34), not to the old 60.

## Step 6: Hash

Tool call (Bash, allowed grant `wmgt_batch_hash.py:*`):
`"${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py" hash "C:\scratch\session\wmgt-intake\resume-7c4e91ab52d0.json"`

In this repository's own sessions `CLAUDE_PLUGIN_ROOT` can be empty. I would then first confirm `.claude/scripts/wmgt_batch_hash.py` exists, and run that mirror path instead. That is not a fallback. If the command is denied or the script is unavailable, I fail closed with a structured handoff.

Expected output (one JSON object): `{"ok": true, "hash": "<64-hex>", "record_count": 35, ...}`. The script would refuse duplicate keys, extra record fields, an oversize record and so on. Any `"ok": false` or non-single-JSON output stops the batch.

## Step 7: Show and preview (verified output only)

1. `wmgt_batch_hash.py show "<file>" "<hash>"`. Expected: the header with operation create, environment production, team T-PROD, source workledger-kit/syncing-open-items, `linear_target` acme/widgets, and record_count 35.
2. `wmgt_batch_hash.py preview "<file>" "<hash>" 0 34`. Expected: 35 rows (under the 100-row and 20000-byte caps). If the `bytes` field is larger than what arrived, I re-request in smaller ranges. Expected: title, status, labels, priority and a 120-character description excerpt per row, plus the `fence` strings with the full descriptions of the first three records.

I put the whole table in the reply before the question. The cells are rendered exactly as printed, and the table ends with the count line "table shows 35 rows; script record_count = 35".

Preview content in the reply (bold where required):
- Source claim: workledger-kit / syncing-open-items, labelled **caller-asserted, not verified**.
- **Environment: production. Team: T-PROD. Repository: acme/widgets.** Verified by linear-work-management: Local Override trust check passed; `linear.write` verified with non-null `verified_at`; T-PROD is in `linear.write` `team_ids`.
- Record count: **35 records to create**.
- This is a resume. Linear was consulted for 58 exact keys (2 query groups).
- **Dropped as already in Linear (25 records), each with its Issue ID**: the 25 dedup keys of original records 0-24 mapped to ISS-101 through ISS-125, one per line (key then Issue ID). They are not recreated.
- **Warning: possible duplicates.** Original records 58 and 59 (now indexes 33 and 34) carry no `dedup_key` line, so the resume cannot check them against Linear. If they were already created before the stop, this will create a duplicate for them.
- The old stopped-run progress file was not consulted. Nothing from the earlier approval carries over.
- The full table of all 35 records. The full description of the first three records, in fences.
- The path of the hashed file `C:\scratch\session\wmgt-intake\resume-7c4e91ab52d0.json`, with a statement that the approval covers that file and the person may open it first.
- Best-effort scan for credentials, tokens or personal data: none noticed (nothing in the supplied facts suggests any).
- The full hash and the batch id `resume-7c4e91ab52d0`.
- Statement that this preview is not identical to a direct request's per-record preview: it tabulates every record and gives full text for only the first three.

## Step 8: The single approval question

Tool call: `AskUserQuestion`
- question: "Create these 35 records in Linear team T-PROD (production, acme/widgets), hash `<hash>`, batch resume-7c4e91ab52d0? 25 records already held by Linear were dropped; records 58 and 59 of the original set have no dedup_key and may duplicate existing Issues."
- header: "Approve batch"
- options:
  - "Approve all 35 records": create all 35 records in production T-PROD as previewed.
  - "Reject": cancel the batch; nothing is written and the files are purged.

There is no "approve most" option. Any other answer (free text, dismissed, unanswered) is treated as a reject.

The eval supplies no answer for this question, so the walkthrough stops here. Nothing has been written to Linear or Notion up to this point. The only file written is the scratchpad submission file.

## Step 9: What follows (conditional, not executed in this dry run)

- If rejected (or any non-approval): nothing is written. I purge with `wmgt_batch_hash.py purge "C:\scratch\session" "<new file>"`, and also purge the superseded old submission and old progress files if their names are known. Otherwise I say they may remain.
- If "Approve all 35 records":
  1. Chunk 1 is indexes 0-24 (at most 25 records and 20000 bytes). Intake runs `wmgt_batch_hash.py chunk "<file>" "<hash>" 0 24`.
  2. It delegates that range to `Skill(linear-work-management)`, passing only the hash, the file path and the range. That skill runs its own `chunk`, checks its conditions (file inside `<scratchpad>/wmgt-intake/`, slug resolves to T-PROD using the printed environment, approval still in force), and writes each record with `mcp__claude_ai_Linear__save_issue` using label IDs from `list_issue_labels`.
  3. Intake reads each Issue back and appends `{index, issue_id}` to `C:\scratch\session\wmgt-intake\<hash>-resume-7c4e91ab52d0.progress.json`. This is a new progress file for this run, written by read-then-rewrite of the whole array.
  4. Chunk 2 is indexes 25-34 (10 records), done the same way.
  5. On a failed record the batch stops and reports the failed index and error. I keep the files for that report. A further resume would again be a new submission with a new hash.
  6. On completion I purge both files and report the hash, the count written, the Issue ID per index, and any conflicts or failures. Each write's transition record carries `source_plugin: workledger-kit` (a caller-supplied claim).
  7. I also purge the old superseded 60-record submission and its progress file at this point, or say they may remain if purge fails.

## Checks against the expected behaviour

| Expected behaviour | Where |
|---|---|
| New submission with a new batch_id, old progress file never read, old approval and file not reused | Step 0, Step 5 |
| Source and content validated | Step 1 |
| Slug resolved through linear-work-management | Step 2 |
| Exact-key queries in groups of at most 50 (58 keys, two groups) against T-PROD | Step 3 |
| 25 records dropped, each key listed with its Issue ID in the preview | Steps 3 and 7 |
| 2 records with no dedup_key flagged as possible duplicates | Steps 3 and 7 |
| Pre-hash checks (labels exist, no closed status) | Step 4 |
| New submission file of the 35 remaining records, hashed | Steps 5 and 6 |
| Full preview and one fresh approval; nothing written before it | Steps 7 and 8 |
