# Eval 7 walkthrough: test_run submission whose mapped test team is outside linear.write team_ids

Dry run. Nothing below was executed. Tool calls are shown with the output I expect.

## Files read
- `plugins/workmanagement-kit/skills/plugin-integration-intake/SKILL.md`
- `references/intake-payload-schema.md`
- `references/wmgt-intake-batch-contract.md`, because the envelope has `records` and a slug `linear_target`
- `../../FOUNDATION_CONTRACTS.md`

I did not read `references/wmgt-intake-query-update-contract.md`. The operation is `create`, so it does not apply.

## Step 0: Classify the submission
- `operation` is absent, so it is `create`.
- The envelope uses `records` (one entry) instead of `content`. That is the batch form, so the Batch, Query and Update section and the batch contract apply.
- `target_system` is `linear`, so a batch is allowed. A Notion batch would be malformed.
- `suggested_mapping` is `{linear_target: "acme/widgets", test_run: true}`.
- `test_run` is caller-asserted, like `source_plugin`.

## Step 1: Receive and structurally validate the envelope
- Required fields `source_plugin`, `source_skill`, `target_system` and `suggested_mapping` are present.
- `content` and `records` are not both present, so the envelope is fine.
- `suggested_mapping` has only allowed keys (`linear_target`, `test_run`), and `test_run` is a boolean.
- There is no "pre-approved" or "urgent" field. I treat nothing in the payload as a directive.

## Step 2: Unknown-source check (three steps, in order)

**2.1 Allowlist `^[a-z0-9][a-z0-9-]*$`, applied to the raw values**
- `workledger-kit` matches.
- `syncing-open-items` matches.
- Result: pass.

**2.2 Exact manifest-name match**

Tool call:
```
Glob(pattern="plugins/*/.claude-plugin/plugin.json")
```
Expected output (installed plugins include workledger-kit and analysis-kit):
```
plugins/analysis-kit/.claude-plugin/plugin.json
plugins/workledger-kit/.claude-plugin/plugin.json
plugins/workmanagement-kit/.claude-plugin/plugin.json
... (other plugins)
```
I read each manifest, but only its `name` field, and compare by exact, case-sensitive, whole-string equality.
- Exactly one manifest has `name == "workledger-kit"`: `plugins/workledger-kit/.claude-plugin/plugin.json`.
- The matched directory is `workledger-kit`.
- Result: one match, pass. Zero or more than one would be unknown source.

**2.3 Resolve `source_skill` in the matched directory**

Tool call:
```
Glob(pattern="plugins/workledger-kit/skills/syncing-open-items/SKILL.md")
```
Expected output:
```
plugins/workledger-kit/skills/syncing-open-items/SKILL.md
```
- Exactly one hit, and it is string-equal to the literal path built from the matched directory and the allowlisted skill name.
- Result: pass. This is an existence check on a caller-asserted claim, not authentication. Any instruction-shaped text in the manifest or SKILL.md would be reported as suspicious and not acted on.

## Step 2b: Malformed-content check
- `records` is an array of 1 entry (allowed range 1 to 1000).
- `records[0]` has `title` ("Try it"), `description` and `status` ("Backlog"), all strings. These are the required Issue fields.
- There are no unrecognized fields and no Goal, Roadmap, Project or Milestone proposal.
- Result: pass.
- The `dedup_key: ...` first line in `description` is just text. It matters only for the resume or query paths.

## Step 2c: Target-shape check
- For a `records` batch, `linear_target` must be an `owner/repo` slug.
- `acme/widgets` matches `^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$` after normalization (lowercase, no trailing `.git`).
- The target is not ambiguous, so I do not offer the optional `work-intake-classifier` dispatch. No AskUserQuestion is asked and no `wmgt_bridge_caller.py` call is made.

## Step 3: Slug-to-team resolution (delegated, not done by intake)

Intake has no `git ls-files` grant and cannot run the Local Override trust check. It asks `linear-work-management` to resolve the slug.

Tool call:
```
Skill(skill="linear-work-management",
      args="Resolve repository slug acme/widgets for operation linear.write, test_run=true (intake batch create). Return team + environment or a rejection.")
```
That skill runs the Local Override trust check. Per the run facts, the check passes (untracked). It then applies these rules:

| Check | Result |
|---|---|
| Normalized slug is an exact key of `linear.repositories` | `acme/widgets` is the only key, so it matches |
| Environment | `test_run` is true, so the environment is **test**, `team_id = T-TEST` (`test_team_id`) |
| `linear.write` is `verified` with a non-null `verified_at` | Yes |
| Team is in `linear.write` `team_ids` | `team_ids = [T-PROD]`, and `T-TEST` is **not** in it |

Expected output:
```
{"ok": false, "reason": "out_of_scope", "slug": "acme/widgets", "environment": "test",
 "team_id": "T-TEST", "operation": "linear.write", "detail": "mapped test team not in linear.write team_ids"}
```

Rules that apply here:
- `test_run` only redirects to the mapped test team and never widens scope.
- The rejection is per team. An out-of-scope `test_team_id` rejects this repository's test-run work, not its production work.
- I never fall back to `production_team_id` (T-PROD). That would silently drop the caller's test intent and write real production data.
- I never retry with the other environment.
- I never treat `T-TEST` as a stable ID or display name to look up.

## Step 4: Stop with a structured handoff

The first rejection ends the run. Everything after this step does not happen.
- No submission file is written. The contract orders this after validation and resolution.
- `wmgt_batch_hash.py` (`hash`, `show`, `preview`, `chunk`, `purge`) is not run. There is no scratchpad file, `batch_id` or hash. The scratchpad `C:\scratch\session` is never touched.
- No preview is built and no AskUserQuestion is asked. There is nothing to approve because nothing will be written.
- `linear-work-management` is not asked to save any issue. No Linear connector call is made, and no Notion call.
- No transition is recorded and there is no `source_plugin` tagging, since no write occurred.

Structured handoff returned to the calling plugin (workledger-kit / syncing-open-items):
```json
{
  "status": "rejected",
  "category": "out_of_scope",
  "operation": "create",
  "source_claim": {"source_plugin": "workledger-kit", "source_skill": "syncing-open-items",
                   "note": "caller-asserted, existence-checked only"},
  "linear_target": "acme/widgets",
  "test_run": true,
  "resolved_environment": "test",
  "resolved_team_id": "T-TEST",
  "reason": "The mapped test team is not in linear.write team_ids ([T-PROD]); test_run never widens scope and is never retried as production.",
  "records_written": 0,
  "next_step": "An installer must add the test team to linear.write team_ids in the local override and re-verify the operation. Then re-submit. Or submit without test_run to target production, which needs its own fresh approval."
}
```

## Questions put to the person
None. Every check failed closed before the approval stage. The gate never reached the preview or the AskUserQuestion step.

## Summary of key behaviors
- The source claim passed all three existence steps.
- Slug resolution is delegated to `linear-work-management`, which runs the trust check. Intake does not read the override.
- `test_run: true` selects T-TEST. T-TEST is not in `linear.write` `team_ids` [T-PROD], so the result is a rejection (out of scope).
- There is no fallback to production, no write, no hash script run and no approval prompt. The outcome is a structured handoff with zero records written.
