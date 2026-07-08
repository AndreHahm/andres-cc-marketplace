---
description: Run the full merge pipeline (assess → merge → review → document) for two or more Markdown files, with file output and pipeline state tracking in .claude/output/. Pauses at safety gates for user confirmation. Supports auto-resume.
---

# /merge-pipeline

## Purpose

Chain all four merge workflow steps into a single command:

1. `/assess-md-merge` — assess mergeability
2. `/merge-md-context` — perform the merge
3. `/review-merged-md` — verify the merged result
4. `/document-merged-md-artifact` — produce usage and maintenance documentation

All process artifacts are written to a shared run directory in `.claude/output/`. The `run_dir` is passed automatically between steps.
The pipeline ends with a Self-Critique running workflow `/merge-pipeline-self-critique.md` (if not skipped).

## Inputs

Required:

```text
files:
  - <source-a.md>
  - <source-b.md>
```

Optional:

```text
target_type: skill | subagent | slash-command | reference | checklist | project-rule | auto
merge_strategy: auto | canonical-single-file | variant-preserving | base-plus-overlay | ...
merge_goal: consolidate | deduplicate | standardize | migrate | compare | archive | auto
preferred_style: concise | detailed | operational | documentation | preserve-primary
strictness: conservative | balanced | aggressive
documentation_depth: concise | standard | detailed
verbosity: verbose | normal | minimal
run_dir: <auto | .claude/output/<slug>-<YYYY-MM-DD>>
restore_from: <run_dir_path>
skip_review: false | true
skip_document: false | true
skip_backup: false | true
skip_assess: false | true
skip_self_critique: false | true
archive_sources: false | true
output_path: <auto | explicit repo path for merged artifact>
dry_run: false | true
```

Defaults:

```text
target_type: auto
merge_strategy: auto
merge_goal: auto
preferred_style: operational
strictness: conservative
documentation_depth: standard
verbosity: normal
run_dir: auto
restore_from: (none)
skip_review: false
skip_document: false
skip_backup: false
skip_assess: false
skip_self_critique: false
archive_sources: false
output_path: auto
dry_run: false
```

## Workflow

### Step 0 — Guard Checks and Auto-Resume

#### Restore Mode

If `restore_from=<run_dir>` is set, skip all other steps and execute **Restore Mode** instead:

1. Read `manifest.md` from `restore_from` to find the backup directory.
2. Restore each file: `python .claude/scripts/copy_files.py <restore_from>/backup/<filename> <original-path>`
3. Do not overwrite a file that already exists at its target path — report and ask for confirmation.
4. Report which files were restored and which were skipped.
5. Stop. Do not proceed with any merge steps.

#### Max Files Guard

If more than 5 files are provided, warn:

```text
Warning: merging N files in a single pass increases context loss risk.
Consider batching into smaller groups of 2–3 files.
Confirm to proceed or stop.
```

This is a soft warning — not a hard block. The user may confirm to continue.

#### Auto-Resume Detection

If `run_dir` is provided and a `manifest.md` exists in that directory, read the step completion table:

- For each step already marked `✅ complete` in the manifest, skip that step automatically.
- Report all auto-skipped steps at the start: `Resuming from Step N — skipping: [list of completed steps]`.
- If `assessment.md` is complete but not yet confirmed by the user in this session, re-present the assessment summary before continuing.

If no `manifest.md` exists but `run_dir` does, infer completion from output files present on disk:

| File present | Inferred step complete |
|---|---|
| `assessment.md` | Step 1 |
| `backup/` with files | Step 1.5 |
| `merge-and-review-report.md` | Steps 2 and 3 |
| `documentation.md` | Step 4 |

This makes `skip_assess=true` unnecessary for most resume cases. Use `skip_assess=true` only to force-skip a completed assessment without re-presenting it.

### Step 1 — Assess

Skip if `skip_assess=true` and a completed `assessment.md` already exists in `run_dir`. Report which step is being resumed from.

Run `/assess-md-merge` with the provided files and forward these parameters:

```text
target_type=<target_type>
merge_goal=<merge_goal>
strictness=<strictness>
run_dir=<run_dir>
```

Write full assessment to `<run_dir>/assessment.md`.

**Pause. Present the full assessment to the user and wait for explicit confirmation before continuing.**

- `DO NOT MERGE` or `BLOCKED`: stop and report. Do not continue.
- `HUMAN DECISION REQUIRED`: require explicit resolution before continuing.
- `MERGE NOT RECOMMENDED`: warn and require explicit override to continue.
- `dry_run=true`: stop after assessment. Do not merge.

### Step 1.5 — Backup Source Files

Skip if `skip_backup=true`.

Copy each source file to `<run_dir>/backup/` using `.claude/scripts/copy_files.py`:

```
python .claude/scripts/copy_files.py <source-file> <run_dir>/backup/<filename>
```

**Filename collision guard:** If two source files share the same basename from different directories, prefix with a directory slug (`<dir-slug>--<filename>`). Example: `agents/code-reviewer.md` → `agents--code-reviewer.md`. Record in `manifest.md`.

The script skips existing destinations (exit 1) — report the skip.

Record in `manifest.md`: original file, backup path, and date.

If any backup fails, report and do not proceed to Step 2 without user confirmation.

### Step 2 — Merge

Run `/merge-md-context` and forward these parameters:

```text
target_type=<target_type>
merge_strategy=<merge_strategy>
preferred_style=<preferred_style>
strictness=<strictness>
output_mode=merged-file-with-report
run_dir=<run_dir>
skip_manifest=true
output_report=<run_dir>/merge-and-review-report.md
```

**Assessment block — pass inline, not by file path.** The Merge Instruction Block (Must Preserve / Must Resolve / Must Not / Validation Checklist) is already in the active context window from Step 1. Extract it and pass it directly as the `assessment_block` value rather than referencing `<run_dir>/assessment.md`. This avoids a redundant disk read of content already present in context.

If `output_path` is set, pass it as the target write location for the merged artifact. Otherwise use the auto-derived path.

Write merge section to `<run_dir>/merge-and-review-report.md` under the heading `## Merge Report`.

### Step 2.5 — Post-Merge Lint

Before proceeding to review, validate the merged artifact's structural integrity:

1. **YAML frontmatter** — if the file has a `---` frontmatter block, verify it is valid YAML (no unclosed quotes, no illegal characters, no duplicate keys).
2. **Top-level heading** — verify the file contains at least one `# Heading`.
3. **Empty sections** — warn if any `##` section contains no content below its heading.
4. **Fenced code blocks** — verify all code fences are properly closed.

If lint passes: continue to Step 3.

If lint fails:

- Report each failure with the specific line or field.
- **Pause and present findings before continuing.** The user must confirm before the review step runs.
- Record lint result in `manifest.md`.

### Step 3 — Review

Skip if `skip_review=true`.

Run `/review-merged-md` and forward these parameters:

```text
target_type=<target_type>
strictness=<strictness>
review_mode=report-only
optimization_scope=safe-only
run_dir=<run_dir>
skip_manifest=true
output_file=<run_dir>/merge-and-review-report.md
append=true
```

Append the review section to `<run_dir>/merge-and-review-report.md` under the heading `## Review` — do not write a separate `review-report.md`. The review section should be compact: Outcome, Assessment Compliance summary (reference `assessment.md` — do not reproduce the full table), Source Coverage, any required fixes, and Final Recommendation.

- `MERGE BLOCKED`: stop and report. Do not document.
- `MERGE HAS CONTEXT LOSS` or `MERGE NEEDS REVISION`: **pause and present findings before continuing.**

### Step 4 — Document

Skip if `skip_document=true`.

Run `/document-merged-md-artifact` and forward these parameters:

```text
target_type=<target_type>
documentation_audience=mixed
documentation_depth=<documentation_depth>
include_open_points=yes
include_next_steps=yes
run_dir=<run_dir>
skip_manifest=true
```

Write to `<run_dir>/documentation.md`.

### Step 4.5 — Archive Source Files

Only if `archive_sources=true`.

Move each original source file to `<run_dir>/backup/<filename>` (if not already backed up there):

```
python .claude/scripts/copy_files.py <source-file> <run_dir>/backup/<filename> --move
```

Update `manifest.md` with the archive action.

Do not delete source files automatically unless `archive_sources=true` is explicitly set.

Report which source files were archived.

### Step 5 — Report Pipeline Complete

Write `manifest.md` to `<run_dir>` — a single write at pipeline end covering all steps:

```markdown
## Pipeline Run: <artifact-slug>

| Step | Status | File | Date |
|---|---|---|---|
| `/assess-md-merge` | ✅ complete | `assessment.md` | YYYY-MM-DD |
| backup | ✅ complete / ⏭ skipped | `backup/` | YYYY-MM-DD |
| `/merge-md-context` | ✅ complete | `merge-and-review-report.md` (merge section) | YYYY-MM-DD |
| lint | ✅ pass / ⚠ warnings | — | YYYY-MM-DD |
| `/review-merged-md` | ✅ complete / ⏭ skipped | `merge-and-review-report.md` (review section) | YYYY-MM-DD |
| `/document-merged-md-artifact` | ✅ complete / ⏭ skipped | `documentation.md` | YYYY-MM-DD |
| self-critique | ✅ complete / ⏭ skipped | `self-critique.md` | YYYY-MM-DD |

## Source Files

- `<source-a>`
- `<source-b>`

## Source Directory Backup

| Original File | Backup Path | Date |
|---|---|---|
| `<source-a>` | `backup/<filename>` | YYYY-MM-DD |
| `<source-b>` | `backup/<filename>` | YYYY-MM-DD |

## Merged Artifact

Location: `<actual path in repository>`

## Run Directory

`.claude/output/<artifact-slug>-<YYYY-MM-DD>/`
```

Then report to the user. Report level is controlled by `verbosity`:

- `verbose`: full file tree + conflict summary + next steps
- `normal`: file tree + conflict summary
- `minimal`: one-line summary only

**Normal / Verbose report:**

```text
Pipeline complete: .claude/output/<slug>-<YYYY-MM-DD>/

  backup/                      ✅  (or skipped)
    <source-a>
    <source-b>
  assessment.md                ✅
  merge-and-review-report.md   ✅  (or partial — review skipped)
  documentation.md             ✅  (or skipped)
  self-critique.md             ✅  (or skipped)
  manifest.md                  ✅

Merged artifact: <repo path>
Source files archived: <yes | no | skipped>
Conflicts resolved: N | Unresolved: N
```

**Minimal report:**

```text
Pipeline complete. Merged artifact: <repo path> — Conflicts resolved: N | Unresolved: N
```

**Session persistence note:** All progress is preserved in the run directory. Resume by passing `run_dir=.claude/output/<slug>-<YYYY-MM-DD>` (with the same `files:` list) to a new invocation.

### Step 5.5 — Self-Critique

Skip if `skip_self_critique=true`.

Run `/merge-pipeline-self-critique` automatically:

```text
/merge-pipeline-self-critique
run_dir=<run_dir>
depth=standard
scope=all
```

Write `self-critique.md` to `<run_dir>/self-critique.md` and update `manifest.md`.

Present the verdict and any Critical or High issues to the user.

## Safety Gates

- Never proceed past Step 1 without explicit user confirmation.
- Never proceed past Step 1.5 (backup) if any backup fails, unless the user explicitly confirms.
- Never proceed past Step 2.5 (lint) if lint fails, unless the user explicitly confirms.
- Never proceed past Step 3 if review outcome is `MERGE BLOCKED`. When blocked, write `merge-and-review-report.md` with the merge section and partial review section before stopping.
- Never auto-override a `HUMAN DECISION REQUIRED` trigger.
- Never delete or overwrite source files unless `archive_sources=true` is explicitly set.
- Never overwrite an existing file during `restore_from` without explicit user confirmation per file.
- Never auto-suppress self-critique findings rated Critical or High — always present them to the user.
- `dry_run=true` stops the pipeline after assessment only.
- `restore_from` mode does not run any merge steps — it only restores backup files.

## Example Invocations

**Standard pipeline:**

```text
/merge-pipeline

files:
- .claude/commands/review-pr-1.md
- .claude/commands/review-pr-2.md

target_type=slash-command
documentation_depth=detailed
```

**Assessment only (dry run):**

```text
/merge-pipeline dry_run=true

files:
- SKILL.md
- SKILL(1).md
```

**Merge only, skip review and docs:**

```text
/merge-pipeline skip_review=true skip_document=true

files:
- review-pr-1.md
- review-pr-2.md
```

**Resume from existing run directory:**

```text
/merge-pipeline
run_dir=.claude/output/review-pr-2026-06-18

files:
- .claude/commands/review-pr-1.md
- .claude/commands/review-pr-2.md
```

**Skip backup (files already versioned in git):**

```text
/merge-pipeline skip_backup=true

files:
- .claude/agents/code-reviewer-1.md
- .claude/agents/code-reviewer-2.md
```

**Merge with explicit output path and archive sources after:**

```text
/merge-pipeline archive_sources=true
output_path=.claude/agents/code-reviewer.md

files:
- .claude/agents/code-reviewer-1.md
- .claude/agents/code-reviewer-2.md
```

**Skip assessment (assessment already done, resume from merge):**

```text
/merge-pipeline skip_assess=true
run_dir=.claude/output/code-reviewer-2026-06-18

files:
- .claude/agents/code-reviewer-1.md
- .claude/agents/code-reviewer-2.md
```

**Auto-resume (no skip flags needed — pipeline detects completed steps from manifest):**

```text
/merge-pipeline
run_dir=.claude/output/code-reviewer-2026-06-18

files:
- .claude/agents/code-reviewer-1.md
- .claude/agents/code-reviewer-2.md
```

**Restore source files from a previous run's backup:**

```text
/merge-pipeline restore_from=.claude/output/code-reviewer-2026-06-18
```

**Minimal verbosity (one-line progress, one-line completion):**

```text
/merge-pipeline verbosity=minimal

files:
- .claude/agents/code-reviewer-1.md
- .claude/agents/code-reviewer-2.md
```

**With explicit merge goal and style:**

```text
/merge-pipeline
merge_goal=consolidate
preferred_style=operational
target_type=subagent

files:
- .claude/agents/code-reviewer-1.md
- .claude/agents/code-reviewer-2.md
- .claude/agents/code-reviewer-3.md
```