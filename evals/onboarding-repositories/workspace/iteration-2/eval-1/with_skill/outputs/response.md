# Simulated run: onboard acme/widgets (onboarding-repositories, eval 1, iteration 2)

Simulation only. No Linear, Notion, GitHub or Codex tool was called, no script was run, and the only file written is this output. Assumptions from the task: config loads with no problems, `acme/widgets` is not in `settings.repos`, all `intake_capabilities` are false, no local file exists, the config entry was approved at step 5, and the Write call's hook prompt is rejected.

`<repo_root>` is the checkout the session runs in.

## Planned calls, in order

### Step 1: Load config (planned, not run)

- Bash: `${CLAUDE_PLUGIN_ROOT}/scripts/wlgr_config.py`, run from `<repo_root>`.
- Assumed reply: no `problems`; `warnings` empty; `repos` = `[]`; `intake_capabilities` = `{batch: false, query: false, update: false, classify: false}`; `local_override` = `{exists: false, tracked: false}`; `repo_root` = `<repo_root>`.
- The reply shows that `digest.output_dir` is gitignored, so checklist step 9 reads back as verified (the loader checks it).

### Step 2: Get the repository (no call)

- Slug `acme/widgets` was given. It passes the slug rule (letters, digits, `.`, `_`, `-`; not only dots).
- It is not in `settings.repos`, so this is a new repository, not a re-check.
- `local_override.tracked` is false, so no stop.

### Step 3: Verify the human steps

- `intake_capabilities.query` is false, so no Linear read-back is possible. Nothing is queried.
- Each of the nine checklist steps needs a person's confirmation, asked one at a time with AskUserQuestion (the person prefers sequential asks). Planned first call:

  AskUserQuestion: "Checklist step 1: does a Linear team exist for acme/widgets, with a short issue prefix? What is the prefix?"
  options: "Yes, with prefix (type it)", "No, not yet", "Not sure"

- Steps 2 to 9 are asked in the same form, in order.
- No answers to these questions were given in this run. Every step is therefore reported as **open**, not attested and not verified. Step 9 is the exception: it is verified by the loader's read-back in step 1.
- Steps 1, 2 and 6 would be verifiable through intake's query once `intake_capabilities.query` is true. Steps 3, 4, 5, 7 and 8 stay attested-only in any case.

### Step 4: Emit the label plan (text only, no call)

- Team prefix is unknown, so names are shown as a pattern: `<PREFIX> plugin: <name>`, one per plugin in acme/widgets, plus any area labels the team wants.
- No plugin list for acme/widgets was given, so the plan has no concrete names yet.
- Workspace-wide labels (`type:`, `impact:`, `kind:`, `origin:`, `meta: master`) already exist and are not recreated.
- Presented as text for a person to create through `linear-work-management`. No label is created here.

### Step 5: Propose the config entry

- Slug check passes. `report_dirs` = `[".claude/output"]` (default, relative, no `..`).
- `local_override.exists` is false, so no Read of an existing file is needed.
- `settings.repos` is empty, so the effective list is empty and the written `repos` list is just the new entry.
- `intake_capabilities` is not added or changed.
- Complete resulting file shown for approval:

  ```json
  { "repos": [ { "slug": "acme/widgets", "report_dirs": [".claude/output"] } ] }
  ```

- Approval asked with AskUserQuestion. The person approved this entry, so the flow continues.

### Step 6: Write and re-validate

- Planned call: Write `<repo_root>/.claude/workledger-kit.local.json` with the content above.
- The plugin's hook (`wlgr-guard-local-config.sh`, a PreToolUse `ask` on that path) prompts again. The person rejects it, so the Write returns a denial.
- Per the skill, a rejected hook prompt means the file is unchanged. Report that it was not written and stop. The re-validation run (`wlgr_config.py` again) is **not** run.

### Step 7: Report

Given at the stop point in step 6; the config result is "not written".

## Final reply sent to the user

**acme/widgets is not onboarded yet. The config entry was not written.**

**Config result:** Not written. You approved the entry at step 5, but the Write to `<repo_root>/.claude/workledger-kit.local.json` was denied at the hook prompt, which you rejected. The file is unchanged, so `settings.repos` still does not list `acme/widgets`. I did not re-run the config check because the write did not happen.

**Checklist (nothing could be verified; intake query is off):**

| # | Step | Status |
|---|---|---|
| 1 | Linear team with a short prefix | Open (not confirmed) |
| 2 | Team statuses include Triaged and Ready to Merge | Open (not confirmed) |
| 3 | GitHub integration connected; automatic issue creation off | Open (attested-only) |
| 4 | Automation mapping (draft to Todo, open to In Progress, review to In Review, ready to Ready to Merge, no merge/close mapping) | Open (attested-only) |
| 5 | Stale auto-close off; auto-archive at longest; parent/sub-issue settings understood | Open (attested-only) |
| 6 | Master open-item and PR-record issues (`meta: master`, `dedup_key:`, `github_labels`) | Open (read-back needs query) |
| 7 | `workmanagement-kit` `linear.repositories` maps acme/widgets to the team | Open (attested-only) |
| 8 | Issue templates removed | Open (attested-only) |
| 9 | `digest.output_dir` gitignored | Verified (loader read-back, no problem reported) |

No step is marked attested, because no confirmation answers were given in this run.

**Label plan:** Team-scoped labels, named `<PREFIX> plugin: <name>`, one per plugin, plus any area labels. The prefix and plugin list for acme/widgets are needed before concrete names can be given. Create them through `linear-work-management`; this plugin creates no labels.

**Next:** Give me the team prefix, the plugin list and the checklist answers. To onboard acme/widgets, accept the config write prompt when it appears on a re-run; then the config is re-validated and `syncing-open-items` can run in plan mode.
