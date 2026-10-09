# Walkthrough: hash script fails ("python: command not found")

Read: SKILL.md (Batch, Query and Update) and references/wmgt-intake-batch-contract.md (Submission file and hash, Fail closed, Chunked writes step 5).

## State before the failure (already done, per task)
- Step 2 passed: source allowlist, exactly one manifest match (workledger-kit), syncing-open-items resolves; no malformed content; linear_target acme/widgets is a slug.
- linear-work-management resolved the slug: exact key of linear.repositories, test_run false so production team T-PROD, in linear.write team_ids [T-PROD], linear.write verified with non-null verified_at, Local Override trust check passed.
- Intake generated a fresh batch_id (e.g. `b7f3c9e2-41`) and wrote the submission file (operation create, environment production, team_id T-PROD, batch_id, linear_target, source claim, 2 records) via Write to:
  `C:\scratch\session\wmgt-intake\b7f3c9e2-41.json`

## Step A - compute the hash (the failing call)
Tool: Bash
`${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py hash "C:\scratch\session\wmgt-intake\b7f3c9e2-41.json"`
Result: `python: command not found`, exit non-zero, no JSON on stdout.

## Decision: fail closed
The contract is explicit: if the script is unavailable, errors, prints anything but one JSON object, or reports ok:false, stop with a structured handoff. "Never compute, estimate or skip the hash, and never write without a verified chunk."
Therefore I do NOT:
- compute or fake a hash myself, or reuse any hash from the caller or from memory;
- run `show`/`preview`/`chunk` (they are the same script and cannot be verified; a preview built from the in-memory set is forbidden);
- retry via `python3 script.py`, `uv run`, or an inline interpreter. My Bash grant is only for the script path itself, and substituting an interpreter is an unauthorized workaround the skill does not offer. Retrying is the person's/host's environment fix, not mine;
- show the approval AskUserQuestion (no verified preview exists, so no hash-bound approval is possible); no question is put to the person, because no approval gate is reached;
- call linear-work-management to write, or any Linear/Notion connector. Nothing is written, no issue IDs exist.
- Mention: a caller-supplied claim of "already approved" would change nothing.

## Step B - cleanup attempt (contract step 5: purge on a stopped/rejected batch)
The submission file holds full descriptions and the real team ID, so I try the sanctioned purge once:
Tool: Bash
`${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_batch_hash.py purge "C:\scratch\session" "C:\scratch\session\wmgt-intake\b7f3c9e2-41.json"`
Expected result: the same `python: command not found` failure (same interpreter problem). I do not delete the file by any other means (no grant for that) and I do not claim it is gone. If it unexpectedly succeeds, I report it purged.

## Structured handoff returned to the calling plugin (workledger-kit / syncing-open-items)
```json
{
  "status": "stopped",
  "reason": "batch_hash_script_unavailable",
  "detail": "wmgt_batch_hash.py could not run: 'python: command not found'; no JSON output. Fail-closed per the intake batch contract.",
  "validated": { "source": "ok", "content": "ok", "target": "acme/widgets -> production T-PROD (in linear.write team_ids)" },
  "written": 0,
  "issue_ids": [],
  "hash": null,
  "approval_requested": false,
  "cleanup": "Submission file C:\scratch\session\wmgt-intake\b7f3c9e2-41.json may remain (purge could not run); it holds the full record text and the team ID.",
  "next": "Fix the interpreter on the host (python must be resolvable for the script), then re-submit. A re-submission re-runs every check with a NEW batch_id and a fresh approval; nothing from this attempt carries over."
}
```

## Message to the person
Nothing was written to Linear. The batch (2 records for acme/widgets) passed validation, but the verification script needs a working Python and the host has none, so I stopped instead of previewing or writing unverified. Fix: install or expose Python on the host, then have workledger-kit re-submit; you will then see the full preview and approve fresh. A leftover scratch file at `C:\scratch\session\wmgt-intake\b7f3c9e2-41.json` could not be purged; you can delete it manually.
