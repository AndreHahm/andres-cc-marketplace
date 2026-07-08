---
description: Merge two complete skill directories including SKILL.md and all additional files (references, scripts, assets, templates, examples). Delegates SKILL.md to /merge-pipeline; classifies, copies, and merges all other files with a confirmation gate.
---

# /merge-skill-directory

## Purpose

Merge two complete skill directories into one canonical skill directory.

A skill directory follows the convention:

```
.claude/skills/<skill-name>/
  SKILL.md        (required)
  README.md       (optional)
  references/      (optional — linked reference documents)
  assets/         (optional — images and static files)
  scripts/        (optional — executable helper scripts)
  templates/      (optional — output or prompt templates)
  examples/       (optional — usage examples)
```

This workflow handles the full directory. It delegates `SKILL.md` merging to `/merge-pipeline` and separately classifies, copies, and merges all other files.

## Inputs

Required:

```text
skill-a: <path to source skill directory A>
skill-b: <path to source skill directory B>
```

Optional:

```text
output:              <target directory — auto-derived from SKILL.md `name` if omitted>
reference_dir:       <canonical reference subdirectory name — default: references>
merge_scope:         full | skill-manifest-only   (default: full)
target_type:         skill                        (fixed; passed to /merge-pipeline)
merge_strategy:      auto | canonical-single-file | variant-preserving | ...
merge_goal:          consolidate | deduplicate | standardize | auto
preferred_style:     operational | concise | detailed | preserve-primary
strictness:          conservative | balanced | aggressive
documentation_depth: concise | standard | detailed
verbosity:           verbose | normal | minimal
run_dir:             <auto | .claude/output/<slug>-<YYYY-MM-DD>>
skip_review:         false | true
skip_document:       false | true
skip_backup:         false | true
skip_assess:         false | true
skip_self_critique:  false | true
archive_sources:     false | true
dry_run:             false | true
```

Defaults:

```text
output:              auto
reference_dir:       references
merge_scope:         full
merge_strategy:      auto
merge_goal:          auto
preferred_style:     operational
strictness:          conservative
documentation_depth: standard
verbosity:           normal
skip_review:         false
skip_document:       false
skip_backup:         false
skip_assess:         false
skip_self_critique:  false
archive_sources:     false
dry_run:             false
```

## Core Rules

- Never auto-proceed past the confirmation gate without explicit user confirmation.
- Never auto-merge scripts or binary files — always copy both with suffixes and flag for manual review.
- Never overwrite an existing file in the output directory without reporting a conflict.
- Never delete source files unless `archive_sources=true` is explicitly set.
- When `merge_scope=skill-manifest-only`, skip Steps 1–3 and 5–7 and behave like `/merge-pipeline` called directly on the two `SKILL.md` files.
- When `skill-b` contains only `SKILL.md`, Step 0.2 triggers a fast-path: Steps 1–3 are skipped automatically (no files to classify or confirm).

## Workflow

See [references/merge-skill-directory-workflow.md]({REPO_ROOT}/.claude/references/merge-skill-directory-workflow.md)

Run the referenced workflow step-by-step in the defined order beginning with `Step 0 — Guard Checks` and ending with `Step 10 — Report Pipeline Complete`.

## Step Summary

| Step | Name | Pauses? |
|---|---|---|
| 0 | Guard checks + auto-resume detection | no |
| 0.2 | SKILL.md-only B fast-path — skip Steps 1–3 if B has no other files | no |
| 0.3 | Pre-merge orphan scan — record A's pre-existing broken references | no |
| 1 | Directory scan — enumerate all non-SKILL.md files *(skipped on fast-path)* | no |
| 2 | Classify files — assign actions; build `copy-manifest.txt` *(skipped on fast-path)* | no |
| 3 | **Confirmation gate** — present full directory manifest *(skipped on fast-path)* | **yes** |
| 3.5 | Pre-copy B-only files — in-place merge only; prevents hook timing conflict *(skipped on fast-path and standard merges)* | no |
| 4 | SKILL.md merge — delegate to `/merge-pipeline` (nested) | yes (assessment) |
| 4.5 | Post-merge diff — `git diff HEAD` on merged SKILL.md; present to user | no |
| 5 | Directory contents execution — merge-md, merge-md-cross, conflict copies; copy-from-b skipped if Step 3.5 ran | no |
| 6 | Reference table integrity check — normalize to `${CLAUDE_SKILL_DIR}/` paths; distinguish pre-existing vs merge-caused orphans | no |
| 7 | Backup source directories — skip A when `output = A`; run after Step 4 | no |
| 8 | Self-critique | no |
| 9 | Archive source directories (only if `archive_sources=true`) | no |
| 10 | Report pipeline complete | no |

## Relationship to `/merge-pipeline`

| Concern | `/merge-pipeline` | `/merge-skill-directory` |
|---|---|---|
| Scope | Any two `.md` files | Full skill directory |
| SKILL.md merge | ✓ (primary purpose) | Delegated to `/merge-pipeline` |
| Reference / other markdown files | Out of scope | Classified and merged/copied |
| Scripts / assets | Out of scope | Copied with conflict detection |
| Directory name normalization | Out of scope | ✓ Step 2 |
| Reference table integrity | Out of scope | ✓ Step 6 |
| Self-critique | ✓ | ✓ Step 8 (outer scope) |

## Self-Review Checklist

Before reporting pipeline complete, verify:

```text
[ ] Both source directories contained SKILL.md.
[ ] Pre-merge orphan scan ran (Step 0.3) and pre-existing broken references are documented.
[ ] Directory scan covered all non-SKILL.md files.
[ ] Every file was assigned a merge action before execution.
[ ] Cross-file overlap scan ran for all markdown files.
[ ] Content-overlap pairs (if any) were confirmed by the user before merging.
[ ] Confirmation gate was presented and user confirmed.
[ ] B-only files without integrated content classified as `skip` (with reason), not `copy-from-b`.
[ ] B-only files copied before SKILL.md merge (in-place: Step 3.5) or after (standard: Step 5a).
[ ] SKILL.md merged via /merge-pipeline.
[ ] Post-merge diff presented to user after Step 4.
[ ] All reference paths in merged SKILL.md use ${CLAUDE_SKILL_DIR}/ prefix.
[ ] All copy actions executed without silent overwrites.
[ ] All merge-md actions produced an output file.
[ ] All copy-both-with-suffix conflicts are listed in directory-manifest.md.
[ ] Reference table integrity check ran and results written.
[ ] Unresolved references classified as pre-existing or merge-caused.
[ ] Manual review items (if any) are listed.
[ ] Backup written (or skip_backup=true).
[ ] manifest.md reflects all step completions.
```

## Example Invocation

```text
/merge-skill-directory
  skill-a: .claude/skills/security-reviewer-2/
  skill-b: .claude/skills/security-reviewer-ok/
  output:  .claude/skills/security-reviewer/
  reference_dir: references
  documentation_depth: detailed
  skip_self_critique: false
```

```text
/merge-skill-directory
  skill-a: .claude/skills/code-reviewer-v1/
  skill-b: .claude/skills/code-reviewer-v2/
  merge_scope: skill-manifest-only
  dry_run: true
```
