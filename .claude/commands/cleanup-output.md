---
description: List, review, and optionally archive or delete completed pipeline run directories in .windsurf/output/.
---

# /cleanup-output

## Purpose

Inspect all run directories in `.windsurf/output/`, report their completion status, and optionally archive or delete old runs.

This command **never deletes automatically**. All removal actions require explicit user confirmation.

## Inputs

Optional:

```text
older_than_days: <integer>
action: report | archive | delete
filter: complete | incomplete | all
```

Defaults:

```text
older_than_days: 30
action: report
filter: all
```

## Workflow

### Step 1 — Scan

List all directories in `.windsurf/output/`. For each directory, read `manifest.md` if present.

Extract per run: artifact slug, pipeline steps completed, source files, merged artifact location, creation date.

### Step 2 — Classify

| Status | Condition |
|---|---|
| `complete` | All 4 pipeline steps are ✅ in `manifest.md` |
| `incomplete` | One or more steps are ⏳ pending |
| `no-manifest` | No `manifest.md` found |

### Step 3 — Report

Always produce a report before any action:

```markdown
## Output Run Directory Report

| Run Directory | Date | Status | Steps | Merged Artifact |
|---|---|---|---|---|
| review-pr-2026-06-18 | 2026-06-18 | complete | 4/4 | .claude/commands/review-pr.md |
```

### Step 4 — Action (only if requested)

Only if `action=archive` or `action=delete`:

1. Show which directories match `filter` and `older_than_days` criteria.
2. **Pause. Require explicit user confirmation before taking action.**
3. `archive`: move matched directories to `.windsurf/output/archive/`.
4. `delete`: permanently remove matched directories and their contents.

## Safety Rules

- Never take action without explicit user confirmation.
- Do not delete the merged artifact itself — only process artifacts in the run directory.
- `incomplete` runs are excluded from cleanup unless `filter=all` is explicitly set.
- `no-manifest` directories are always listed but never auto-cleaned.

## Example Invocations

Report all runs:

```text
/cleanup-output
```

Report runs older than 7 days:

```text
/cleanup-output older_than_days=7
```

Delete complete runs older than 30 days (requires confirmation):

```text
/cleanup-output older_than_days=30 action=delete filter=complete
```

Archive all complete runs:

```text
/cleanup-output action=archive filter=complete
```
