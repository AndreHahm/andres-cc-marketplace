# Simulated run: onboarding-repositories for acme/widgets

Simulation only. No Linear, Notion, GitHub or Codex tool was called, no script was run, and no file was written
except this output. Calls are described in the order they would be made, with the reply I would expect.

## Assumptions (from the task)

- The config loads with no problems and no warnings.
- `acme/widgets` is not in `settings.repos` (new repository, not a re-check).
- All four `intake_capabilities` are `false`, so `query` is off and Linear-side steps can only be attested.
- No `.claude/workledger-kit.local.json` exists, and `local_override.tracked` is false.
- The person approves the proposed config entry at step 5.
- The person rejects the plugin hook prompt on the `Write` at step 6.
- Simulation choice (not in the task): for the step 3 attestations, I assume the person confirms each step as in
  place. Nothing is marked verified, because `query` is off.

## Planned calls, in order

### 1. Load config (step 1)

Bash, run from the repository root:

```
${CLAUDE_PLUGIN_ROOT}/scripts/wlgr_config.py
```

Expected reply (simulated):

```json
{
  "repos": [],
  "problems": [],
  "warnings": [],
  "repo_root": "<repo root of this checkout>",
  "intake_capabilities": { "batch": false, "query": false, "update": false, "classify": false },
  "local_override": { "exists": false, "tracked": false }
}
```

Empty `repos` is expected for a project that has not onboarded anything yet. No problems, so the
`digest.output_dir` gitignore check passes (checklist step 9 is verified by the loader's own read-back).

### 2. Get the repository (step 2)

No tool call. The slug was given, `acme/widgets`. Validation passes: letters and `/` only, with neither half made
of dots only. The slug is not in `settings.repos`, so this is a new repository. `local_override.tracked` is false,
so the run continues.

### 3. Verify the human steps (step 3)

`query` is false, so every Linear-side step is asked with `AskUserQuestion` and recorded as **attested, not
verified**. Questions are asked one at a time, and I wait for each answer.

Q1, checklist step 1. `AskUserQuestion`: "Is there a Linear team for acme/widgets with a short issue prefix?"
Options: "Yes, team and prefix exist", "No", "Not sure".
Reply (simulated): "Yes, team and prefix exist." Prefix value not supplied in this simulation, so it stays
`<PREFIX>` in the label plan.

Q2, checklist step 2. "Do the team statuses include Triaged and Ready to Merge, alongside Backlog, Todo, In
Progress, In Review, Done and Canceled?" Reply (simulated): "Yes."

Q3, checklist step 3. "Is Linear's GitHub integration connected, with PRs linking by the team prefix, and
automatic issue creation from PRs and GitHub issues off?" Reply (simulated): "Yes."

Q4, checklist step 4. "Does Linear's automation map draft PR to Todo, open PR to In Progress, review to In Review,
ready to Ready to Merge, and have no mapping for merge or close?" Reply (simulated): "Yes."

Q5, checklist step 5. "Is stale auto-close off, auto-archive set to its longest period, and are the parent and
sub-issue auto-close settings understood?" Reply (simulated): "Yes."

Q6, checklist step 6. "Do master open-item and master PR-record issues exist, each labelled `meta: master`, with a
first-line `dedup_key:` (and a `github_labels` line on the open-item one), excluded from saved views?" Reply
(simulated): "Yes."

Q7, checklist step 7. "Is the `owner/repo` to team mapping set in workmanagement-kit's `linear.repositories`?"
Reply (simulated): "Yes, I believe so." Recorded as attested, but the skill notes this cannot be satisfied until
Wave 3a ships, so it is reported as **open** with that reason.

Q8, checklist step 8. "Have any issue templates been created? If so, have they been removed?" Reply (simulated):
"No templates were created."

Step 9 needs no question: the loader reported no `digest.output_dir` problem.

### 4. Emit the label plan (step 4)

Text output, no tool call. Workspace-wide labels (`type:`, `impact:`, `kind:`, `origin:`, `meta: master`) already
exist and are not recreated. Team-scoped labels for acme/widgets, to be created by a person through
`linear-work-management`:

| Name | Scope | Reason |
|---|---|---|
| `<PREFIX> plugin: <name>`, one per plugin in acme/widgets | Team | Groups open items by plugin |
| Any area labels the repository wants | Team | Requested by the person; none supplied here |

The plugin list for acme/widgets was not given, so the plan is a template. This skill creates no label.

### 5. Propose the config entry (step 5)

No `Read`: `local_override.exists` is false, so there is no existing file to merge. `settings.repos` is empty, so the
effective list is empty, and the written list is the new entry alone. `report_dirs` defaults to
`[".claude/output"]`, which is a relative path with no `..`. `intake_capabilities` is not added (the skill never
sets it).

Complete resulting file shown to the person:

```json
{
  "repos": [
    { "slug": "acme/widgets", "report_dirs": [".claude/output"] }
  ]
}
```

`AskUserQuestion`: "Write this complete file to `<repo_root>/.claude/workledger-kit.local.json`?" Options:
"Approve", "Change", "Cancel". Reply (given by the person in this task): **Approve**.

### 6. Write (step 6)

Write, path `<repo_root>/.claude/workledger-kit.local.json`, with the content approved above.

The plugin's `PreToolUse` hook matches the path and prompts again. The person rejects it, so the expected reply is a
denial:

```
Write denied: the permission prompt for .claude/workledger-kit.local.json was rejected.
```

Per the skill, the file is unchanged. Report that it was not written and stop. No re-validation run is needed,
because nothing changed.

### 7. Report (stop)

No further calls.

## Final reply I would send the person

acme/widgets is **not onboarded**. The config file was not written.

- **Config:** Your approval was recorded, but the hook prompt on the Write to
  `.claude/workledger-kit.local.json` was rejected, so the write was denied and the file is unchanged. Nothing was
  added to `repos`. Re-run the skill and approve the write at the hook prompt to retry.
- **Checklist (attested, not verified; Linear was not queried because `query` is off):**
  1. Team and prefix: attested. Prefix still needed for the label plan.
  2. Statuses: attested.
  3. Linear GitHub integration and automatic issue creation off: attested.
  4. Automation mapping: attested.
  5. Stale auto-close and auto-archive settings: attested.
  6. Master issues: attested. Not read back.
  7. workmanagement-kit `owner/repo` to team mapping: **open**. Cannot be satisfied until Wave 3a ships.
  8. Issue templates: attested.
  9. `digest.output_dir` gitignored: verified by the config loader, no problem reported.
- **Label plan:** `<PREFIX> plugin: <name>` per plugin, plus any area labels, created through
  `linear-work-management`. Plugin list still needed.
- **Limits:** Attestations are not verified. Intake submission stays in plan mode until the `batch` and `query`
  flags ship, so `syncing-open-items` cannot submit for acme/widgets yet.

## Notes on the run

- The step 6 rejection is the expected outcome here: the file is left unchanged, the skill stops, and no
  re-validation is run.
- No Linear, Notion or GitHub tool was called. Everything above is a plan, not an action taken.
